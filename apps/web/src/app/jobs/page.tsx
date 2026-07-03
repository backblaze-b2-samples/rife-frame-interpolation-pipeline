import Link from "next/link";
import { Film } from "lucide-react";

import { Button } from "@/components/ui/button";
import { JobsList } from "@/components/jobs/jobs-list";

export default function JobsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Render Jobs</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            RIFE interpolation jobs — each turns a source clip into a
            smooth slow-motion render stored on B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/jobs/new">
            <Film aria-hidden="true" className="h-3.5 w-3.5" />
            New render job
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <JobsList />
      </div>
    </div>
  );
}
