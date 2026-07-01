export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Video-specific — fps is load-bearing (target-fps + amplification).
  fps: number | null;
  duration_seconds: number | null;
  codec: string | null;
  video_width: number | null;
  video_height: number | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Interpolation pipeline ---

export type JobStatus = "pending" | "running" | "completed" | "failed";
export type Multiplier = 2 | 4 | 8;
export type Codec = "h264" | "h265";

export interface JobConfig {
  source_key: string;
  multiplier: Multiplier;
  codec: Codec;
}

export interface InterpolationJob {
  job_id: string;
  config: JobConfig;
  status: JobStatus;
  source_fps: number | null;
  target_fps: number | null;
  source_bytes: number;
  render_bytes: number;
  amplification_ratio: number | null;
  render_key: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface JobSummary {
  job_id: string;
  source_key: string;
  source_filename: string;
  multiplier: number;
  codec: string;
  status: JobStatus;
  source_bytes: number;
  render_bytes: number;
  amplification_ratio: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface RunProgress {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string | null;
  error: string | null;
  updated_at: string;
}

export interface DashboardStats {
  total_source_bytes: number;
  total_source_human: string;
  total_render_bytes: number;
  total_render_human: string;
  write_amplification_ratio: number;
  jobs_completed: number;
  jobs_total: number;
  fps_minutes_processed: number;
}

export interface RenderVolumePoint {
  date: string;
  render_bytes: number;
}

export interface SourceClip {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
}

export interface LibraryRender {
  key: string;
  multiplier: number;
  size_bytes: number;
  size_human: string;
  status: JobStatus;
  job_id: string | null;
}

export interface LibraryClip {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
  renders: LibraryRender[];
}

// Finite create-form options (selectors, not free text).
export const MULTIPLIERS: Multiplier[] = [2, 4, 8];
export const CODECS: { value: Codec; label: string }[] = [
  { value: "h264", label: "H.264 (MP4)" },
  { value: "h265", label: "H.265 (HEVC)" },
];
