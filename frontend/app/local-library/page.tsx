"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Database, RefreshCw } from "lucide-react"
import { api } from "@/lib/api-client"
import type { LocalLibraryConfig, LocalReferenceBook } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

// Import custom components
import { LibraryConfigPanel } from "@/components/local-library/LibraryConfigPanel"
import { LibraryScanPanel } from "@/components/local-library/LibraryScanPanel"
import { BookListTable } from "@/components/local-library/BookListTable"
import { BookDetailDrawer } from "@/components/local-library/BookDetailDrawer"
import { EssenceViewer } from "@/components/local-library/EssenceViewer"
import { ProjectBindingPanel } from "@/components/local-library/ProjectBindingPanel"
import { SimilarityGuardReport } from "@/components/local-library/SimilarityGuardReport"

export default function LocalLibraryDashboard() {
  const router = useRouter()
  const [config, setConfig] = useState<LocalLibraryConfig | null>(null)
  const [books, setBooks] = useState<LocalReferenceBook[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedBook, setSelectedBook] = useState<LocalReferenceBook | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isEssenceViewerOpen, setIsEssenceViewerOpen] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, bookList] = await Promise.all([
        api.localLibrary.getConfig().catch(() => null),
        api.localLibrary.listBooks().catch(() => []),
      ])
      setConfig(cfg)
      setBooks(bookList)

      // update selected book if it's currently open
      if (selectedBook) {
        const updatedBook = bookList.find(b => b.id === selectedBook.id)
        if (updatedBook) setSelectedBook(updatedBook)
      }
    } catch (e: any) {
      toast.error(e?.message || "加载数据失败")
    } finally {
      setLoading(false)
    }
  }, [selectedBook])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleViewBook = (book: LocalReferenceBook) => {
    setSelectedBook(book)
    setIsDrawerOpen(true)
  }

  const handleViewEssence = (bookId: string) => {
    const book = books.find(b => b.id === bookId)
    if (book) {
      setSelectedBook(book)
      setIsEssenceViewerOpen(true)
    }
  }

  const isConfigReady = Boolean(config?.source_dir && config?.allow_local_file_access)

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 md:p-8 min-h-[calc(100vh-2rem)]">
      <div className="shrink-0">
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => router.push("/")}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          返回项目列表
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card/40 border border-border/50 p-6 rounded-2xl backdrop-blur-xl shadow-lg">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent flex items-center gap-3">
            <Database className="w-7 h-7 sm:w-8 sm:h-8 text-primary" /> 本地文件夹吸收系统
          </h1>
          <p className="text-sm text-muted-foreground mt-2 font-medium">
            绑定本地原创/参考书库，自动提取摘要、写法圣经与场景模板。
          </p>
        </div>
        <Button variant="outline" size="sm" className="hidden md:flex opacity-50 cursor-not-allowed" title="未来阶段特性，目前默认使用 Local Direct Backend">
          <div className="w-2 h-2 rounded-full bg-muted-foreground mr-2" />
          Agent 离线 (直接挂载模式)
        </Button>
        <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
          <RefreshCw className={`size-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          刷新状态
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <LibraryConfigPanel config={config} onConfigUpdated={loadData} />
        </div>
        <div className="space-y-6">
          <LibraryScanPanel onScanComplete={loadData} disabled={!isConfigReady} />
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          已挂载书库 ({books.length})
        </h2>
        <BookListTable books={books} onViewBook={handleViewBook} />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
        <ProjectBindingPanel />
        <SimilarityGuardReport />
      </div>

      {/* Drawers and Dialogs */}
      <BookDetailDrawer 
        book={selectedBook} 
        open={isDrawerOpen} 
        onOpenChange={setIsDrawerOpen}
        onRefreshList={loadData}
        onViewEssence={(id) => {
          setIsDrawerOpen(false)
          handleViewEssence(id)
        }}
      />
      
      <EssenceViewer
        bookId={selectedBook?.id || ""}
        open={isEssenceViewerOpen}
        onOpenChange={setIsEssenceViewerOpen}
      />
    </main>
  )
}
