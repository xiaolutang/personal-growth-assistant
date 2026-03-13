import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { FloatingChat } from "@/components/FloatingChat";
import { Home } from "@/pages/Home";
import { Tasks } from "@/pages/Tasks";
import { Inbox } from "@/pages/Inbox";
import { Notes } from "@/pages/Notes";
import { Projects } from "@/pages/Projects";
import { useChatStore } from "@/stores/chatStore";

function App() {
  const panelHeight = useChatStore((state) => state.panelHeight);

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
          </Routes>
        </div>
        <FloatingChat />
      </div>
    </BrowserRouter>
  );
}

export default App;
