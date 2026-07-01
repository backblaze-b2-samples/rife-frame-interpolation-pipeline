import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Ingest a source video clip (MP4/MOV/WebM/MKV/AVI). Clips land under{" "}
          <code>source/clips/</code> on B2 and become the input to a RIFE render
          job. Up to 500 MB per file.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
