import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/client';
import type { ClimberProfile } from '@/types';
import { useAppStore } from '@/store/useAppStore';

const PROFILES_KEY = ['profiles'];
const profileKey = (id: string) => ['profile', id];

export function useProfiles() {
  return useQuery<ClimberProfile[]>({
    queryKey: PROFILES_KEY,
    queryFn: api.listProfiles,
    staleTime: 60_000,
  });
}

export function useProfile(id: string | null) {
  return useQuery<ClimberProfile>({
    queryKey: profileKey(id ?? ''),
    queryFn: () => api.getProfile(id!),
    enabled: !!id,
    staleTime: 120_000,
  });
}

export function useDefaultProfile() {
  return useQuery<ClimberProfile>({
    queryKey: ['profiles', 'default'],
    queryFn: api.getDefaultProfile,
    staleTime: Infinity,
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();
  const { setCurrentProfile } = useAppStore();

  return useMutation<
    ClimberProfile,
    api.ApiError,
    Omit<ClimberProfile, 'id' | 'ape_index' | 'max_comfortable_reach_cm'>
  >({
    mutationFn: api.createProfile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: PROFILES_KEY });
      queryClient.setQueryData(profileKey(data.id), data);
      setCurrentProfile(data);
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { setCurrentProfile } = useAppStore();

  return useMutation<ClimberProfile, api.ApiError, { id: string; updates: Partial<ClimberProfile> }>({
    mutationFn: ({ id, updates }) => api.updateProfile(id, updates),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: PROFILES_KEY });
      queryClient.setQueryData(profileKey(data.id), data);
      setCurrentProfile(data);
    },
  });
}
