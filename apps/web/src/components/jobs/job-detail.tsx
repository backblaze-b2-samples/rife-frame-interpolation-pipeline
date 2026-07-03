"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  useJob,
  useJobProgress,
  useRenderUrl,
  useRunJob,
  useDeleteJob,
} from "@/lib/queries";
import { statusBadgeClass } from "@/lib/job-format";

function fmtBytes(n: number): string {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${u[i]}`;
}

export function JobDetail({ clipId, multiplier }: { clipId: string; multiplier: number }) {
  const router = useRouter();
  const { data: job, isLoading, error, refetch } = useJob(clipId, multiplier, true);
  // Poll run-progress whenever the manifest is non-terminal. The manifest stays
  // "pending" for the whole render (it only flips to completed/failed at the
  // end), so this keeps live progress polling while a render is in flight — but
  // it does NOT by itself mean a render is underway (see isRendering below).
  const isBusy = job?.status === "running" || job?.status === "pending";
  const { data: progress } = useJobProgress(isBusy);
  const runJob = useRunJob();
  // Run is only blocked while a render is actively in flight — never for a
  // freshly-created "pending" job, which must be startable from the UI.
  const isRunning = job?.status === "running" || runJob.isPending;
  const deleteJob = useDeleteJob();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const live = progress?.find((p) => p.job_id === job?.job_id);
  // A render is actually underway only when the ephemeral run-progress registry
  // holds a live, non-terminal entry for THIS job. That entry is created solely
  // when a run is enqueued (progress.start), so a freshly-created "pending" job
  // that was never run has none — it shows the idle/ready state, not this card.
  // runJob.isPending bridges the brief click->first-poll gap right after "Run".
  const isRendering =
    runJob.isPending ||
    live?.status === "running" ||
    live?.status === "pending";
  // Created but never run: a pending manifest with no active render. Gets a
  // ready-to-run hint instead of the (misleading) in-progress card.
  const isIdle = job?.status === "pending" && !isRendering;
  const canPlay = job?.status === "completed" && !!job.render_key;
  const { data: render } = useRenderUrl(clipId, multiplier, canPlay);

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (isLoading || !job) {
    return <Skeleton className="h-64 w-full" />;
  }

  const onRun = async () => {
    try {
      await runJob.mutateAsync({ clipId, multiplier });
      toast.success("Render started");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Run failed");
    }
  };

  const onDelete = async () => {
    setConfirmingDelete(false);
    try {
      await deleteJob.mutateAsync({ clipId, multiplier });
      toast.success("Job deleted");
      router.push("/jobs");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const rows: [string, string][] = [
    ["Source clip", job.config.source_key],
    ["Multiplier", `${job.config.multiplier}x`],
    ["Codec", job.config.codec.toUpperCase()],
    ["Source fps", job.source_fps !== null ? `${job.source_fps}` : "—"],
    ["Target fps", job.target_fps !== null ? `${job.target_fps}` : "—"],
    ["Source size", fmtBytes(job.source_bytes)],
    ["Render size", fmtBytes(job.render_bytes)],
    ["Created", new Date(job.created_at).toLocaleString()],
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span
          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(job.status)}`}
        >
          {job.status}
        </span>
        <div className="flex gap-2">
          <Button size="sm" onClick={onRun} disabled={isRunning}>
            <Play className="h-4 w-4" />
            {job.status === "completed" ? "Re-run" : "Run"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-destructive"
            onClick={() => setConfirmingDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this render job?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the job manifest and its render output from B2, scoped
              to this job&apos;s own prefix. The source clip is not affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Hero: write-amplification ratio (render bytes / source bytes). */}
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Write amplification</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <div className="stat-value text-3xl">
            {job.amplification_ratio !== null ? `${job.amplification_ratio}x` : "—"}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {fmtBytes(job.render_bytes)} rendered from {fmtBytes(job.source_bytes)} source — the
            classic write-heavy B2 workload.
          </p>
        </CardContent>
      </Card>

      {isIdle && (
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">
              This job is ready but hasn&apos;t run yet. Click{" "}
              <span className="font-medium text-foreground">Run</span> to
              interpolate the source clip and render the slow-motion output.
            </p>
          </CardContent>
        </Card>
      )}

      {isRendering && (
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">
              {live?.message ?? "Render in progress…"}
            </p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.round((live?.progress ?? 0.05) * 100)}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {job.status === "failed" && job.error && (
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-destructive">{job.error}</p>
          </CardContent>
        </Card>
      )}

      {canPlay && render?.url && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Rendered slow motion</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <video
              src={render.url}
              controls
              loop
              playsInline
              className="w-full max-w-2xl rounded-md border border-border bg-black"
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Manifest</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <dl className="divide-y divide-border">
            {rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 px-5 py-3 text-sm">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="break-all text-right font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
