"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Film, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useJobs, useDeleteJob, useRunJob, useJobProgress } from "@/lib/queries";
import { clipIdFor, jobHref, statusBadgeClass } from "@/lib/job-format";
import type { JobSummary } from "@rife-frame-interpolation-pipeline/shared";

export function JobsList() {
  const router = useRouter();
  const { data: jobs, isLoading, error, refetch } = useJobs();
  const anyRunning = (jobs ?? []).some((j) => j.status === "running" || j.status === "pending");
  useJobProgress(anyRunning); // poll live progress while a render is in flight
  const runJob = useRunJob();
  const deleteJob = useDeleteJob();
  const [pendingDelete, setPendingDelete] = useState<JobSummary | null>(null);

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 p-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <EmptyState
        icon={Film}
        title="No render jobs yet"
        description="Create a render job to interpolate a source clip into high-frame-rate slow motion."
        action={
          <Button asChild size="sm">
            <Link href="/jobs/new">New render job</Link>
          </Button>
        }
      />
    );
  }

  const onRun = async (j: JobSummary) => {
    try {
      await runJob.mutateAsync({ clipId: clipIdFor(j.source_key), multiplier: j.multiplier });
      toast.success("Render started");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Run failed");
    }
  };

  const onConfirmDelete = async () => {
    const j = pendingDelete;
    setPendingDelete(null);
    if (!j) return;
    try {
      await deleteJob.mutateAsync({ clipId: clipIdFor(j.source_key), multiplier: j.multiplier });
      toast.success("Job deleted");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source clip</TableHead>
              <TableHead>Multiplier</TableHead>
              <TableHead>Codec</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Amplification</TableHead>
              <TableHead className="w-[1%]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((j) => (
              <TableRow
                key={`${j.source_key}-${j.multiplier}`}
                className="cursor-pointer"
                onClick={() => router.push(jobHref(j.source_key, j.multiplier))}
              >
                <TableCell className="font-medium">{j.source_filename}</TableCell>
                <TableCell>{j.multiplier}x</TableCell>
                <TableCell className="uppercase text-xs">{j.codec}</TableCell>
                <TableCell>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(j.status)}`}
                  >
                    {j.status}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {j.amplification_ratio !== null ? `${j.amplification_ratio}x` : "—"}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      aria-label="Run render"
                      disabled={j.status === "running"}
                      onClick={() => onRun(j)}
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      aria-label="Delete job"
                      onClick={() => setPendingDelete(j)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>

      <AlertDialog
        open={!!pendingDelete}
        onOpenChange={(open) => !open && setPendingDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this render job?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete
                ? `This removes the ${pendingDelete.multiplier}x render of ${pendingDelete.source_filename} from B2 (scoped to the job's own prefix). The source clip is not affected.`
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onConfirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
