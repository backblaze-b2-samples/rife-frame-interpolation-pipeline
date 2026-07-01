"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import { DangerZone } from "./danger-zone";
import { CODECS, MULTIPLIERS } from "@rife-frame-interpolation-pipeline/shared";

// These preferences are demo-only (no API) — they mirror the create-job form's
// finite-value selector UX so a clone has a working exemplar for its own forms.
const settingsSchema = z.object({
  displayName: z
    .string()
    .min(2, "Display name must be at least 2 characters")
    .max(50),
  bio: z.string().max(160, "Bio must be 160 characters or fewer").optional(),
  defaultMultiplier: z.coerce.number(),
  defaultCodec: z.enum(["h264", "h265"]),
});

type SettingsValues = z.infer<typeof settingsSchema>;

const defaultValues: SettingsValues = {
  displayName: "Anonymous",
  bio: "",
  defaultMultiplier: 2,
  defaultCodec: "h264",
};

export function SettingsForm() {
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues,
  });

  const onSubmit = async (values: SettingsValues) => {
    setSubmitting(true);
    // Demo-only — wire to a real API endpoint when you add one
    await new Promise((r) => setTimeout(r, 400));
    setSubmitting(false);
    toast.success("Settings saved", {
      description: `Default render: ${values.defaultMultiplier}x, ${values.defaultCodec.toUpperCase()}`,
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Profile */}
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Profile</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <FormField
              control={form.control}
              name="displayName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display name</FormLabel>
                  <FormControl>
                    <Input placeholder="Your name" {...field} />
                  </FormControl>
                  <FormDescription>
                    Shown in activity logs and share links.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="bio"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Bio</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="A short description of this workspace"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>Max 160 characters.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* Interpolation defaults */}
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Interpolation defaults</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <FormField
              control={form.control}
              name="defaultMultiplier"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Default multiplier</FormLabel>
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
                    Pre-selected in the New render job form. Default 2x.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="defaultCodec"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Default codec</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                    H.264 (MP4) is browser-playable and the safe default.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <DangerZone />

        {/* Action bar */}
        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => form.reset(defaultValues)}
          >
            Reset
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
