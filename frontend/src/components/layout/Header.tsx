import { Menu, Sun, Moon, Download, X } from "lucide-react";
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
  const { canInstall, promptInstall, showBanner, dismissBanner } = usePWAInstall();

  function handleToggle() {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }

  return (
    <>
      {/* PWA 安装引导横条 */}
      {showBanner && (
        <div className="bg-primary text-primary-foreground flex items-center justify-center gap-3 px-4 py-2 text-sm relative">
          <span>将「成长助手」添加到桌面，随时记录灵感</span>
          <Button
            size="sm"
            variant="secondary"
            className="h-7 text-xs"
            onClick={promptInstall}
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            安装到桌面
          </Button>
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-primary-foreground/10 rounded"
            onClick={dismissBanner}
            aria-label="关闭安装提示"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
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
          {canInstall && !showBanner && (
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
    </>
  );
}
