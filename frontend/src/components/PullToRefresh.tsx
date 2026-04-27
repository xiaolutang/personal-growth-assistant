import { useState, useRef, useCallback, useEffect, type ReactNode } from "react";
import { ChevronDown, Check } from "lucide-react";

type RefreshState = "idle" | "pulling" | "refreshing" | "success";

interface PullToRefreshProps {
  /** Distance (px) the user must pull to trigger refresh. Default 80. */
  pullThreshold?: number;
  /** Async callback invoked when refresh is triggered. Must return a Promise. */
  onRefresh: () => Promise<void>;
  children: ReactNode;
}

const SUCCESS_DURATION = 1500;
const MAX_PULL = 120;

export function PullToRefresh({
  pullThreshold = 80,
  onRefresh,
  children,
}: PullToRefreshProps) {
  const [state, setState] = useState<RefreshState>("idle");
  // Use ref for pullDistance to avoid useCallback rebuilds on every pixel change;
  // derive the render value via a separate state that only updates when needed.
  const pullDistanceRef = useRef(0);
  const [pullDistance, setPullDistance] = useState(0);

  const startY = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const refreshing = useRef(false);

  // Reset to idle after success feedback
  useEffect(() => {
    if (state !== "success") return;
    const timer = setTimeout(() => {
      setState("idle");
      pullDistanceRef.current = 0;
      setPullDistance(0);
    }, SUCCESS_DURATION);
    return () => clearTimeout(timer);
  }, [state]);

  const getTouchY = useCallback((e: React.TouchEvent | TouchEvent): number => {
    return e.touches[0]?.clientY ?? (e as TouchEvent).changedTouches?.[0]?.clientY ?? 0;
  }, []);

  const isScrolledToTop = useCallback((): boolean => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollTop <= 0;
  }, []);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (refreshing.current) return;
      startY.current = getTouchY(e);
    },
    [getTouchY],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (refreshing.current) return;

      const currentY = getTouchY(e);
      const delta = currentY - startY.current;

      // Only respond to downward pull when at the top
      if (delta <= 0 || !isScrolledToTop()) {
        if (pullDistanceRef.current > 0) {
          pullDistanceRef.current = 0;
          setPullDistance(0);
        }
        return;
      }

      // Apply rubber-band resistance so it gets harder to pull further
      const resisted = Math.min(MAX_PULL, delta * 0.5);
      pullDistanceRef.current = resisted;
      setPullDistance(resisted);
      setState(resisted >= pullThreshold ? "pulling" : "idle");

      // Prevent native pull-to-refresh (overscroll bounce)
      e.preventDefault();
    },
    [getTouchY, isScrolledToTop, pullThreshold],
  );

  const handleTouchEnd = useCallback(async () => {
    if (refreshing.current) return;

    const currentDistance = pullDistanceRef.current;
    if (currentDistance >= pullThreshold) {
      refreshing.current = true;
      setState("refreshing");
      pullDistanceRef.current = pullThreshold;
      setPullDistance(pullThreshold);

      try {
        await onRefresh();
        setState("success");
      } catch {
        // On error, return to refreshable state
        setState("idle");
        pullDistanceRef.current = 0;
        setPullDistance(0);
      } finally {
        refreshing.current = false;
      }
    } else {
      // Below threshold, snap back
      pullDistanceRef.current = 0;
      setPullDistance(0);
      setState("idle");
    }
  }, [pullThreshold, onRefresh]);

  // Indicator content based on state
  const renderIndicator = () => {
    let text: string;
    let icon: ReactNode;

    switch (state) {
      case "pulling":
        text = "释放刷新";
        icon = (
          <ChevronDown
            className="h-5 w-5 transition-transform duration-200"
            style={{ transform: "rotate(180deg)" }}
          />
        );
        break;
      case "refreshing":
        text = "刷新中...";
        icon = (
          <div className="h-5 w-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
        );
        break;
      case "success":
        text = "刷新成功";
        icon = <Check className="h-5 w-5 text-green-500" />;
        break;
      default:
        if (pullDistance > 0) {
          text = "下拉刷新";
          icon = (
            <ChevronDown className="h-5 w-5 transition-transform duration-200" />
          );
        } else {
          return null;
        }
    }

    return (
      <div
        className="flex items-center justify-center gap-1.5 text-sm text-muted-foreground select-none"
        style={{ height: pullDistance > 0 || state !== "idle" ? pullThreshold : 0 }}
      >
        {icon}
        <span>{text}</span>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto overscroll-none"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      {/* Pull indicator area */}
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: state === "idle" && pullDistance === 0 ? "transform 0.3s ease" : "none",
        }}
      >
        {renderIndicator()}
      </div>

      {/* Content area — same translate so content moves with pull */}
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: state === "idle" && pullDistance === 0 ? "transform 0.3s ease" : "none",
        }}
      >
        {children}
      </div>
    </div>
  );
}
