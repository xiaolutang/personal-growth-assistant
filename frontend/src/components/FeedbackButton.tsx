import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, MessageSquare, Send } from "lucide-react";

import {
  submitFeedback,
  getFeedbackList,
  syncFeedback,
  type FeedbackSeverity,
  type FeedbackItem,
  ApiError,
} from "@/services/api";
import { useAgentStore } from "@/stores/agentStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useIsMobile } from "@/hooks/useIsMobile";

const FLOATING_GAP = 16;
const MOBILE_NAV_HEIGHT = 56; // h-14 = 56px

type ActiveTab = "submit" | "list";

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

const statusColors: Record<string, string> = {
  pending: "text-amber-500 dark:text-amber-400",
  reported: "text-blue-600 dark:text-blue-400",
  in_progress: "text-yellow-500 dark:text-yellow-400",
  resolved: "text-emerald-600 dark:text-emerald-400",
};

const statusLabels: Record<string, string> = {
  pending: "待处理",
  reported: "已上报",
  in_progress: "处理中",
  resolved: "已解决",
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function FeedbackButton() {
  const panelHeight = useAgentStore((state) => state.panelHeight);
  const isMobile = useIsMobile();
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("submit");

  // submit state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [form, setForm] = useState(initialForm);

  // list state
  const [feedbackList, setFeedbackList] = useState<FeedbackItem[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [listError, setListError] = useState(false);

  const containerStyle = useMemo(
    () => ({
      bottom: `${panelHeight + FLOATING_GAP + (isMobile ? MOBILE_NAV_HEIGHT : 0)}px`,
    }),
    [panelHeight, isMobile],
  );

  useEffect(() => {
    if (!isSuccess) return;

    const timer = window.setTimeout(() => {
      setIsSuccess(false);
      setForm(initialForm);
      // auto-switch to list tab — useEffect will handle loading
      setActiveTab("list");
    }, 1200);

    return () => window.clearTimeout(timer);
  }, [isSuccess]);

  const [isSyncing, setIsSyncing] = useState(false);

  const loadFeedbackList = useCallback(async () => {
    setIsLoadingList(true);
    setListError(false);
    try {
      const data = await getFeedbackList();
      setFeedbackList(data.items);
    } catch {
      setListError(true);
    } finally {
      setIsLoadingList(false);
    }
  }, []);

  // sync + load list when switching to list tab
  useEffect(() => {
    if (!isOpen || activeTab !== "list") return;
    let cancelled = false;

    const syncAndLoad = async () => {
      // try sync first (non-blocking on failure)
      setIsSyncing(true);
      try {
        const syncResult = await syncFeedback();
        if (!cancelled && syncResult.items.length > 0) {
          setFeedbackList(syncResult.items);
          setIsSyncing(false);
          return; // sync data is freshest, skip loading
        }
      } catch {
        // sync failed, fall through to loading from local
      }
      if (!cancelled) setIsSyncing(false);

      // load from local as fallback
      await loadFeedbackList();
    };

    syncAndLoad();
    return () => { cancelled = true; };
  }, [isOpen, activeTab, loadFeedbackList]);

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
        feedback_type: "general",
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

  const tabClass = (tab: ActiveTab) =>
    `flex-1 py-2 text-xs font-medium border-b-2 transition-colors ${
      activeTab === tab
        ? "border-indigo-500 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400"
        : "border-transparent text-muted-foreground hover:text-foreground"
    }`;

  return (
    <div
      className="fixed right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col items-end gap-3 sm:right-6"
      style={containerStyle}
      data-testid="feedback-container"
    >
      {isOpen && (
        <div className="w-full rounded-2xl border border-border bg-background/95 shadow-xl backdrop-blur">
          {/* Tab header */}
          <div className="flex border-b border-border">
            <button
              type="button"
              className={tabClass("submit")}
              onClick={() => setActiveTab("submit")}
            >
              提交反馈
            </button>
            <button
              type="button"
              className={tabClass("list")}
              onClick={() => setActiveTab("list")}
            >
              我的反馈
            </button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="ml-auto mr-1 mt-1 h-7 text-xs"
              onClick={toggleOpen}
            >
              关闭
            </Button>
          </div>

          {/* Submit tab */}
          {activeTab === "submit" && (
            <form onSubmit={handleSubmit} className="p-4">
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
                    className="mt-1 min-h-[80px]"
                  />
                </label>
              </div>

              <div className="mt-4 flex items-center justify-between gap-3">
                <div className="min-h-5 text-xs">
                  {errorMessage && <p className="text-destructive">{errorMessage}</p>}
                  {isSuccess && <p className="text-emerald-600 dark:text-emerald-400">反馈已提交，我们会尽快处理。</p>}
                </div>
                <Button type="submit" disabled={isTitleEmpty || isSubmitting} className="gap-2">
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  提交
                </Button>
              </div>
            </form>
          )}

          {/* List tab */}
          {activeTab === "list" && (
            <div className="p-4 max-h-[360px] overflow-y-auto">
              {isSyncing ? (
                <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  同步中…
                </div>
              ) : null}
              {!isSyncing && isLoadingList ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : listError ? (
                <div className="py-8 text-center">
                  <p className="text-sm text-destructive">加载失败，请重试</p>
                  <Button type="button" variant="outline" size="sm" className="mt-2" onClick={loadFeedbackList}>
                    重试
                  </Button>
                </div>
              ) : feedbackList.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  暂无反馈记录
                </p>
              ) : (
                <ul className="space-y-2">
                  {feedbackList.map((item) => (
                    <li
                      key={item.id}
                      className="rounded-lg border border-border p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium leading-tight line-clamp-2">
                          {item.title}
                        </p>
                        <span
                          className={`shrink-0 text-xs font-medium ${statusColors[item.status] ?? "text-muted-foreground"}`}
                        >
                          {statusLabels[item.status] ?? item.status}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatTime(item.created_at)}
                        {item.updated_at && (
                          <span className="ml-2">
                            · 更新于 {formatTime(item.updated_at)}
                          </span>
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      <Button
        type="button"
        size="icon"
        onClick={toggleOpen}
        className="h-12 w-12 rounded-full shadow-lg"
        aria-label={isOpen ? "关闭反馈面板" : "打开反馈面板"}
      >
        <MessageSquare className="h-5 w-5" />
      </Button>
    </div>
  );
}
