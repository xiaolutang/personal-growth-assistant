import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { Link } from "react-router-dom";

export function OfflineFallback() {
  const { isOnline } = useOnlineStatus();

  // 在线时不显示离线页
  if (isOnline) {
    return null;
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900/30">
            <svg
              className="h-8 w-8 text-orange-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M12 2v4m0 12v4m-6-6H2m20 0h-4"
              />
            </svg>
          </div>
        </div>
        <h2 className="mb-2 text-xl font-semibold text-foreground">
          你当前处于离线状态
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          无法连接到服务器，部分功能不可用。已缓存的数据仍可正常访问。
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 transition-colors"
          >
            返回首页
          </Link>
          <Link
            to="/tasks"
            className="inline-flex items-center justify-center rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            查看任务
          </Link>
        </div>
      </div>
    </div>
  );
}
