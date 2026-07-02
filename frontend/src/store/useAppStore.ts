import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AnalysisResult, BetaType, ClimberProfile } from '@/types';

interface AppState {
  // Profile
  currentProfile: ClimberProfile | null;
  setCurrentProfile: (profile: ClimberProfile | null) => void;

  // Analysis
  analyses: AnalysisResult[];
  currentAnalysis: AnalysisResult | null;
  setCurrentAnalysis: (analysis: AnalysisResult | null) => void;
  addAnalysis: (analysis: AnalysisResult) => void;
  removeAnalysis: (id: string) => void;

  // Move navigation
  activeMove: number | null;
  setActiveMove: (moveNumber: number | null) => void;
  nextMove: () => void;
  prevMove: () => void;

  // Beta type selection
  activeBetaType: BetaType;
  setActiveBetaType: (type: BetaType) => void;

  // UI state
  isAnalyzing: boolean;
  setIsAnalyzing: (v: boolean) => void;
  analysisProgress: string;
  setAnalysisProgress: (msg: string) => void;

  // Selected hold
  selectedHoldId: string | null;
  setSelectedHoldId: (id: string | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Profile
      currentProfile: null,
      setCurrentProfile: (profile) => set({ currentProfile: profile }),

      // Analysis
      analyses: [],
      currentAnalysis: null,
      setCurrentAnalysis: (analysis) => {
        set({ currentAnalysis: analysis, activeMove: 1 });
      },
      addAnalysis: (analysis) =>
        set((state) => ({
          analyses: [analysis, ...state.analyses].slice(0, 50), // keep last 50
        })),
      removeAnalysis: (id) =>
        set((state) => ({
          analyses: state.analyses.filter((a) => a.id !== id),
          currentAnalysis:
            state.currentAnalysis?.id === id ? null : state.currentAnalysis,
        })),

      // Move navigation
      activeMove: null,
      setActiveMove: (moveNumber) => set({ activeMove: moveNumber }),
      nextMove: () => {
        const state = get();
        const { currentAnalysis, activeMove, activeBetaType } = state;
        if (!currentAnalysis) return;
        const beta = currentAnalysis.betas.find((b) => b.beta_type === activeBetaType);
        if (!beta) return;
        const maxMove = beta.moves.length;
        if (activeMove !== null && activeMove < maxMove) {
          set({ activeMove: activeMove + 1 });
        }
      },
      prevMove: () => {
        const state = get();
        const { activeMove } = state;
        if (activeMove !== null && activeMove > 1) {
          set({ activeMove: activeMove - 1 });
        }
      },

      // Beta type
      activeBetaType: 'high_percentage',
      setActiveBetaType: (type) => set({ activeBetaType: type, activeMove: 1 }),

      // UI state
      isAnalyzing: false,
      setIsAnalyzing: (v) => set({ isAnalyzing: v }),
      analysisProgress: '',
      setAnalysisProgress: (msg) => set({ analysisProgress: msg }),

      // Hold selection
      selectedHoldId: null,
      setSelectedHoldId: (id) => set({ selectedHoldId: id }),
    }),
    {
      name: 'climb-beta-store',
      partialize: (state) => ({
        currentProfile: state.currentProfile,
        analyses: state.analyses.slice(0, 20), // persist last 20
        activeBetaType: state.activeBetaType,
      }),
    }
  )
);
