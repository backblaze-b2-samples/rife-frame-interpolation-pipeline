"use client";

import { TrendingUp, HardDrive, Film, Gauge } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useDashboardStats } from "@/lib/queries";

export function StatsCards() {
  const { data: stats, isLoading, error, refetch } = useDashboardStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      // The hero metric — render bytes / source bytes.
      title: "Write Amplification",
      value: stats ? `${stats.write_amplification_ratio}x` : "—",
      icon: TrendingUp,
    },
    {
      title: "Source Ingested",
      value: stats?.total_source_human ?? "0 B",
      icon: HardDrive,
    },
    {
      title: "Render Output",
      value: stats?.total_render_human ?? "0 B",
      icon: Film,
    },
    {
      title: "Jobs Completed",
      value: stats ? `${stats.jobs_completed} / ${stats.jobs_total}` : "0",
      icon: Gauge,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card key={card.title} className={`card-hover animate-fade-in-up stagger-${i + 1}`}>
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
