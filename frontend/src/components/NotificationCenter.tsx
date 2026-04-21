import { useState, useEffect, useRef } from "react";
import { Bell, Check, AlertTriangle, Lightbulb, BookOpen, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getNotifications,
  dismissNotification,
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationItem,
  type NotificationPreferences,
} from "@/services/api";
import { useNavigate } from "react-router-dom";

const typeIcons: Record<string, typeof AlertTriangle> = {
  overdue_task: AlertTriangle,
  stale_inbox: Lightbulb,
  review_prompt: BookOpen,
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.max(0, now - then);
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return new Date(dateStr).toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

export function NotificationCenter() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [prefs, setPrefs] = useState<NotificationPreferences>({
    overdue_task_enabled: true,
    stale_inbox_enabled: true,
    review_prompt_enabled: true,
  });
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadNotifications();
    // 每 60 秒轮询刷新通知
    const interval = setInterval(loadNotifications, 60_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowPrefs(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  async function loadNotifications() {
    try {
      const res = await getNotifications();
      setItems(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // 静默失败，不影响 Header
    }
  }

  async function handleDismiss(id: string) {
    // 乐观更新，失败时回滚
    const prevItems = items;
    const prevCount = unreadCount;
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, dismissed: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
    try {
      await dismissNotification(id);
    } catch {
      setItems(prevItems);
      setUnreadCount(prevCount);
    }
  }

  async function handleDismissAll() {
    const undimissed = items.filter((n) => !n.dismissed);
    if (undimissed.length === 0) return;
    const prevItems = items;
    const prevCount = unreadCount;
    setItems((prev) => prev.map((n) => ({ ...n, dismissed: true })));
    setUnreadCount(0);
    try {
      await Promise.all(undimissed.map((n) => dismissNotification(n.id)));
    } catch {
      setItems(prevItems);
      setUnreadCount(prevCount);
    }
  }

  function handleClickNotification(n: NotificationItem) {
    if (!n.dismissed) handleDismiss(n.id);
    setOpen(false);
    if (n.ref_id) {
      navigate(`/entries/${n.ref_id}`);
    } else if (n.type === "review_prompt") {
      navigate("/review");
    }
  }

  async function togglePref(key: keyof NotificationPreferences) {
    setPrefs(prev => {
      const next = { ...prev, [key]: !prev[key] };
      updateNotificationPreferences(next).catch(() => {
        setPrefs(prev2 => ({ ...prev2, [key]: !prev2[key] }));
      });
      return next;
    });
  }

  useEffect(() => {
    if (open && showPrefs) {
      getNotificationPreferences().then(setPrefs).catch(() => {});
    }
  }, [open, showPrefs]);

  return (
    <div className="relative" ref={panelRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => { setOpen(!open); setShowPrefs(false); }}
        aria-label="通知"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground px-1">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-lg border bg-popover shadow-lg z-50 overflow-hidden">
          {showPrefs ? (
            <div className="p-3">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">提醒偏好</h3>
                <Button variant="ghost" size="sm" onClick={() => setShowPrefs(false)}>
                  返回
                </Button>
              </div>
              <label className="flex items-center justify-between py-2 text-sm">
                <span>拖延任务提醒</span>
                <input
                  type="checkbox"
                  checked={prefs.overdue_task_enabled}
                  onChange={() => togglePref("overdue_task_enabled")}
                  className="accent-primary h-4 w-4"
                />
              </label>
              <label className="flex items-center justify-between py-2 text-sm">
                <span>灵感未转化提醒</span>
                <input
                  type="checkbox"
                  checked={prefs.stale_inbox_enabled}
                  onChange={() => togglePref("stale_inbox_enabled")}
                  className="accent-primary h-4 w-4"
                />
              </label>
              <label className="flex items-center justify-between py-2 text-sm">
                <span>回顾提醒</span>
                <input
                  type="checkbox"
                  checked={prefs.review_prompt_enabled}
                  onChange={() => togglePref("review_prompt_enabled")}
                  className="accent-primary h-4 w-4"
                />
              </label>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between px-3 py-2 border-b">
                <h3 className="text-sm font-semibold">通知</h3>
                <div className="flex gap-1">
                  {unreadCount > 0 && (
                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleDismissAll}>
                      全部已读
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" className="h-7" onClick={() => setShowPrefs(true)}>
                    <Settings className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {items.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    暂无通知
                  </div>
                ) : (
                  items.map((n) => {
                    const Icon = typeIcons[n.type] || Bell;
                    return (
                      <div
                        key={n.id}
                        className={`flex items-start gap-2 px-3 py-2 border-b last:border-b-0 cursor-pointer hover:bg-accent transition-colors ${n.dismissed ? "opacity-50" : ""}`}
                        onClick={() => handleClickNotification(n)}
                      >
                        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${n.dismissed ? "text-muted-foreground" : "text-primary"}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium leading-tight">{n.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.message}</p>
                          {n.created_at && (
                            <p className="text-[10px] text-muted-foreground/60 mt-0.5">{formatRelativeTime(n.created_at)}</p>
                          )}
                        </div>
                        {!n.dismissed && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 shrink-0"
                            onClick={(e) => { e.stopPropagation(); handleDismiss(n.id); }}
                          >
                            <Check className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
