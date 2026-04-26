import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReportHeader } from "../ReportHeader";

// Mock API export functions
const mockExportEntries = vi.fn();
const mockExportGrowthReport = vi.fn();

vi.mock("@/services/api", () => ({
  exportEntries: (...args: any[]) => mockExportEntries(...args),
  exportGrowthReport: (...args: any[]) => mockExportGrowthReport(...args),
}));

describe("ReportHeader", () => {
  let createdAnchor: HTMLAnchorElement | null = null;
  const origCreateElement = document.createElement.bind(document);

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    globalThis.URL.revokeObjectURL = vi.fn();
    createdAnchor = null;
    // 拦截 document.createElement("a") 以验证 href/download
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreateElement(tag);
      if (tag === "a") {
        createdAnchor = el as HTMLAnchorElement;
        el.click = vi.fn();
      }
      return el;
    });
  });

  it("渲染报告类型切换按钮", () => {
    const onReportTypeChange = vi.fn();
    render(<ReportHeader reportType="daily" onReportTypeChange={onReportTypeChange} />);

    expect(screen.getByText("日报")).toBeTruthy();
    expect(screen.getByText("周报")).toBeTruthy();
    expect(screen.getByText("月报")).toBeTruthy();
    expect(screen.getByText("趋势")).toBeTruthy();
  });

  it("渲染导出按钮", () => {
    render(<ReportHeader reportType="daily" onReportTypeChange={vi.fn()} />);
    expect(screen.getByText("全量导出")).toBeTruthy();
    expect(screen.getByText("成长报告")).toBeTruthy();
  });

  it("点击报告类型触发 onReportTypeChange", () => {
    const onReportTypeChange = vi.fn();
    render(<ReportHeader reportType="daily" onReportTypeChange={onReportTypeChange} />);
    fireEvent.click(screen.getByText("周报"));
    expect(onReportTypeChange).toHaveBeenCalledWith("weekly");
  });

  it("全量导出：调用 exportEntries + 设置正确 href/download + 下载 + 回收 URL", async () => {
    const blob = new Blob(["test data"]);
    mockExportEntries.mockResolvedValue(blob);
    render(<ReportHeader reportType="daily" onReportTypeChange={vi.fn()} />);

    const exportBtn = screen.getByText("全量导出").closest("button")!;
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(mockExportEntries).toHaveBeenCalledWith({ format: "markdown" });
      expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
      // 验证 anchor 元素属性
      expect(createdAnchor).not.toBeNull();
      expect(createdAnchor!.href).toBe("blob:mock-url");
      expect(createdAnchor!.download).toBe("entries_export.zip");
      expect(createdAnchor!.click).toHaveBeenCalled();
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
    });
  });

  it("成长报告导出：调用 exportGrowthReport + 设置正确文件名 + 下载", async () => {
    const blob = new Blob(["report data"]);
    mockExportGrowthReport.mockResolvedValue(blob);
    // Mock toISOString to return a fixed non-current date for deterministic filename
    const spy = vi.spyOn(Date.prototype, "toISOString").mockReturnValue("2025-12-25T08:00:00.000Z");
    render(<ReportHeader reportType="daily" onReportTypeChange={vi.fn()} />);

    const reportBtn = screen.getByText("成长报告").closest("button")!;
    fireEvent.click(reportBtn);

    await waitFor(() => {
      expect(mockExportGrowthReport).toHaveBeenCalled();
      expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
      expect(createdAnchor).not.toBeNull();
      expect(createdAnchor!.href).toBe("blob:mock-url");
      expect(createdAnchor!.download).toBe("growth_report_2025-12-25.md");
      expect(createdAnchor!.click).toHaveBeenCalled();
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
    });
    spy.mockRestore();
  });

  it("导出失败不触发下载且按钮恢复可用", async () => {
    mockExportEntries.mockRejectedValue(new Error("network error"));
    render(<ReportHeader reportType="daily" onReportTypeChange={vi.fn()} />);

    const exportBtn = screen.getByText("全量导出").closest("button")!;
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(exportBtn).not.toBeDisabled();
    });
    // 导出失败不应触发下载链路
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(createdAnchor).toBeNull();
  });
});
