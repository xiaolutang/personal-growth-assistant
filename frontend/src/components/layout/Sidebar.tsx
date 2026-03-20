import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Home,
  CheckCircle,
  Lightbulb,
  FileText,
  Folder,
  BarChart3,
  MessageSquare,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SessionList } from "@/components/SessionList";

const navItems = [
  { to: "/", icon: Home, label: "首页" },
  { to: "/tasks", icon: CheckCircle, label: "任务" },
  { to: "/inbox", icon: Lightbulb, label: "灵感" },
  { to: "/notes", icon: FileText, label: "笔记" },
  { to: "/projects", icon: Folder, label: "项目" },
  { to: "/review", icon: BarChart3, label: "回顾" },
];

export function Sidebar() {
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card">
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

        {/* Footer */}
        <div className="border-t p-4">
          <p className="text-xs text-muted-foreground">
            v0.1.0 - Personal Growth
          </p>
        </div>
      </div>
    </aside>
  );
}
