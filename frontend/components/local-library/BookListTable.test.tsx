import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { BookListTable } from "./BookListTable"

describe("BookListTable", () => {
  const mockBooks = [
    {
      id: "1",
      title: "Test Book",
      source_file_name: "test.txt",
      source_file_ext: ".txt",
      source_file_hash: "123",
      source_file_mtime: "2026-01-01T00:00:00Z",
      source_file_path: "/test.txt",
      source_encoding: "utf-8",
      source_file_size: 1000,
      parse_status: "pending",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      chapter_count: 10,
      total_word_count: 50000,
      essence_dir_path: "",
      manifest_path: ""
    }
  ]

  it("renders empty state correctly", () => {
    render(<BookListTable books={[]} onViewBook={vi.fn()} />)
    expect(screen.getByText("暂无参考书籍")).toBeInTheDocument()
  })

  it("renders books correctly", () => {
    render(<BookListTable books={mockBooks as any} onViewBook={vi.fn()} />)
    expect(screen.getByText("Test Book")).toBeInTheDocument()
    expect(screen.getByText("等待解析")).toBeInTheDocument()
  })
})
