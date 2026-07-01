"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useRenderVolume } from "@/lib/queries";

const chartConfig = {
  render_mb: { label: "Render MB", color: "var(--chart-1)" },
} satisfies ChartConfig;

// The dashboard's render-output-volume-over-time chart (the write-amplification
// payload growing on B2). Reuses the starter's chart primitive.
export function UploadChart() {
  const { data: volume, isLoading, error, refetch } = useRenderVolume(14);

  const data = useMemo(
    () =>
      (volume ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        render_mb: Math.round((d.render_bytes / (1024 * 1024)) * 10) / 10,
      })),
    [volume],
  );

  const total = data.reduce((sum, d) => sum + d.render_mb, 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Render Output Volume</CardTitle>
        <CardDescription className="text-xs">
          MB written to B2 over the last 14 days · {total.toFixed(1)} MB total
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No renders yet"
            description="Run a render job to see output volume grow here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="render-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-render_mb)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-render_mb)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={32} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar
                dataKey="render_mb"
                fill="url(#render-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
