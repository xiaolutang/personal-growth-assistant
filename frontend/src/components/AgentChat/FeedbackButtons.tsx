import { useState, useCallback } from "react";
import { ThumbsUp, ThumbsDown, Flag } from "lucide-react";
import { cn } from "@/lib/utils";

/** 反馈数据 */
export interface FeedbackData {
  /** feedback 类型：positive / negative / flag */
  type: "positive" | "negative" | "flag";
  /** 预设选项 key（negative 时有值） */
  reason?: string;
  /** 用户补充说明（"其他"时填写） */
  detail?: string;
}

/** 负面反馈预设选项 */
const NEGATIVE_OPTIONS = [
  { key: "understanding_wrong", label: "理解错了" },
  { key: "action_incorrect", label: "操作不正确" },
  { key: "not_helpful", label: "回复没帮助" },
  { key: "should_ask_didnt", label: "应该追问没追问" },
  { key: "shouldnt_ask_did", label: "不该追问追问了" },
  { key: "other", label: "其他" },
] as const;

interface FeedbackButtonsProps {
  /** Agent 消息 ID */
  messageId: string;
  /** 反馈提交回调 */
  onSubmit: (feedback: FeedbackData) => void;
  /** 额外 className */
  className?: string;
}

type PanelType = "none" | "negative" | "flag";

export function FeedbackButtons({ messageId, onSubmit, className }: FeedbackButtonsProps) {
  const [activePanel, setActivePanel] = useState<PanelType>("none");
  const [submitted, setSubmitted] = useState(false);
  const [selectedReason, setSelectedReason] = useState<string | null>(null);
  const [otherText, setOtherText] = useState("");

  // 点击 👍 → 直接提交正面反馈
  const handlePositive = useCallback(() => {
    if (submitted) return;
    setSubmitted(true);
    onSubmit({ type: "positive" });
  }, [submitted, onSubmit]);

  // 点击 👎 → 展开/收起负面反馈面板
  const handleNegativeToggle = useCallback(() => {
    if (submitted) return;
    setActivePanel((prev) => (prev === "negative" ? "none" : "negative"));
  }, [submitted]);

  // 点击 ⚑ → 展开/收起标记面板
  const handleFlagToggle = useCallback(() => {
    if (submitted) return;
    setActivePanel((prev) => (prev === "flag" ? "none" : "flag"));
  }, [submitted]);

  // 提交负面反馈
  const handleNegativeSubmit = useCallback(() => {
    if (!selectedReason || submitted) return;
    const feedback: FeedbackData = {
      type: "negative",
      reason: selectedReason,
      detail: selectedReason === "other" ? otherText : undefined,
    };
    setSubmitted(true);
    onSubmit(feedback);
  }, [selectedReason, otherText, submitted, onSubmit]);

  // 提交标记
  const handleFlagSubmit = useCallback(() => {
    if (submitted) return;
    setSubmitted(true);
    onSubmit({ type: "flag" });
  }, [submitted, onSubmit]);

  // 按钮基础样式
  const btnBase =
    "h-7 w-7 inline-flex items-center justify-center rounded-md transition-colors";
  const btnGhost =
    "text-muted-foreground hover:text-foreground hover:bg-muted";
  const btnDisabled =
    "text-muted-foreground/40 cursor-not-allowed";

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {/* 按钮行 */}
      <div className="flex items-center gap-0.5">
        {/* 👍 */}
        <button
          type="button"
          onClick={handlePositive}
          disabled={submitted}
          className={cn(btnBase, submitted ? btnDisabled : btnGhost)}
          aria-label="赞"
          title="赞"
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>

        {/* 👎 */}
        <button
          type="button"
          onClick={handleNegativeToggle}
          disabled={submitted}
          className={cn(btnBase, submitted ? btnDisabled : btnGhost)}
          aria-label="踩"
          title="踩"
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>

        {/* ⚑ */}
        <button
          type="button"
          onClick={handleFlagToggle}
          disabled={submitted}
          className={cn(btnBase, submitted ? btnDisabled : btnGhost)}
          aria-label="标记"
          title="标记"
        >
          <Flag className="h-3.5 w-3.5" />
        </button>

        {submitted && (
          <span className="text-xs text-muted-foreground ml-1">已反馈</span>
        )}
      </div>

      {/* 负面反馈面板 */}
      {activePanel === "negative" && !submitted && (
        <div className="rounded-lg bg-muted/60 p-2.5 space-y-2 text-sm">
          <p className="text-xs text-muted-foreground font-medium">请选择问题类型：</p>
          <div className="space-y-1">
            {NEGATIVE_OPTIONS.map((opt) => (
              <label
                key={opt.key}
                className="flex items-center gap-2 cursor-pointer py-0.5"
              >
                <input
                  type="radio"
                  name={`feedback-reason-${messageId}`}
                  value={opt.key}
                  checked={selectedReason === opt.key}
                  onChange={() => setSelectedReason(opt.key)}
                  className="accent-[#6366F1]"
                />
                <span className="text-xs text-foreground">{opt.label}</span>
              </label>
            ))}
          </div>

          {/* "其他"输入框 */}
          {selectedReason === "other" && (
            <textarea
              value={otherText}
              onChange={(e) => setOtherText(e.target.value)}
              placeholder="请描述具体问题..."
              className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-[#6366F1] resize-none"
              rows={2}
            />
          )}

          <button
            type="button"
            onClick={handleNegativeSubmit}
            disabled={!selectedReason}
            className={cn(
              "w-full rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              selectedReason
                ? "bg-[#6366F1] text-white hover:bg-[#5558E6]"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            提交反馈
          </button>
        </div>
      )}

      {/* 标记面板 */}
      {activePanel === "flag" && !submitted && (
        <div className="rounded-lg bg-muted/60 p-2.5 space-y-2 text-sm">
          <p className="text-xs text-muted-foreground">标记此回复不当</p>
          <button
            type="button"
            onClick={handleFlagSubmit}
            className="w-full rounded-md px-3 py-1.5 text-xs font-medium bg-[#6366F1] text-white hover:bg-[#5558E6] transition-colors"
          >
            提交标记
          </button>
        </div>
      )}
    </div>
  );
}
