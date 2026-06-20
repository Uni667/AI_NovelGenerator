"use client"
 
import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  BookOpen, Settings, Plus, Home, Menu, Sun, Moon, BarChart3, 
  Users, Globe, Compass, FileEdit, Database, LayoutGrid, Search, 
  ChevronsRight, Award, LogOut, User
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { useProjects } from "@/lib/hooks/use-projects"
import { BackendStatus } from "@/components/layout/backend-status"
import { getUser, clearToken } from "@/lib/auth"
import { useTheme } from "next-themes"
import { useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { projectService } from "@/lib/services/projectService"
 
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const { data: projects } = useProjects()
  const { theme, setTheme } = useTheme()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState("")
  const [user, setUserState] = useState<{ username: string; tier: string } | null>(null)
  
  // Extract active project ID safely from URL
  const projectIdMatch = pathname.match(/\/projects\/([^\/]+)/)
  const activeProjectId = projectIdMatch && projectIdMatch[1] !== "new" ? projectIdMatch[1] : null
 
  // Fetch active tab safely from window search params without build-time deoptimization
  const [activeTab, setActiveTab] = useState("overview")
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      setActiveTab(params.get("tab") || "overview")
    }
  }, [pathname])

  // Sync searchQuery from URL query parameters
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      setSearchQuery(params.get("search") || "")
    }
  }, [pathname])

  // Fetch current user details reactively to prevent SSR hydration mismatch
  useEffect(() => {
    const updateUser = () => {
      const u = getUser()
      if (u) {
        setUserState({ username: u.username, tier: "Pro 订阅" })
      } else {
        setUserState({ username: "演示用户", tier: "体验版" })
      }
    }
    updateUser()
    window.addEventListener("auth-changed", updateUser)
    return () => window.removeEventListener("auth-changed", updateUser)
  }, [pathname])

  const handleSearchChange = (val: string) => {
    setSearchQuery(val)
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      if (val) {
        params.set("search", val)
      } else {
        params.delete("search")
      }
      if (pathname === "/") {
        router.replace(`/?${params.toString()}`)
      }
    }
  }
 
  const filteredProjects = projects?.filter((p: any) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  )
 
  const projectNavItems = [
    { label: "章节管理", tab: "workbench", icon: BookOpen },
    { label: "人物设定", tab: "characters", icon: Users },
    { label: "世界设定", tab: "pipeline", icon: Globe },
    { label: "大纲设计", tab: "plotarcs", icon: Compass },
    { label: "写作记录", tab: "generation", icon: FileEdit },
    { label: "知识库", tab: "knowledge", icon: Database },
    { label: "设置中心", tab: "settings", icon: Settings },
  ]
 
  return (
    <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground">
      {/* Header Logo */}
      <div className="p-4 border-b border-sidebar-border flex items-center justify-between shrink-0">
        <Link href="/" className="flex items-center gap-2" onClick={onNavigate}>
          <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-[0_0_15px_rgba(99,102,241,0.3)]">
            <BookOpen className="h-4 w-4" />
          </div>
          <span className="font-bold text-sm text-sidebar-foreground dark:text-white tracking-wide">AI 小说生成器</span>
        </Link>
        <button className="h-5 w-5 flex items-center justify-center rounded hover:bg-sidebar-accent hover:text-sidebar-accent-foreground text-muted-foreground">
          <LayoutGrid className="h-3.5 w-3.5" />
        </button>
      </div>
 
      {/* Scrollable Navigation */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-4">
          {/* Action Button */}
          <Link href="/projects/new" onClick={onNavigate} className="block">
            <Button className="w-full gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs h-9 shadow-[0_0_12px_rgba(99,102,241,0.3)] transition-all duration-300" size="sm">
              <Plus className="h-4 w-4" />
              新建项目
            </Button>
          </Link>
 
          {/* Project Directory Selector */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
              <span>项目列表</span>
              <Search className="h-3 w-3 opacity-60" />
            </div>
            
            <div className="relative mt-1 mb-2">
              <input
                type="text"
                placeholder="搜索项目..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full bg-sidebar-accent/50 dark:bg-black/40 border border-sidebar-border rounded-lg px-2.5 py-1 text-xs outline-none text-sidebar-foreground placeholder:text-sidebar-foreground/40 transition-colors focus:border-indigo-500/50"
              />
            </div>
 
            <div className="space-y-0.5 max-h-[140px] overflow-y-auto pr-1">
              {projects === undefined ? (
                <div className="space-y-2 px-1">
                  <Skeleton className="h-7 w-full bg-sidebar-accent rounded" />
                  <Skeleton className="h-7 w-full bg-sidebar-accent rounded" />
                </div>
              ) : filteredProjects && filteredProjects.length > 0 ? (
                filteredProjects.map((p: any) => {
                  const isActive = activeProjectId === p.id
                  return (
                    <Link
                      key={p.id}
                      href={`/projects/${p.id}?tab=${activeTab}`}
                      onClick={onNavigate}
                      className={`flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition-all duration-200 relative overflow-hidden ${
                        isActive
                          ? "bg-indigo-500/10 text-indigo-600 dark:text-white font-semibold border-l-2 border-indigo-500"
                          : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                      }`}
                    >
                      <span className="truncate">{p.name}</span>
                      {isActive && <ChevronsRight className="h-3 w-3 text-indigo-600 dark:text-indigo-400 shrink-0 ml-1.5" />}
                    </Link>
                  )
                })
              ) : (
                <div className="text-[10px] text-muted-foreground/60 italic text-center py-2">无匹配项目</div>
              )}
            </div>
          </div>
 
          {/* Project Shortcuts Menu (rendered when inside a project page) */}
          {activeProjectId && (
            <div className="space-y-1 pt-1 border-t border-sidebar-border">
              <div className="px-1 text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-2">
                项目导航
              </div>
              <div className="space-y-1">
                {projectNavItems.map((item) => {
                  const isActive = activeTab === item.tab
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.tab}
                      href={`/projects/${activeProjectId}?tab=${item.tab}`}
                      onClick={onNavigate}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                        isActive
                          ? "bg-indigo-500/10 text-indigo-600 dark:text-white border-l-2 border-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.05)]"
                          : "text-sidebar-foreground/75 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                      }`}
                    >
                      <Icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? 'text-indigo-600' : 'text-sidebar-foreground/50'}`} />
                      <span>{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
 
      {/* Bottom Cards & Profile */}
      <div className="p-3 border-t border-sidebar-border space-y-3 shrink-0">
        {/* Space Usage Card */}
        {(() => {
          const storage = projectService.estimateStorageUsage(projects || [])
          return (
            <div className="p-3 rounded-xl border border-sidebar-border bg-sidebar-accent/40 backdrop-blur-md">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1 font-medium">
                <span>空间使用</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">{storage.percentage}%</span>
              </div>
              <div className="font-bold text-xs text-sidebar-foreground dark:text-white mb-2">{storage.formatted}</div>
              <div className="w-full h-1 bg-sidebar-border rounded-full overflow-hidden mb-2.5">
                <div 
                  className="bg-indigo-600 h-full rounded-full shadow-[0_0_8px_rgba(99,102,241,0.5)] transition-all duration-500" 
                  style={{ width: `${storage.percentage}%` }}
                />
              </div>
              <button 
                className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 hover:opacity-80 transition-opacity block w-full text-center"
                onClick={() => toast.info("升级服务通道即将推出")}
              >
                升级空间
              </button>
            </div>
          )
        })()}
 
        {/* Profile Card */}
        <div className="p-2.5 rounded-xl border border-sidebar-border bg-sidebar-accent/20 flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-2 min-w-0">
            <div className="h-7 w-7 rounded-full bg-indigo-500/20 flex items-center justify-center text-xs font-bold text-indigo-600 dark:text-indigo-400 shrink-0 border border-indigo-500/30">
              <User className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex flex-col">
              <span className="text-xs font-semibold text-sidebar-foreground dark:text-white truncate">{user?.username || "用户昵称"}</span>
              <span className="text-[9px] text-sidebar-foreground/50 font-mono">{user?.tier || "Pro 订阅"}</span>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 text-[9px] font-bold px-1.5 py-0.5 border border-indigo-500/20">
            {user?.username === "演示用户" ? "Free" : "Pro"}
          </span>
        </div>
 
        {/* System Settings & Actions */}
        <div className="pt-2 space-y-1">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-xs text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent h-8 px-2.5"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? (
              <><Sun className="h-3.5 w-3.5 text-amber-400" />浅色模式</>
            ) : (
              <><Moon className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />深色模式</>
            )}
          </Button>
 
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-xs text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent h-8 px-2.5"
            onClick={() => { clearToken(); queryClient.clear(); router.push("/login") }}
          >
            <LogOut className="h-3.5 w-3.5 text-rose-500 dark:text-rose-400" />
            退出登录
          </Button>
        </div>
 
        <div className="flex justify-center pt-1 border-t border-sidebar-border">
          <BackendStatus />
        </div>
      </div>
    </div>
  )
}
 
export function Sidebar() {
  const [open, setOpen] = useState(false)
 
  return (
    <>
      {/* Mobile Header and Drawer */}
      <div className="lg:hidden">
        <header className="fixed top-0 left-0 right-0 h-14 bg-sidebar/60 backdrop-blur-xl border-b border-sidebar-border z-40 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger render={
                <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded-lg">
                  <Menu className="h-5 w-5" />
                </Button>
              } />
              <SheetContent side="left" className="w-64 p-0 flex flex-col border-r border-sidebar-border bg-sidebar">
                <SidebarContent onNavigate={() => setOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="flex items-center gap-1.5 ml-1">
              <BookOpen className="h-4.5 w-4.5 text-indigo-500" />
              <span className="font-bold text-sm bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">AI 小说生成器</span>
            </div>
          </div>
        </header>
      </div>
 
      {/* Desktop: fixed sidebar */}
      <aside className="hidden lg:flex w-60 h-full border-r border-sidebar-border bg-sidebar flex-col shrink-0 relative z-10">
        <SidebarContent />
      </aside>
    </>
  )
}
