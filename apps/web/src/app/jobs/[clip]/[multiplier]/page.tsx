"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { JobDetail } from "@/components/jobs/job-detail";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ clip: string; multiplier: string }>;
}) {
  const { clip, multiplier } = use(params);
  const clipId = decodeURIComponent(clip);
  const mult = Number(multiplier);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to jobs
        </Link>
        <h1 className="page-title mt-2">
          {clipId} · {mult}x
        </h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Interpolation job detail — manifest, write amplification and render
          playback.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <JobDetail clipId={clipId} multiplier={mult} />
      </div>
    </div>
  );
}
