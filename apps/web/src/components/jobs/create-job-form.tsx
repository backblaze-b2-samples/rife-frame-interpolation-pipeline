"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useSources, useCreateJob } from "@/lib/queries";
import { jobHref } from "@/lib/job-format";
import { CODECS, MULTIPLIERS } from "@rife-frame-interpolation-pipeline/shared";

const schema = z.object({
  // Finite-value fields use SELECTORS (never free text):
  source_key: z.string().min(1, "Pick a source clip"),
  multiplier: z.coerce.number().refine((v) => MULTIPLIERS.includes(v as 2 | 4 | 8), {
    message: "Choose 2x, 4x or 8x",
  }),
  codec: z.enum(["h264", "h265"]),
});

type FormValues = z.infer<typeof schema>;

// Create-form safe defaults surfaced as GUIDANCE (placeholder / FormDescription,
// never an autofill button): default 2x + H.264.
const DEFAULTS: FormValues = {
  source_key: "",
  multiplier: 2,
  codec: "h264",
};

export function CreateJobForm() {
  const router = useRouter();
  const { data: sources = [] } = useSources();
  const create = useCreateJob();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULTS,
  });

  const selectedKey = form.watch("source_key");
  const selectedMultiplier = form.watch("multiplier");
  const selectedClip = sources.find((s) => s.key === selectedKey);

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      await create.mutateAsync({
        source_key: values.source_key,
        multiplier: values.multiplier as 2 | 4 | 8,
        codec: values.codec,
      });
      toast.success("Render job created — run it to interpolate");
      router.push(jobHref(values.source_key, values.multiplier));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">New render job</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <FormField
              control={form.control}
              name="source_key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Source clip</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full max-w-md">
                        <SelectValue placeholder="Select an uploaded clip…" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {sources.length === 0 ? (
                        <SelectItem value="__none" disabled>
                          No clips — upload one first
                        </SelectItem>
                      ) : (
                        sources.map((s) => (
                          <SelectItem key={s.key} value={s.key}>
                            {s.filename} ({s.size_human})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Clips you upload land under <code>source/clips/</code> on B2.
                    Start with a short clip at 2x for a fast first render.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="multiplier"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Frame-rate multiplier</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={(v) => field.onChange(Number(v))}
                      value={String(field.value)}
                      className="flex gap-6"
                    >
                      {MULTIPLIERS.map((m) => (
                        <label
                          key={m}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                        >
                          <RadioGroupItem value={String(m)} />
                          {m}x
                        </label>
                      ))}
                    </RadioGroup>
                  </FormControl>
                  <FormDescription>
                    Default 2x. Target fps = source fps x multiplier (computed on
                    run).
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="codec"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Output codec</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-60">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {CODECS.map((c) => (
                        <SelectItem key={c.value} value={c.value}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Default <strong>H.264 (MP4)</strong> — browser-playable. H.265
                    (HEVC) is smaller but may not play in Chrome.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Derived, read-only target fps hint (never a text input). */}
            <div className="rounded-md border border-border bg-muted/20 p-3 text-sm">
              <span className="text-muted-foreground">Target frame rate: </span>
              {selectedClip ? (
                <span className="font-medium">
                  source fps x {selectedMultiplier}x (measured when the render
                  runs)
                </span>
              ) : (
                <span className="text-muted-foreground">
                  pick a clip to preview
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create render job"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
