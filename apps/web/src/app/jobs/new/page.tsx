import { CreateJobForm } from "@/components/jobs/create-job-form";

export default function NewJobPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New Render Job</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Pick a source clip, a frame-rate multiplier and a codec. A render job
          is an immutable record of that transformation — to change parameters,
          create a new job.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CreateJobForm />
      </div>
    </div>
  );
}
