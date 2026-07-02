import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/client';
import type { AnalysisResult, AnalysisSummary } from '@/types';
import { useAppStore } from '@/store/useAppStore';

const ANALYSES_KEY = ['analyses'];
const analysisKey = (id: string) => ['analysis', id];

export function useAnalysisList() {
  return useQuery<AnalysisSummary[]>({
    queryKey: ANALYSES_KEY,
    queryFn: api.listAnalyses,
    staleTime: 30_000,
  });
}

export function useAnalysis(id: string | null) {
  return useQuery<AnalysisResult>({
    queryKey: analysisKey(id ?? ''),
    queryFn: () => api.getAnalysis(id!),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useCreateAnalysis() {
  const queryClient = useQueryClient();
  const { setIsAnalyzing, setAnalysisProgress, addAnalysis, setCurrentAnalysis } = useAppStore();

  const PROGRESS_MESSAGES = [
    'Detecting climbing wall...',
    'Measuring wall angle...',
    'Identifying holds...',
    'Classifying hold types...',
    'Building route graph...',
    'Generating beta sequences...',
    'Evaluating biomechanics...',
    'Computing difficulty...',
    'Finalizing analysis...',
  ];

  return useMutation<
    AnalysisResult,
    api.ApiError,
    { files: File[]; profileId?: string; boardType?: string; betaTypes?: string[] }
  >({
    mutationFn: async ({ files, profileId, boardType, betaTypes }) => {
      setIsAnalyzing(true);
      let messageIdx = 0;

      // Cycle through progress messages
      const interval = setInterval(() => {
        setAnalysisProgress(PROGRESS_MESSAGES[messageIdx % PROGRESS_MESSAGES.length]);
        messageIdx++;
      }, 3000);

      try {
        const result = await api.uploadImages(files, {
          climberProfileId: profileId,
          boardType,
          betaTypes,
        });
        return result;
      } finally {
        clearInterval(interval);
        setIsAnalyzing(false);
        setAnalysisProgress('');
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ANALYSES_KEY });
      queryClient.setQueryData(analysisKey(data.id), data);
      addAnalysis(data);
      setCurrentAnalysis(data);
    },
  });
}

export function useDeleteAnalysis() {
  const queryClient = useQueryClient();
  const { removeAnalysis } = useAppStore();

  return useMutation<void, api.ApiError, string>({
    mutationFn: api.deleteAnalysis,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ANALYSES_KEY });
      queryClient.removeQueries({ queryKey: analysisKey(id) });
      removeAnalysis(id);
    },
  });
}
