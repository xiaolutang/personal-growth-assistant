import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Home } from "@/pages/Home";
import { Tasks } from "@/pages/Tasks";
import { Inbox } from "@/pages/Inbox";
import { Notes } from "@/pages/Notes";
import { Projects } from "@/pages/Projects";

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col ml-64">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/notes" element={<Notes />} />
            <Route path="/projects" element={<Projects />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
