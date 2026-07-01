"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createJob,
  deleteFile,
  deleteJob,
  getDashboardStats,
  getFiles,
  getFileStats,
  getJob,
  getJobProgress,
  getJobs,
  getLibrary,
  getPreviewUrl,
  getRenderUrl,
  getRenderVolume,
  getSources,
  getUploadActivity,
  runJob,
} from "@/lib/api-client";
import type {
  DashboardStats,
  FileMetadata,
  InterpolationJob,
  JobConfig,
  JobSummary,
  LibraryClip,
  RenderVolumePoint,
  RunProgress,
  SourceClip,
} from "@rife-frame-interpolation-pipeline/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  jobs: () => [...qk.all, "jobs"] as const,
  job: (clipId: string, multiplier: number) =>
    [...qk.all, "jobs", clipId, multiplier] as const,
  jobProgress: () => [...qk.all, "jobs", "progress"] as const,
  dashboardStats: () => [...qk.all, "jobs", "stats"] as const,
  renderVolume: (days: number) => [...qk.all, "jobs", "volume", days] as const,
  sources: () => [...qk.all, "jobs", "sources"] as const,
  library: () => [...qk.all, "library"] as const,
  renderUrl: (clipId: string, multiplier: number) =>
    [...qk.all, "jobs", clipId, multiplier, "render"] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Interpolation jobs ---

export function useSources() {
  return useQuery<SourceClip[], ApiError>({
    queryKey: qk.sources(),
    queryFn: getSources,
  });
}

export function useDashboardStats() {
  return useQuery<DashboardStats, ApiError>({
    queryKey: qk.dashboardStats(),
    queryFn: getDashboardStats,
  });
}

export function useRenderVolume(days = 14) {
  return useQuery<RenderVolumePoint[], ApiError>({
    queryKey: qk.renderVolume(days),
    queryFn: () => getRenderVolume(days),
  });
}

export function useJobs() {
  return useQuery<JobSummary[], ApiError>({
    queryKey: qk.jobs(),
    queryFn: getJobs,
  });
}

export function useJob(
  clipId: string | undefined,
  multiplier: number | undefined,
  poll = false,
) {
  return useQuery<InterpolationJob, ApiError>({
    queryKey: qk.job(clipId ?? "", multiplier ?? 0),
    queryFn: () => getJob(clipId as string, multiplier as number),
    enabled: !!clipId && multiplier !== undefined,
    refetchInterval: poll ? 2000 : false,
  });
}

// Polls while any render is still in flight so progress bars refresh live.
export function useJobProgress(poll = false) {
  return useQuery<RunProgress[], ApiError>({
    queryKey: qk.jobProgress(),
    queryFn: getJobProgress,
    refetchInterval: poll ? 2000 : false,
  });
}

export function useRenderUrl(
  clipId: string | undefined,
  multiplier: number | undefined,
  enabled: boolean,
) {
  return useQuery({
    queryKey: qk.renderUrl(clipId ?? "", multiplier ?? 0),
    queryFn: () => getRenderUrl(clipId as string, multiplier as number),
    enabled: enabled && !!clipId && multiplier !== undefined,
    staleTime: 60_000,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation<InterpolationJob, ApiError, JobConfig>({
    mutationFn: (config) => createJob(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs() });
      qc.invalidateQueries({ queryKey: qk.dashboardStats() });
    },
  });
}

export function useRunJob() {
  const qc = useQueryClient();
  return useMutation<
    RunProgress,
    ApiError,
    { clipId: string; multiplier: number }
  >({
    mutationFn: ({ clipId, multiplier }) => runJob(clipId, multiplier),
    onSuccess: (_run, { clipId, multiplier }) => {
      qc.invalidateQueries({ queryKey: qk.jobProgress() });
      qc.invalidateQueries({ queryKey: qk.job(clipId, multiplier) });
      qc.invalidateQueries({ queryKey: qk.jobs() });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation<
    { deleted: boolean; clip_id: string; multiplier: number },
    ApiError,
    { clipId: string; multiplier: number }
  >({
    mutationFn: ({ clipId, multiplier }) => deleteJob(clipId, multiplier),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Scoped media library ---

export function useLibrary() {
  return useQuery<LibraryClip[], ApiError>({
    queryKey: qk.library(),
    queryFn: getLibrary,
  });
}
