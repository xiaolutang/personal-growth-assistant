import { useEffect, useState, useCallback, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { Sidebar } from "@/components/layout/Sidebar";
import { SidebarProvider, useSidebar } from "@/components/layout/SidebarContext";
import { MobileNavBar } from "@/components/layout/MobileNavBar";
import { FloatingChat } from "@/components/FloatingChat";
import { FeedbackButton } from "@/components/FeedbackButton";
import { PageAIAssistant } from "@/components/PageAIAssistant";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { OfflineIndicator } from "@/components/OfflineIndicator";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ThemeProvider } from "@/lib/theme";
import { useChatStore } from "@/stores/chatStore";
import { useTaskStore } from "@/stores/taskStore";
import { useUserStore } from "@/stores/userStore";
import { initFetchInterceptor } from "@/lib/uid";
import { initSync } from "@/lib/offlineSync";

// 路由懒加载
const Home = lazy(() => import("@/pages/Home").then(m => ({ default: m.Home })));
const Tasks = lazy(() => import("@/pages/Tasks").then(m => ({ default: m.Tasks })));
const EntryDetail = lazy(() => import("@/pages/EntryDetail").then(m => ({ default: m.EntryDetail })));
const Review = lazy(() => import("@/pages/Review").then(m => ({ default: m.Review })));
const Explore = lazy(() => import("@/pages/Explore").then(m => ({ default: m.Explore })));
const GraphPage = lazy(() => import("@/pages/GraphPage").then(m => ({ default: m.GraphPage })));
const GoalsPage = lazy(() => import("@/pages/GoalsPage").then(m => ({ default: m.GoalsPage })));
const GoalDetail = lazy(() => import("@/pages/GoalDetail").then(m => ({ default: m.GoalDetail })));
const Login = lazy(() => import("@/pages/Login").then(m => ({ default: m.Login })));
const Register = lazy(() => import("@/pages/Register").then(m => ({ default: m.Register })));
const OfflineFallback = lazy(() => import("@/pages/OfflineFallback").then(m => ({ default: m.OfflineFallback })));

// Suspense fallback
function PageSpinner() {
  return <div className="flex items-center justify-center h-64 text-muted-foreground">加载中...</div>;
}

// 在首次渲染前初始化 fetch 拦截器，确保所有请求都带 auth header
initFetchInterceptor();

// 平板断点：768-1024px 时默认收起 sidebar
const TABLET_BREAKPOINT = 1024;

function AppLayout() {
  const panelHeight = useChatStore((state) => state.panelHeight);
  const { isOpen, close } = useSidebar();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < TABLET_BREAKPOINT : false
  );

  // 监听窗口大小变化，自动切换平板折叠状态
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${TABLET_BREAKPOINT - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setSidebarCollapsed(e.matches);
    mql.addEventListener("change", handler);
    setSidebarCollapsed(mql.matches);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const toggleCollapse = useCallback(() => setSidebarCollapsed((v) => !v), []);

  // 全局 Cmd+K / Ctrl+K：跳转探索页并聚焦搜索框
  useEffect(() => {
    const handleGlobalSearch = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.key !== "k") return;
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
      e.preventDefault();
      // 已在 explore 页时仅聚焦，不重复导航（保留现有 query params）
      if (!location.pathname.startsWith("/explore")) {
        navigate("/explore");
      }
      requestAnimationFrame(() => {
        window.dispatchEvent(new CustomEvent("focus-explore-search"));
      });
    };
    document.addEventListener("keydown", handleGlobalSearch);
    return () => document.removeEventListener("keydown", handleGlobalSearch);
  }, [navigate, location.pathname]);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={isOpen} onClose={close} collapsed={sidebarCollapsed} onToggleCollapse={toggleCollapse} />
      <div
        className={`flex flex-1 flex-col transition-all duration-300 pb-16 lg:pb-0`}
        style={{
          marginLeft: sidebarCollapsed ? "4rem" : "16rem",
          paddingBottom: panelHeight,
        }}
      >
        {/* 大屏内容区最大宽度限制 */}
        <div className="mx-auto w-full max-w-[1280px]">
          <Suspense fallback={<PageSpinner />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/goals/:id" element={<GoalDetail />} />
            <Route path="/inbox" element={<Navigate to="/explore?type=inbox" replace />} />
            <Route path="/notes" element={<Navigate to="/explore?type=note" replace />} />
            <Route path="/projects" element={<Navigate to="/explore?type=project" replace />} />
            <Route path="/review" element={<Review />} />
            <Route path="/entries/:id" element={<EntryDetail />} />
            <Route path="/offline" element={<OfflineFallback />} />
          </Routes>
          </Suspense>
        </div>
      </div>
      <FeedbackButton />
      <FloatingChat />
      <PageAIAssistant pageContext={{ page: "global" }} />
      <MobileNavBar />
    </div>
  );
}

function App() {
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);
  const loadFromStorage = useUserStore((state) => state.loadFromStorage);
  const user = useUserStore((state) => state.user);
  const fetchMe = useUserStore((state) => state.fetchMe);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // 用户加载完成后决定是否显示 onboarding
  useEffect(() => {
    if (isAuthenticated && user) {
      setShowOnboarding(!user.onboarding_completed);
    } else {
      setShowOnboarding(false);
    }
  }, [isAuthenticated, user]);

  function handleOnboardingComplete() {
    setShowOnboarding(false);
    fetchMe();
  }

  // 初始化用户状态（从 localStorage 恢复登录态）
  useEffect(() => {
    loadFromStorage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 认证校验完成且有效后才加载数据和同步
  const isLoading = useUserStore((state) => state.isLoading);
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      fetchEntries({ limit: 100 });
      initSync();
    }
  }, [isAuthenticated, isLoading, fetchEntries]);

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* 受保护路由 */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <ThemeProvider>
              <SidebarProvider>
                {showOnboarding && (
                  <OnboardingFlow onComplete={handleOnboardingComplete} />
                )}
                <Toaster position="top-center" richColors />
                <OfflineIndicator />
                <AppLayout />
              </SidebarProvider>
              </ThemeProvider>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
