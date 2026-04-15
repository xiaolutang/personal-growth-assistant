import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Home,
  CheckCircle,
  BarChart3,
  Compass,
  Brain,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  LogOut,
  User,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SessionList } from "@/components/SessionList";
import { useUserStore } from "@/stores/userStore";
import { ExportDialog } from "@/components/ExportDialog";

const navItems = [
  { to: "/", icon: Home, label: "今天" },
  { to: "/explore", icon: Compass, label: "探索" },
  { to: "/graph", icon: Brain, label: "图谱" },
  { to: "/tasks", icon: CheckCircle, label: "任务" },
  { to: "/review", icon: BarChart3, label: "回顾" },
];

export { navItems };

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const user = useUserStore((s) => s.user);
  const logout = useUserStore((s) => s.logout);

  // 点击导航项后关闭移动端抽屉
  const handleNavClick = () => {
    if (onClose) onClose();
  };

  return (
    <>
      {/* 移动端遮罩层 */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card transition-transform duration-300 ease-in-out",
          // 桌面端始终显示
          "md:translate-x-0",
          // 移动端根据 isOpen 控制
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center border-b px-6">
            <span className="text-lg font-semibold text-primary">
              Growth Assistant
            </span>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={handleNavClick}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )
                }
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* 对话历史 */}
          <div className="border-t">
            <button
              onClick={() => setIsChatExpanded(!isChatExpanded)}
              className="flex items-center justify-between w-full px-4 py-3 text-sm hover:bg-accent transition-colors"
            >
              <div className="flex items-center gap-3">
                <MessageSquare className="h-5 w-5" />
                <span className="font-medium">对话历史</span>
              </div>
              {isChatExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>

            {isChatExpanded && (
              <div className="border-t">
                <SessionList compact showTitle={false} maxHeight="320px" />
              </div>
            )}
          </div>

          {/* Footer with user info */}
          <div className="border-t p-4">
            {user && (
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-foreground">
                  <User className="h-4 w-4" />
                  <span className="truncate">{user.username}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setShowExport(true)}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                    title="导出数据"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      logout();
                      window.location.href = `${import.meta.env.BASE_URL}login`;
                    }}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                    title="登出"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              v0.1.0 - Personal Growth
            </p>
          </div>
        </div>
        <ExportDialog open={showExport} onClose={() => setShowExport(false)} />
      </aside>
    </>
  );
}
