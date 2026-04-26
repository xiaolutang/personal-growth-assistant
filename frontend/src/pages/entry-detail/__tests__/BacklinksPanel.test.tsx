import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock react-router-dom
const mockNavigate = vi.fn();
const mockParams = { id: "entry-1" };
vi.mock("react-router-dom", () => ({
  useParams: () => mockParams,
  useNavigate: () => mockNavigate,
}));

// Mock API
let getEntryMock = vi.fn();
let getEntriesMock = vi.fn();
let getProjectProgressMock = vi.fn();
let getBacklinksMock = vi.fn();
let getRelatedEntriesMock = vi.fn();
let getEntryLinksMock = vi.fn();
let generateEntrySummaryMock = vi.fn();
let getKnowledgeContextMock = vi.fn();

vi.mock("@/services/api", () => ({
  getEntry: (...args: any[]) => getEntryMock(...args),
  getEntries: (...args: any[]) => getEntriesMock(...args),
  getProjectProgress: (...args: any[]) => getProjectProgressMock(...args),
  getBacklinks: (...args: any[]) => getBacklinksMock(...args),
  getRelatedEntries: (...args: any[]) => getRelatedEntriesMock(...args),
  getEntryLinks: (...args: any[]) => getEntryLinksMock(...args),
  generateEntrySummary: (...args: any[]) => generateEntrySummaryMock(...args),
  getKnowledgeContext: (...args: any[]) => getKnowledgeContextMock(...args),
  exportSingleEntry: vi.fn().mockResolvedValue(new Blob()),
}));

vi.mock("@/components/PageChatPanel", () => ({
  PageChatPanel: () => <div data-testid="page-chat-panel" />,
}));

vi.mock("@/components/ServiceUnavailable", () => ({
  ServiceUnavailable: () => <div>Service Unavailable</div>,
}));

import { EntryDetail } from "../../EntryDetail";

const makeTask = (overrides = {}) => ({
  id: "entry-1",
  title: "Test Entry",
  content: "Test content",
  category: "note",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  parent_id: undefined,
  ...overrides,
});

describe("EntryDetail - 反向引用面板", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getEntryMock.mockResolvedValue(makeTask());
    getEntriesMock.mockResolvedValue({ entries: [] });
    getProjectProgressMock.mockResolvedValue(null);
    getBacklinksMock.mockResolvedValue({ backlinks: [] });
    getRelatedEntriesMock.mockResolvedValue([]);
    getEntryLinksMock.mockResolvedValue({ links: [] });
    generateEntrySummaryMock.mockRejectedValue(new Error("not available"));
    getKnowledgeContextMock.mockRejectedValue(new Error("not available"));
  });

  it("有反向引用时展示列表", async () => {
    getBacklinksMock.mockResolvedValue({
      backlinks: [
        { id: "bl-1", title: "引用笔记A", category: "note" },
        { id: "bl-2", title: "引用笔记B", category: "note" },
      ],
    });

    render(<EntryDetail />);

    await waitFor(() => {
      expect(screen.getByText("反向引用 (2)")).toBeTruthy();
    });

    expect(screen.getByText("引用笔记A")).toBeTruthy();
    expect(screen.getByText("引用笔记B")).toBeTruthy();
  });

  it("无反向引用时隐藏面板", async () => {
    getBacklinksMock.mockResolvedValue({ backlinks: [] });

    render(<EntryDetail />);

    await waitFor(() => {
      expect(getBacklinksMock).toHaveBeenCalledWith("entry-1");
    });

    expect(screen.queryByText(/反向引用/)).toBeNull();
  });

  it("反向引用可点击跳转", async () => {
    getBacklinksMock.mockResolvedValue({
      backlinks: [
        { id: "bl-1", title: "引用笔记A", category: "note" },
      ],
    });

    render(<EntryDetail />);

    await waitFor(() => {
      expect(screen.getByText("引用笔记A")).toBeTruthy();
    });

    const item = screen.getByText("引用笔记A").closest("[class*='cursor-pointer']");
    expect(item).toBeTruthy();
    fireEvent.click(item!);
    expect(mockNavigate).toHaveBeenCalledWith("/entry/bl-1");
  });

  it("API 失败时静默降级（不展示错误）", async () => {
    getBacklinksMock.mockRejectedValue(new Error("Network error"));

    render(<EntryDetail />);

    await waitFor(() => {
      expect(getBacklinksMock).toHaveBeenCalledWith("entry-1");
    });

    // 不应有反向引用面板
    expect(screen.queryByText(/反向引用/)).toBeNull();
    // 页面正常渲染
    expect(screen.getByText("Test Entry")).toBeTruthy();
  });
});
