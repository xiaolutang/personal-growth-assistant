/**
 * F08: ViewSelector component tests
 * - Renders list and grouped options
 * - Highlights the active view
 * - Calls onViewChange when clicked
 * - Extensible: supports custom option definitions
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViewSelector } from "../ViewSelector";
import type { ViewOption } from "../constants";

const defaultOptions: ViewOption[] = [
  { key: "list", label: "列表" },
  { key: "grouped", label: "按项目" },
];

describe("F08: ViewSelector", () => {
  it("renders all options", () => {
    render(<ViewSelector options={defaultOptions} activeView="list" onViewChange={vi.fn()} />);
    expect(screen.getByText("列表")).toBeInTheDocument();
    expect(screen.getByText("按项目")).toBeInTheDocument();
  });

  it("highlights the active view", () => {
    render(<ViewSelector options={defaultOptions} activeView="grouped" onViewChange={vi.fn()} />);
    const groupedBtn = screen.getByText("按项目");
    expect(groupedBtn.closest("button")).toHaveAttribute("data-active", "true");
    const listBtn = screen.getByText("列表");
    expect(listBtn.closest("button")).toHaveAttribute("data-active", "false");
  });

  it("calls onViewChange when an option is clicked", () => {
    const handleChange = vi.fn();
    render(<ViewSelector options={defaultOptions} activeView="list" onViewChange={handleChange} />);
    fireEvent.click(screen.getByText("按项目"));
    expect(handleChange).toHaveBeenCalledWith("grouped");
  });

  it("supports extensible options for F09 timeline", () => {
    const extendedOptions: ViewOption[] = [
      ...defaultOptions,
      { key: "timeline", label: "时间线" },
    ];
    render(<ViewSelector options={extendedOptions} activeView="list" onViewChange={vi.fn()} />);
    expect(screen.getByText("时间线")).toBeInTheDocument();
  });
});
