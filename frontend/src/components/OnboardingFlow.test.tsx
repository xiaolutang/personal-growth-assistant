import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OnboardingFlow } from "./OnboardingFlow";

describe("OnboardingFlow", () => {
  const updateMeMock = vi.hoisted(() => vi.fn());

  vi.mock("@/stores/userStore", async () => {
    const actual = await vi.importActual<typeof import("@/stores/userStore")>("@/stores/userStore");
    return {
      ...actual,
      useUserStore: (selector: (s: { updateMe: typeof updateMeMock }) => unknown) =>
        selector({ updateMe: updateMeMock }),
    };
  });

  afterEach(() => {
    updateMeMock.mockReset();
    vi.useRealTimers();
  });

  it("正常流程：显示欢迎 → 点击下一步 → 点击完成 → 调用 updateMe", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    updateMeMock.mockResolvedValue({ onboarding_completed: true });

    render(<OnboardingFlow onComplete={onComplete} />);

    // 欢迎步骤可见
    expect(screen.getByText("欢迎来到个人成长助手")).toBeInTheDocument();

    // 点击「开始使用」进入引导步骤
    await user.click(screen.getByRole("button", { name: /开始使用/ }));
    expect(screen.getByText("记录你的第一条想法")).toBeInTheDocument();

    // 点击「我准备好了」完成 onboarding
    await user.click(screen.getByRole("button", { name: /我准备好了/ }));

    await waitFor(() => {
      expect(updateMeMock).toHaveBeenCalledWith({ onboarding_completed: true });
    });
    expect(onComplete).toHaveBeenCalled();
  });

  it("Skip 按钮：点击 Skip 也调用 updateMe({ onboarding_completed: true })", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    updateMeMock.mockResolvedValue({ onboarding_completed: true });

    render(<OnboardingFlow onComplete={onComplete} />);

    // 欢迎步骤点击「跳过引导」
    const skipButtons = screen.getAllByRole("button", { name: /跳过/ });
    await user.click(skipButtons[0]);

    await waitFor(() => {
      expect(updateMeMock).toHaveBeenCalledWith({ onboarding_completed: true });
    });
    expect(onComplete).toHaveBeenCalled();
  });

  it("PUT 失败时显示重试提示", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    updateMeMock.mockRejectedValue(new Error("更新失败"));

    render(<OnboardingFlow onComplete={onComplete} />);

    // 点击「开始使用」
    await user.click(screen.getByRole("button", { name: /开始使用/ }));

    // 点击「我准备好了」触发失败
    await user.click(screen.getByRole("button", { name: /我准备好了/ }));

    // 应该显示错误提示
    expect(await screen.findByText("引导状态保存失败")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /重试/ })).toBeInTheDocument();

    // onComplete 不应被调用
    expect(onComplete).not.toHaveBeenCalled();
  });
});
