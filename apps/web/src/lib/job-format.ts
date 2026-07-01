import type { JobStatus } from "@rife-frame-interpolation-pipeline/shared";

/** Stable, filesystem-safe clip id from a source key — mirrors the backend
 * (services/api/app/service/jobs.py::clip_id_for) so the UI can build the
 * /jobs/<clipId>/<multiplier> route from a job's source_key. */
export function clipIdFor(sourceKey: string): string {
  const base = sourceKey.split("/").pop() ?? sourceKey;
  const stem = base.includes(".") ? base.slice(0, base.lastIndexOf(".")) : base;
  const safe = stem.replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return safe || "clip";
}

export function jobHref(sourceKey: string, multiplier: number): string {
  return `/jobs/${encodeURIComponent(clipIdFor(sourceKey))}/${multiplier}`;
}

const STATUS_STYLES: Record<JobStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  running: "bg-[var(--attention)]/15 text-[var(--attention)]",
  completed: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  failed: "bg-destructive/15 text-destructive",
};

export function statusBadgeClass(status: JobStatus): string {
  return STATUS_STYLES[status] ?? STATUS_STYLES.pending;
}

export function humanBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = bytes;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}
