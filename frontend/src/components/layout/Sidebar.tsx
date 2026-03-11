import { NavLink } from "react-router-dom";
import {
  Home,
  CheckCircle,
  Lightbulb,
  FileText,
  Folder,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: Home, label: "首页" },
  { to: "/tasks", icon: CheckCircle, label: "任务" },
  { to: "/inbox", icon: Lightbulb, label: "灵感" },
  { to: "/notes", icon: FileText, label: "笔记" },
  { to: "/projects", icon: Folder, label: "项目" },
];

export function Sidebar() {
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
