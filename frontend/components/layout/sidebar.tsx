"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookOpen, Settings, Plus, Home } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useProjects } from "@/lib/hooks/use-projects"

export function Sidebar() {
  const pathname = usePathname()
  const { data: projects } = useProjects()

  return (
    <aside className="w-64 h-full border-r bg-sidebar flex flex-col shrink-0">
      <div className="p-4 border-b">
        <Link href="/" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <span className="font-bold text-lg">AI 小说生成器</span>
        </Link>
      </div>

      <ScrollArea className="flex-1">
        <nav className="p-3 space-y-1">
          <Link href="/">
            <Button variant={pathname === "/" ? "secondary" : "ghost"} className="w-full justify-start gap-2">
              <Home className="h-4 w-4" />
              项目列表
            </Button>
          </Link>

          {projects?.map((p: any) => (
            <Link key={p.id} href={`/projects/${p.id}`}>
              <Button
                variant={pathname.startsWith(`/projects/${p.id}`) ? "secondary" : "ghost"}
                className="w-full justify-start gap-2 text-sm"
              >
                <BookOpen className="h-4 w-4" />
                <span className="truncate">{p.name}</span>
              </Button>
            </Link>
          ))}
        </nav>
      </ScrollArea>

      <div className="p-3 border-t">
        <Link href="/projects/new">
          <Button className="w-full gap-2" size="sm">
            <Plus className="h-4 w-4" />
            新建项目
          </Button>
        </Link>
        <Link href="/settings" className="mt-2 block">
          <Button variant="ghost" className="w-full justify-start gap-2" size="sm">
            <Settings className="h-4 w-4" />
            全局设置
          </Button>
        </Link>
      </div>
    </aside>
  )
}
