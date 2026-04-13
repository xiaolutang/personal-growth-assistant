import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { FloatingChat } from "@/components/FloatingChat";
import { FeedbackButton } from "@/components/FeedbackButton";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Home } from "@/pages/Home";
import { Tasks } from "@/pages/Tasks";
import { Inbox } from "@/pages/Inbox";
import { Notes } from "@/pages/Notes";
import { Projects } from "@/pages/Projects";
import { EntryDetail } from "@/pages/EntryDetail";
import { Review } from "@/pages/Review";
import { Login } from "@/pages/Login";
import { Register } from "@/pages/Register";
import { useChatStore } from "@/stores/chatStore";
import { useTaskStore } from "@/stores/taskStore";
import { useUserStore } from "@/stores/userStore";
import { initFetchInterceptor } from "@/lib/uid";

// 在首次渲染前初始化 fetch 拦截器，确保所有请求都带 auth header
initFetchInterceptor();

function App() {
  const panelHeight = useChatStore((state) => state.panelHeight);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);
  const loadFromStorage = useUserStore((state) => state.loadFromStorage);

  // 初始化用户状态（从 localStorage 恢复登录态）
  useEffect(() => {
    loadFromStorage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 认证后才加载数据
  useEffect(() => {
    if (isAuthenticated) {
      fetchEntries({ limit: 100 });
    }
  }, [isAuthenticated, fetchEntries]);

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
              <div className="flex min-h-screen bg-background">
                <Sidebar />
                <div
                  className="flex flex-1 flex-col ml-64"
                  style={{ paddingBottom: panelHeight }}
                >
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/tasks" element={<Tasks />} />
                    <Route path="/inbox" element={<Inbox />} />
                    <Route path="/notes" element={<Notes />} />
                    <Route path="/projects" element={<Projects />} />
                    <Route path="/review" element={<Review />} />
                    <Route path="/entries/:id" element={<EntryDetail />} />
                  </Routes>
                </div>
                <FeedbackButton />
                <FloatingChat />
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
