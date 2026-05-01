"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookOpen, Settings, Plus, Home, Menu } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { useProjects } from "@/lib/hooks/use-projects"
import { useState } from "react"

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const { data: projects } = useProjects()

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
          <Link href="/" onClick={onNavigate}>
            <Button variant={pathname === "/" ? "secondary" : "ghost"} className="w-full justify-start gap-2">
              <Home className="h-4 w-4" />
              项目列表
            </Button>
          </Link>

          {projects?.map((p: any) => (
            <Link key={p.id} href={`/projects/${p.id}`} onClick={onNavigate}>
              <Button
                variant={pathname.startsWith(`/projects/${p.id}`) ? "secondary" : "ghost"}
                className="w-full justify-start gap-2 text-sm"
              >
                <BookOpen className="h-4 w-4 shrink-0" />
                <span className="truncate">{p.name}</span>
              </Button>
            </Link>
          ))}
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
            全局设置
          </Button>
        </Link>
      </div>
    </>
  )
}

export function Sidebar() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile: Sheet drawer */}
      <div className="lg:hidden">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger>
            <Button variant="ghost" size="icon" className="fixed top-3 left-3 z-50">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0 flex flex-col">
            <SidebarContent onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>
      </div>

      {/* Desktop: fixed sidebar */}
      <aside className="hidden lg:flex w-64 h-full border-r bg-sidebar flex-col shrink-0">
        <SidebarContent />
      </aside>
    </>
  )
}
