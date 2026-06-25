import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { LibraryConfigPanel } from "./LibraryConfigPanel"

// Mock api-client and sonner
vi.mock("@/lib/api-client", () => ({
  api: {
    localLibrary: {
      updateConfig: vi.fn().mockResolvedValue({}),
      testConfig: vi.fn().mockResolvedValue({ success: true })
    }
  }
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe("LibraryConfigPanel", () => {
  const mockConfig: any = {
    source_dir: "/path/to/source",
    essence_dir: "/path/to/essence",
    allow_local_file_access: true,
    watcher_enabled: false,
    use_hard_link: false,
    max_scan_depth: 3
  }

  it("renders correctly with config", () => {
    render(<LibraryConfigPanel config={mockConfig} onConfigUpdated={vi.fn()} />)
    expect(screen.getByDisplayValue("/path/to/source")).toBeInTheDocument()
    expect(screen.getByDisplayValue("/path/to/essence")).toBeInTheDocument()
    const switches = screen.getAllByRole("switch")
    expect(switches[0]).toBeChecked() // 允许本地读写
    expect(switches[1]).not.toBeChecked() // 自动监控
  })
})
