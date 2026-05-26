"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookOpen, Settings, Plus, Home, Menu, Sun, Moon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { useProjects } from "@/lib/hooks/use-projects"
import { BackendStatus } from "@/components/layout/backend-status"
import { getUser, clearToken } from "@/lib/auth"
import { useTheme } from "next-themes"
import { useRouter } from "next/navigation"
import { LogOut, User } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const { data: projects } = useProjects()
  const { theme, setTheme } = useTheme()
  const router = useRouter()
  const queryClient = useQueryClient()

  return (
    <>
      <div className="p-4 border-b">
        <Link href="/" className="flex items-center gap-2" onClick={onNavigate}>
          <BookOpen className="h-5 w-5 text-primary" />
          <span className="font-bold text-lg">AI 小说生成器</span>
        </Link>
      </div>

      <ScrollArea className="flex-1">
        <nav className="p-3 space-y-1">
          <Link href="/" onClick={onNavigate} className="block relative">
            {pathname === "/" && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-2/3 bg-primary rounded-r-md shadow-[0_0_10px_var(--primary)]" />
            )}
            <Button 
              variant={pathname === "/" ? "secondary" : "ghost"} 
              className={`w-full justify-start gap-2 transition-all duration-300 ${pathname === "/" ? "bg-primary/10 text-primary hover:bg-primary/20" : "hover:bg-primary/5"}`}
            >
              <Home className="h-4 w-4" />
              项目列表
            </Button>
          </Link>

          {projects === undefined ? (
            <div className="px-3 py-2 space-y-3">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4 bg-muted/40 rounded shrink-0 animate-pulse" />
                <Skeleton className="h-3 w-28 bg-muted/30 rounded animate-pulse" />
              </div>
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4 bg-muted/40 rounded shrink-0 animate-pulse" />
                <Skeleton className="h-3 w-20 bg-muted/30 rounded animate-pulse" />
              </div>
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4 bg-muted/40 rounded shrink-0 animate-pulse" />
                <Skeleton className="h-3 w-24 bg-muted/30 rounded animate-pulse" />
              </div>
            </div>
          ) : (
            projects.map((p: any) => {
              const isActive = pathname.startsWith(`/projects/${p.id}`)
              return (
                <Link key={p.id} href={`/projects/${p.id}`} onClick={onNavigate} className="block relative mt-1">
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-2/3 bg-primary rounded-r-md shadow-[0_0_10px_var(--primary)] animate-glow-pulse" />
                  )}
                  <Button
                    variant={isActive ? "secondary" : "ghost"}
                    className={`w-full justify-start gap-2 text-sm transition-all duration-300 ${isActive ? "bg-primary/10 text-primary hover:bg-primary/20 shadow-[inset_2px_0_0_0_transparent]" : "hover:bg-primary/5"}`}
                  >
                    <BookOpen className="h-4 w-4 shrink-0" />
                    <span className="truncate">{p.name}</span>
                  </Button>
                </Link>
              )
            })
          )}
        </nav>
      </ScrollArea>

      <div className="p-3 border-t space-y-2">
        <Link href="/projects/new" onClick={onNavigate}>
          <Button className="w-full gap-2" size="sm">
            <Plus className="h-4 w-4" />
            新建项目
          </Button>
        </Link>
        <Link href="/settings" onClick={onNavigate}>
          <Button variant="ghost" className="w-full justify-start gap-2" size="sm">
            <Settings className="h-4 w-4" />
            模型管理中心
          </Button>
        </Link>
        <div className="flex items-center gap-2 px-1 py-1.5 text-sm text-muted-foreground">
          <User className="h-3.5 w-3.5" />
          <span className="truncate">{getUser()?.username || "未登录"}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-muted-foreground"
          onClick={() => { clearToken(); queryClient.clear(); router.push("/login") }}
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </Button>
        {/* 主题切换 — 始终渲染占位空间，避免布局跳动 */}
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? (
            <><Sun className="h-4 w-4" />浅色模式</>
          ) : (
            <><Moon className="h-4 w-4" />深色模式</>
          )}
        </Button>
        <div className="flex justify-center mt-1">
          <BackendStatus />
        </div>
      </div>
    </>
  )
}

export function Sidebar() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile Header and Drawer */}
      <div className="lg:hidden">
        <header className="fixed top-0 left-0 right-0 h-14 bg-background/60 backdrop-blur-xl border-b border-border/30 z-40 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger render={
                <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded-lg">
                  <Menu className="h-5 w-5" />
                </Button>
              } />
              <SheetContent side="left" className="w-64 p-0 flex flex-col">
                <SidebarContent onNavigate={() => setOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="flex items-center gap-1.5 ml-1">
              <BookOpen className="h-4.5 w-4.5 text-primary" />
              <span className="font-bold text-sm bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">AI 小说生成器</span>
            </div>
          </div>
        </header>
      </div>

      {/* Desktop: fixed sidebar */}
      <aside className="hidden lg:flex w-64 h-full border-r border-sidebar-border bg-sidebar/60 backdrop-blur-3xl flex-col shrink-0 shadow-2xl relative z-10">
        <SidebarContent />
      </aside>
    </>
  )
}
