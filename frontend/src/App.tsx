import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { FloatingChat } from "@/components/FloatingChat";
import { Home } from "@/pages/Home";
import { Tasks } from "@/pages/Tasks";
import { Inbox } from "@/pages/Inbox";
import { Notes } from "@/pages/Notes";
import { Projects } from "@/pages/Projects";
import { EntryDetail } from "@/pages/EntryDetail";
import { Review } from "@/pages/Review";
import { useChatStore } from "@/stores/chatStore";
import { useTaskStore } from "@/stores/taskStore";

function App() {
  const panelHeight = useChatStore((state) => state.panelHeight);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);

  // 应用启动时从后端获取数据（只执行一次）
  useEffect(() => {
    fetchEntries({ limit: 100 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 空依赖数组，只在挂载时执行一次

  return (
    <BrowserRouter>
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
        <FloatingChat />
      </div>
    </BrowserRouter>
  );
}

export default App;
