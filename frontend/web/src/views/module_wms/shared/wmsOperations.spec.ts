import { describe, expect, it } from "vitest";

import {
  buildDocumentMetrics,
  formatNullable,
  getQuantityProgress,
  getWmsStatusMeta,
  sumDecimalFields,
} from "./wmsOperations";

describe("WMS operations presentation helpers", () => {
  it("maps workflow statuses to business labels, tag type, and progress", () => {
    expect(getWmsStatusMeta("pending_reserve")).toMatchObject({
      label: "待锁库",
      type: "warning",
      progress: 20,
    });
    expect(getWmsStatusMeta("reviewed")).toMatchObject({
      label: "已复核",
      type: "primary",
      progress: 82,
    });
    expect(getWmsStatusMeta("confirmed")).toMatchObject({
      label: "已确认",
      type: "success",
      progress: 100,
    });
    expect(getWmsStatusMeta("unknown_status")).toMatchObject({
      label: "unknown_status",
      type: "info",
      progress: 0,
    });
  });

  it("calculates quantity progress without overflowing or dividing by zero", () => {
    expect(getQuantityProgress("8", "10")).toBe(80);
    expect(getQuantityProgress("12", "10")).toBe(100);
    expect(getQuantityProgress("3", "0")).toBe(0);
    expect(getQuantityProgress(undefined, "10")).toBe(0);
  });

  it("sums decimal-like fields from API rows", () => {
    const total = sumDecimalFields(
      [
        { available_qty: "10.5", locked_qty: "1" },
        { available_qty: "2.25", locked_qty: "0.75" },
      ],
      ["available_qty", "locked_qty"]
    );
    expect(total).toBe(14.5);
  });

  it("builds operational metrics from status distribution", () => {
    const metrics = buildDocumentMetrics(
      [
        { status: "pending_receive" },
        { status: "pending_receive" },
        { status: "pending_inspection" },
        { status: "confirmed" },
      ],
      [
        { label: "待收货", statuses: ["pending_receive"], icon: "ri:truck-line" },
        { label: "待检验", statuses: ["pending_inspection"], icon: "ri:microscope-line" },
        { label: "已确认", statuses: ["confirmed"], icon: "ri:checkbox-circle-line" },
      ]
    );

    expect(metrics).toEqual([
      { label: "待收货", value: 2, icon: "ri:truck-line", tone: "warning" },
      { label: "待检验", value: 1, icon: "ri:microscope-line", tone: "primary" },
      { label: "已确认", value: 1, icon: "ri:checkbox-circle-line", tone: "success" },
    ]);
  });

  it("formats empty values as a readable placeholder", () => {
    expect(formatNullable(undefined)).toBe("-");
    expect(formatNullable("")).toBe("-");
    expect(formatNullable(0)).toBe("0");
  });
});
