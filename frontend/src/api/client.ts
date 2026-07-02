import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  AnalysisResult,
  AnalysisSummary,
  ClimberProfile,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 120_000, // 2 min — vision pipeline can take time
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — add correlation ID for debugging
api.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID();
  return config;
});

// Response interceptor — normalize errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string }>) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'Unknown API error';
    throw new ApiError(message, error.response?.status ?? 0, error);
  }
);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly cause?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ---- Analysis ----

export async function uploadImages(
  files: File[],
  options: {
    climberProfileId?: string;
    boardType?: string;
    notes?: string;
    betaTypes?: string[];
  } = {}
): Promise<AnalysisResult> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (options.climberProfileId) {
    formData.append('climber_profile_id', options.climberProfileId);
  }
  formData.append('board_type', options.boardType ?? 'unknown');
  if (options.notes) formData.append('notes', options.notes);
  formData.append(
    'beta_types',
    (options.betaTypes ?? ['high_percentage', 'energy_efficient']).join(',')
  );

  const { data } = await api.post<AnalysisResult>('/api/v1/analysis/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  const { data } = await api.get<AnalysisResult>(`/api/v1/analysis/${id}`);
  return data;
}

export async function listAnalyses(): Promise<AnalysisSummary[]> {
  const { data } = await api.get<AnalysisSummary[]>('/api/v1/analysis/');
  return data;
}

export async function deleteAnalysis(id: string): Promise<void> {
  await api.delete(`/api/v1/analysis/${id}`);
}

// ---- Profiles ----

export async function listProfiles(): Promise<ClimberProfile[]> {
  const { data } = await api.get<ClimberProfile[]>('/api/v1/profiles/');
  return data;
}

export async function getProfile(id: string): Promise<ClimberProfile> {
  const { data } = await api.get<ClimberProfile>(`/api/v1/profiles/${id}`);
  return data;
}

export async function createProfile(
  profile: Omit<ClimberProfile, 'id' | 'ape_index' | 'max_comfortable_reach_cm'>
): Promise<ClimberProfile> {
  const { data } = await api.post<ClimberProfile>('/api/v1/profiles/', {
    ...profile,
    id: `profile_${Date.now()}`,
  });
  return data;
}

export async function updateProfile(
  id: string,
  updates: Partial<ClimberProfile>
): Promise<ClimberProfile> {
  const { data } = await api.put<ClimberProfile>(`/api/v1/profiles/${id}`, {
    ...updates,
    id,
  });
  return data;
}

export async function deleteProfile(id: string): Promise<void> {
  await api.delete(`/api/v1/profiles/${id}`);
}

export async function getDefaultProfile(): Promise<ClimberProfile> {
  const { data } = await api.get<ClimberProfile>('/api/v1/profiles/default/profile');
  return data;
}

// ---- Health ----

export async function getHealth(): Promise<{ status: string; version: string }> {
  const { data } = await api.get('/health');
  return data;
}

// ---- Image URL helper ----

export function getImageUrl(imagePath: string): string {
  // Convert absolute path to relative URL via static files
  const filename = imagePath.split('/').slice(-2).join('/'); // last 2 segments: analysis_id/filename
  return `${API_BASE}/static/uploads/${filename}`;
}

export default {
  uploadImages,
  getAnalysis,
  listAnalyses,
  deleteAnalysis,
  listProfiles,
  getProfile,
  createProfile,
  updateProfile,
  deleteProfile,
  getDefaultProfile,
  getHealth,
  getImageUrl,
};
