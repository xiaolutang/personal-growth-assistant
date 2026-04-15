import { NavLink } from "react-router-dom";
import { Home, CheckCircle, BarChart3, Compass, Brain } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: Home, label: "今天" },
  { to: "/explore", icon: Compass, label: "探索" },
  { to: "/graph", icon: Brain, label: "图谱" },
  { to: "/tasks", icon: CheckCircle, label: "任务" },
  { to: "/review", icon: BarChart3, label: "回顾" },
];

export function MobileNavBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 border-t border-gray-200 bg-white md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <div className="flex items-center justify-around h-14">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-0.5 px-3 py-1 text-[10px] font-medium transition-colors",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
