import { useState } from "react";
import { Loader2, Sparkles, ArrowRight, SkipForward, RefreshCw } from "lucide-react";
import { useUserStore } from "@/stores/userStore";
import { Button } from "@/components/ui/button";
import { trackEvent } from "@/lib/analytics";

type Step = "welcome" | "guide" | "error";

interface OnboardingFlowProps {
  onComplete: () => void;
}

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const updateMe = useUserStore((s) => s.updateMe);
  const [step, setStep] = useState<Step>("welcome");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleComplete() {
    setIsSubmitting(true);
    try {
      await updateMe({ onboarding_completed: true });
      trackEvent("onboarding_completed");
      onComplete();
    } catch {
      setStep("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRetry() {
    setStep("guide");
    await handleComplete();
  }

  function handleSkip() {
    // 跳过也标记完成
    handleComplete();
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/95 backdrop-blur-sm">
      <div className="w-full max-w-md mx-4 space-y-8 text-center">
        {/* Welcome Step */}
        {step === "welcome" && (
          <>
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/30">
                <Sparkles className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                欢迎来到个人成长助手
              </h1>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                记录想法、管理任务、追踪项目，让每一天的成长清晰可见。
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <Button
                onClick={() => setStep("guide")}
                className="gap-2"
                size="lg"
              >
                开始使用
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                onClick={handleSkip}
                disabled={isSubmitting}
                className="text-muted-foreground"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <SkipForward className="h-4 w-4" />
                )}
                跳过引导
              </Button>
            </div>
          </>
        )}

        {/* Guide Step */}
        {step === "guide" && (
          <>
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/30">
                <Sparkles className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                记录你的第一条想法
              </h2>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                点击左下角的对话框图标，输入任何你正在思考的事情。
                <br />
                比如：&ldquo;今天学了一个新概念&rdquo; 或 &ldquo;下周需要准备项目汇报&rdquo;。
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <Button
                onClick={handleComplete}
                disabled={isSubmitting}
                className="gap-2"
                size="lg"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                我准备好了
              </Button>
              <Button
                variant="ghost"
                onClick={handleSkip}
                disabled={isSubmitting}
                className="gap-2 text-muted-foreground"
              >
                <SkipForward className="h-4 w-4" />
                跳过
              </Button>
            </div>
          </>
        )}

        {/* Error Step */}
        {step === "error" && (
          <>
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                <RefreshCw className="h-8 w-8 text-red-600 dark:text-red-400" />
              </div>
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                引导状态保存失败
              </h2>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                网络异常，请重试或直接关闭。
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <Button
                onClick={handleRetry}
                className="gap-2"
                size="lg"
              >
                <RefreshCw className="h-4 w-4" />
                重试
              </Button>
              <Button
                variant="ghost"
                onClick={onComplete}
                className="text-muted-foreground"
              >
                关闭引导
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
