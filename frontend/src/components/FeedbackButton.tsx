import { useEffect, useMemo, useState } from "react";
import { Loader2, MessageSquare, Send } from "lucide-react";

import { submitFeedback, type FeedbackSeverity, ApiError } from "@/services/api";
import { useChatStore } from "@/stores/chatStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const FLOATING_GAP = 16;

const severityOptions: Array<{ value: FeedbackSeverity; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const initialForm = {
  title: "",
  description: "",
  severity: "medium" as FeedbackSeverity,
};

export function FeedbackButton() {
  const panelHeight = useChatStore((state) => state.panelHeight);
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [form, setForm] = useState(initialForm);

  const containerStyle = useMemo(
    () => ({ bottom: `${panelHeight + FLOATING_GAP}px` }),
    [panelHeight],
  );

  useEffect(() => {
    if (!isSuccess) return;

    const timer = window.setTimeout(() => {
      setIsOpen(false);
      setIsSuccess(false);
      setForm(initialForm);
    }, 1500);

    return () => window.clearTimeout(timer);
  }, [isSuccess]);

  const isTitleEmpty = form.title.trim().length === 0;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isTitleEmpty || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      await submitFeedback({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        severity: form.severity,
      });
      setIsSuccess(true);
    } catch (error) {
      const message = error instanceof ApiError
        ? error.toUserMessage()
        : "反馈提交失败，请稍后重试";
      setErrorMessage(message);
      setIsSuccess(false);
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleOpen() {
    setIsOpen((open) => !open);
    setErrorMessage("");
    setIsSuccess(false);
  }

  return (
    <div
      className="fixed right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col items-end gap-3 sm:right-6"
      style={containerStyle}
      data-testid="feedback-container"
    >
      {isOpen && (
        <form
          onSubmit={handleSubmit}
          className="w-full rounded-2xl border border-border bg-background/95 p-4 shadow-xl backdrop-blur"
        >
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">提交反馈</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                问题会通过 log-service Issue API 进入反馈队列。
              </p>
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={toggleOpen}>
              关闭
            </Button>
          </div>

          <div className="space-y-3">
            <label className="block text-sm font-medium">
              标题
              <Input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="例如：搜索结果加载缓慢"
                className="mt-1"
                maxLength={120}
              />
            </label>

            <label className="block text-sm font-medium">
              严重程度
              <select
                value={form.severity}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  severity: event.target.value as FeedbackSeverity,
                }))}
                className="mt-1 flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                {severityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium">
              描述
              <Textarea
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="补充复现步骤、影响范围或期望行为"
                className="mt-1 min-h-[112px]"
              />
            </label>
          </div>

          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="min-h-5 text-xs">
              {errorMessage && <p className="text-destructive">{errorMessage}</p>}
              {isSuccess && <p className="text-emerald-600">反馈已提交，我们会尽快处理。</p>}
            </div>
            <Button type="submit" disabled={isTitleEmpty || isSubmitting} className="gap-2">
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              提交
            </Button>
          </div>
        </form>
      )}

      <Button
        type="button"
        size="icon"
        onClick={toggleOpen}
        className="h-12 w-12 rounded-full shadow-lg"
        aria-label={isOpen ? "关闭反馈表单" : "打开反馈表单"}
      >
        <MessageSquare className="h-5 w-5" />
      </Button>
    </div>
  );
}
