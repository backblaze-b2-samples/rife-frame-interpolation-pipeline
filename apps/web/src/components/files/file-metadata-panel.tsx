"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { FileMetadataDetail } from "@rife-frame-interpolation-pipeline/shared";

interface FileMetadataPanelProps {
  metadata: FileMetadataDetail;
}

function MetaRow({ label, value }: { label: string; value: string | number }) {
  const displayValue = value === "" ? "none" : String(value);

  return (
    <div className="grid min-w-0 grid-cols-[minmax(6rem,0.45fr)_minmax(0,1fr)] gap-3 text-sm">
      <span className="min-w-0 text-muted-foreground">{label}</span>
      <span
        className="min-w-0 break-all text-right font-mono text-xs tabular-nums text-foreground sm:text-sm"
        title={displayValue}
      >
        {displayValue}
      </span>
    </div>
  );
}

function formatTimestamp(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function FileMetadataPanel({ metadata }: FileMetadataPanelProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3 px-5 pt-5">
        <CardTitle className="card-title">File Details</CardTitle>
      </CardHeader>
      <CardContent className="min-w-0 space-y-3 px-5 pb-5">
        <MetaRow label="Filename" value={metadata.filename} />
        <MetaRow label="Size" value={metadata.size_human} />
        <MetaRow label="Type" value={metadata.mime_type} />
        <MetaRow label="Extension" value={metadata.extension || "none"} />

        <Separator />
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Checksums
        </p>
        <MetaRow label="MD5" value={metadata.md5} />
        <MetaRow label="SHA-256" value={metadata.sha256} />

        {/* Video metadata — fps is load-bearing (drives target-fps + amplification) */}
        {(metadata.fps !== null ||
          metadata.duration_seconds !== null ||
          metadata.video_width !== null) && (
          <>
            <Separator />
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Video
            </p>
            {metadata.fps !== null && (
              <MetaRow label="Frame rate" value={`${metadata.fps} fps`} />
            )}
            {metadata.video_width !== null && metadata.video_height !== null && (
              <MetaRow
                label="Resolution"
                value={`${metadata.video_width} x ${metadata.video_height}`}
              />
            )}
            {metadata.duration_seconds !== null && (
              <MetaRow
                label="Duration"
                value={`${metadata.duration_seconds.toFixed(1)}s`}
              />
            )}
            {metadata.codec && <MetaRow label="Codec" value={metadata.codec} />}
            {metadata.bitrate && (
              <MetaRow label="Bitrate" value={`${metadata.bitrate} bps`} />
            )}
          </>
        )}

        <Separator />
        <MetaRow
          label="Uploaded"
          value={formatTimestamp(metadata.uploaded_at)}
        />
      </CardContent>
    </Card>
  );
}
