import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { AbsorptionProgressPanel } from "./AbsorptionProgressPanel"

// Mock api-client and sonner
vi.mock("@/lib/api-client", () => ({
  api: {
    localLibrary: {
      getAbsorptionStatus: vi.fn().mockResolvedValue({
        status: "running",
        progress_current: 50,
        progress_total: 100,
        current_step: "Test Step"
      }),
      startAbsorption: vi.fn().mockResolvedValue({}),
      pauseAbsorption: vi.fn().mockResolvedValue({}),
      resumeAbsorption: vi.fn().mockResolvedValue({}),
      cancelAbsorption: vi.fn().mockResolvedValue({})
    }
  }
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe("AbsorptionProgressPanel", () => {
  it("renders correctly when not absorbing", () => {
    render(<AbsorptionProgressPanel bookId="test-id" bookStatus="parsed" onStatusChange={vi.fn()} />)
    expect(screen.getByText("尚未开始吸收转换流程")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /开始全书吸收/i })).toBeInTheDocument()
  })
})
