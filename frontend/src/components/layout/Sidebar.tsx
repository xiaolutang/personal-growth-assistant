import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  MessageSquare,
  ChevronDown,
  ChevronRight,
  LogOut,
  User,
  Download,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SessionList } from "@/components/SessionList";
import { useUserStore } from "@/stores/userStore";
import { ExportDialog } from "@/components/ExportDialog";
import { navItems } from "@/components/layout/navConfig";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({ isOpen = false, onClose, collapsed = false, onToggleCollapse }: SidebarProps) {
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
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-300 ease-in-out",
          collapsed ? "w-16" : "w-64",
          // 桌面端始终显示 (lg 断点及以上)
          "lg:translate-x-0",
          // 移动端和平板根据 isOpen 控制
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className={cn(
            "flex h-16 items-center border-b",
            collapsed ? "justify-center px-2" : "px-6"
          )}>
            <span className={cn(
              "text-lg font-semibold text-primary transition-all",
              collapsed && "text-sm"
            )}>
              {collapsed ? "GA" : "Growth Assistant"}
            </span>
            {/* 平板端折叠按钮 */}
            <button
              onClick={onToggleCollapse}
              className={cn(
                "ml-auto text-muted-foreground hover:text-foreground transition-colors",
                "hidden lg:flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent"
              )}
              title={collapsed ? "展开侧栏" : "收起侧栏"}
            >
              {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={handleNavClick}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    "flex items-center rounded-lg text-sm font-medium transition-colors",
                    collapsed ? "justify-center px-0 py-2" : "gap-3 px-3 py-2",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )
                }
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && item.label}
              </NavLink>
            ))}
          </nav>

          {/* 对话历史 */}
          {!collapsed && (
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
          )}

          {/* Footer with user info */}
          <div className={cn("border-t", collapsed ? "p-2" : "p-4")}>
            {user && (
              <div className={cn(
                "flex items-center justify-between",
                collapsed ? "flex-col gap-1" : "mb-2"
              )}>
                <div className={cn(
                  "flex items-center text-sm text-foreground",
                  collapsed ? "justify-center" : "gap-2"
                )}>
                  <User className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{user.username}</span>}
                </div>
                <div className={cn("flex items-center", collapsed ? "gap-0" : "gap-1")}>
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
            {!collapsed && (
              <p className="text-xs text-muted-foreground">
                v0.1.0 - Personal Growth
              </p>
            )}
          </div>
        </div>
        <ExportDialog open={showExport} onClose={() => setShowExport(false)} />
      </aside>
    </>
  );
}
