"use client";

import { useState } from "react";
import { Library, PlayCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { getLibraryPlayUrl } from "@/lib/api-client";
import { useLibrary } from "@/lib/queries";
import { statusBadgeClass } from "@/lib/job-format";

export function MediaLibrary() {
  const { data: clips, isLoading, error, refetch } = useLibrary();
  const [playing, setPlaying] = useState<{ key: string; url: string } | null>(null);

  const play = async (key: string) => {
    try {
      const { url } = await getLibraryPlayUrl(key);
      setPlaying({ key, url });
    } catch {
      setPlaying(null);
    }
  };

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }
  if (!clips || clips.length === 0) {
    return (
      <EmptyState
        icon={Library}
        title="Library is empty"
        description="Upload a source clip, then render it — clips and their renders appear here, scoped to this app's own folders."
      />
    );
  }

  return (
    <div className="space-y-4">
      {playing && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title truncate">{playing.key}</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <video
              src={playing.url}
              controls
              autoPlay
              loop
              playsInline
              className="w-full max-w-2xl rounded-md border border-border bg-black"
            />
          </CardContent>
        </Card>
      )}

      {clips.map((clip) => (
        <Card key={clip.key}>
          <CardContent className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium truncate">{clip.filename}</p>
                <p className="text-xs text-muted-foreground">
                  source · {clip.size_human}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => play(clip.key)}>
                <PlayCircle className="h-4 w-4" />
                Play source
              </Button>
            </div>

            {clip.renders.length > 0 ? (
              <ul className="mt-4 divide-y divide-border rounded-md border border-border">
                {clip.renders.map((r) => (
                  <li key={r.key} className="flex items-center justify-between gap-3 px-3 py-2">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{r.multiplier}x render</span>
                      <span className="text-muted-foreground">{r.size_human}</span>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${statusBadgeClass(r.status)}`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => play(r.key)}>
                      <PlayCircle className="h-4 w-4" />
                      Play
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-xs text-muted-foreground">
                No renders yet — create a job for this clip.
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
