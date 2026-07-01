"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Film } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useJobs } from "@/lib/queries";
import { jobHref, statusBadgeClass } from "@/lib/job-format";

// Dashboard "recent render jobs" table (replaces the starter's recent-uploads).
export function RecentUploadsTable() {
  const router = useRouter();
  const { data: jobs = [], isLoading, error, refetch } = useJobs();
  const recent = jobs.slice(0, 8);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Render Jobs</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Film}
            title="No render jobs yet"
            description="Create a render job to interpolate a clip into slow motion."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[40%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Clip
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Mult
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Amplification
                </TableHead>
                <TableHead className="w-[24%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((j) => (
                <TableRow
                  key={`${j.source_key}-${j.multiplier}`}
                  className="table-row-hover cursor-pointer"
                  onClick={() => router.push(jobHref(j.source_key, j.multiplier))}
                >
                  <TableCell className="font-medium">
                    <div className="truncate">{j.source_filename}</div>
                  </TableCell>
                  <TableCell className="tabular-nums whitespace-nowrap">{j.multiplier}x</TableCell>
                  <TableCell className="tabular-nums whitespace-nowrap">
                    {j.amplification_ratio !== null ? `${j.amplification_ratio}x` : "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(j.status)}`}
                    >
                      {j.status}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
