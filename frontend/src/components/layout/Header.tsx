import { Menu, Sun, Moon, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSidebar } from "@/components/layout/SidebarContext";
import { useTheme } from "@/lib/theme";
import { usePWAInstall } from "@/lib/usePWAInstall";
import { NotificationCenter } from "@/components/NotificationCenter";

interface HeaderProps {
  title: string;
  onToggleSidebar?: () => void;
}

export function Header({ title, onToggleSidebar }: HeaderProps) {
  const { toggle } = useSidebar();
  const { resolvedTheme, setTheme } = useTheme();
  const { canInstall, promptInstall } = usePWAInstall();

  function handleToggle() {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 px-4 md:px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onToggleSidebar ?? toggle}
          aria-label="打开侧边栏"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>
      <div className="flex items-center gap-1">
        {canInstall && (
          <Button variant="ghost" size="icon" onClick={promptInstall} aria-label="安装应用">
            <Download className="h-5 w-5" />
          </Button>
        )}
        <NotificationCenter />
        <Button variant="ghost" size="icon" onClick={handleToggle} aria-label="切换主题">
          {resolvedTheme === "dark" ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </Button>
      </div>
    </header>
  );
}
