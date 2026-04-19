import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ExportDialog } from "./ExportDialog";

const mockExportEntries = vi.fn();

vi.mock("@/services/api", () => ({
  exportEntries: (...args: unknown[]) => mockExportEntries(...args),
}));

// Mock URL.createObjectURL / revokeObjectURL
const mockCreateObjectURL = vi.fn(() => "blob:test-url");
const mockRevokeObjectURL = vi.fn();

// Mock HTMLDialogElement (jsdom doesn't support showModal)
beforeEach(() => {
  globalThis.URL.createObjectURL = mockCreateObjectURL;
  globalThis.URL.revokeObjectURL = mockRevokeObjectURL;
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
  });
});
afterEach(() => {
  vi.restoreAllMocks();
});

function renderDialog(open = true) {
  const onClose = vi.fn();
  const result = render(<ExportDialog open={open} onClose={onClose} />);
  return { onClose, ...result };
}

describe("ExportDialog", () => {
  beforeEach(() => {
    mockExportEntries.mockReset();
    mockCreateObjectURL.mockReturnValue("blob:test-url");
    mockRevokeObjectURL.mockReset();
  });

  it("open=true 时渲染对话框并显示标题", () => {
    renderDialog(true);
    expect(screen.getByText("导出数据")).toBeInTheDocument();
  });

  it("默认选中 Markdown 格式，点击可切换为 JSON", async () => {
    const user = userEvent.setup();
    renderDialog(true);

    const jsonBtn = screen.getByText("JSON");
    await user.click(jsonBtn);

    // 切换后 JSON 按钮应该获得 active 样式（bg-primary）
    expect(jsonBtn.className).toContain("bg-primary");
  });

  it("类型筛选下拉可选项", async () => {
    const user = userEvent.setup();
    renderDialog(true);

    const select = screen.getByDisplayValue("全部类型");
    await user.selectOptions(select, "task");

    expect((select as HTMLSelectElement).value).toBe("task");
  });

  it("设置日期范围后传递给 exportEntries", async () => {
    const user = userEvent.setup();
    mockExportEntries.mockResolvedValueOnce(new ArrayBuffer(8));
    const { container } = renderDialog(true);

    // 通过 type 查找日期输入
    const dateInputs = container.querySelectorAll<HTMLInputElement>("input[type='date']");
    expect(dateInputs.length).toBe(2);

    await user.type(dateInputs[0], "2026-01-01");
    await user.type(dateInputs[1], "2026-04-19");

    // 点击导出
    const exportBtn = screen.getByText("导出");
    await user.click(exportBtn);

    await waitFor(() => {
      expect(mockExportEntries).toHaveBeenCalledWith(
        expect.objectContaining({
          startDate: "2026-01-01",
          endDate: "2026-04-19",
        }),
      );
    });
  });

  it("导出成功后调用 onClose", async () => {
    const user = userEvent.setup();
    mockExportEntries.mockResolvedValueOnce(new ArrayBuffer(8));
    const { onClose } = renderDialog(true);

    const exportBtn = screen.getByText("导出");
    await user.click(exportBtn);

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
    expect(mockCreateObjectURL).toHaveBeenCalled();
  });

  it("导出失败显示错误提示", async () => {
    const user = userEvent.setup();
    mockExportEntries.mockRejectedValueOnce(new Error("网络错误"));
    renderDialog(true);

    const exportBtn = screen.getByText("导出");
    await user.click(exportBtn);

    expect(await screen.findByText("网络错误")).toBeInTheDocument();
  });

  it("点击取消按钮调用 onClose", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDialog(true);

    const cancelBtn = screen.getByText("取消");
    await user.click(cancelBtn);

    expect(onClose).toHaveBeenCalled();
  });
});
