import { Skeleton } from "@/components/ui/skeleton"
import { Sparkles } from "lucide-react"

export default function ProjectLoading() {
  return (
    <div className="relative w-full h-[80vh] min-h-[500px] flex items-center justify-center overflow-hidden animate-in fade-in duration-500">
      {/* 1. Background Glow Blobs */}
      <div className="absolute top-1/4 left-1/3 w-80 h-80 rounded-full bg-primary/10 blur-[130px] pointer-events-none animate-pulse" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 rounded-full bg-indigo-500/10 blur-[130px] pointer-events-none animate-pulse" />
      
      {/* 2. Glassmorphic Center Loading Card */}
      <div className="absolute z-20 flex flex-col items-center p-8 max-w-sm w-full mx-4 rounded-3xl glass-panel border-primary/20 shadow-2xl shadow-primary/5 border-glow animate-float text-center">
        {/* Animated Glowing Ring */}
        <div className="relative flex items-center justify-center w-16 h-16 mb-5">
          <div className="absolute inset-0 rounded-full border-2 border-primary/20" />
          <div className="absolute inset-0 rounded-full border-2 border-t-primary border-r-primary animate-spin" />
          <Sparkles className="w-6 h-6 text-primary animate-pulse" />
        </div>
        
        <h3 className="text-base font-bold tracking-tight text-foreground flex items-center gap-1.5 justify-center mb-1">
          智能创作空间
        </h3>
        <p className="text-xs text-muted-foreground font-medium animate-pulse mb-5">
          正在载入小说创作管线与资源...
        </p>
        
        {/* Decorative dynamic status messages */}
        <div className="w-full bg-secondary/15 rounded-2xl border border-border/20 px-4 py-3 text-[11px] text-muted-foreground/80 font-mono space-y-1.5 text-left">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>Connecting to database...</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground/50">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40" />
            <span>Loading LLM node configurations...</span>
          </div>
        </div>
      </div>

      {/* 3. Blurred Backdrop Skeleton Layout (to give depth of field) */}
      <div className="w-full h-full max-w-6xl mx-auto space-y-6 pb-10 blur-[5px] opacity-20 scale-[0.98] pointer-events-none select-none transition-all duration-700">
        {/* Header Bar Area */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/20 pb-5">
          <div className="space-y-2">
            <Skeleton className="h-8 w-72 bg-muted/50 rounded-xl" />
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-20 bg-muted/40 rounded-lg" />
              <Skeleton className="h-4 w-32 bg-muted/40 rounded-lg" />
            </div>
          </div>
          <Skeleton className="h-10 w-36 bg-muted/50 rounded-xl shrink-0" />
        </div>

        {/* Horizontal Tabs Row */}
        <div className="flex gap-2 overflow-x-auto pb-1.5 border-b border-border/10">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton
              key={i}
              className={`h-9 shrink-0 bg-muted/40 rounded-xl ${
                i === 0 ? "w-16 bg-muted/60" : i === 1 ? "w-24" : i === 2 ? "w-20" : "w-16"
              }`}
            />
          ))}
        </div>

        {/* Main Workspace mock Grid */}
        <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px] h-[55vh]">
          {/* Mock Sidebar Column */}
          <div className="hidden xl:flex flex-col h-full bg-card/40 border border-border/30 rounded-2xl p-4 space-y-4">
            <div className="flex justify-between items-center border-b border-border/20 pb-3 shrink-0">
              <Skeleton className="h-5 w-24 bg-muted/50 rounded-lg" />
              <Skeleton className="h-7 w-7 bg-muted/50 rounded-full" />
            </div>
            <div className="flex-1 space-y-2.5 overflow-hidden">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="p-3 border border-border/10 rounded-xl space-y-2 bg-secondary/10">
                  <div className="flex justify-between items-center">
                    <Skeleton className="h-4 w-12 bg-muted/50 rounded-md" />
                    <Skeleton className="h-3 w-8 bg-muted/40 rounded-md" />
                  </div>
                  <Skeleton className="h-4 w-full bg-muted/40 rounded-md" />
                </div>
              ))}
            </div>
          </div>

          {/* Mock Editor Column */}
          <div className="flex flex-col h-full bg-card/50 border border-border/30 rounded-2xl p-5 space-y-5">
            <div className="flex items-center justify-between border-b border-border/20 pb-3 shrink-0">
              <div className="flex items-center gap-3">
                <Skeleton className="h-5 w-28 bg-muted/50 rounded-md" />
                <Skeleton className="h-4 w-16 bg-muted/40 rounded-md" />
              </div>
              <div className="flex gap-2">
                <Skeleton className="h-8 w-16 bg-muted/40 rounded-lg" />
                <Skeleton className="h-8 w-20 bg-muted/40 rounded-lg" />
              </div>
            </div>

            <div className="flex-1 space-y-4">
              <Skeleton className="h-6 w-3/4 bg-muted/50 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-full bg-muted/40 rounded-md" />
                <Skeleton className="h-4 w-full bg-muted/40 rounded-md" />
                <Skeleton className="h-4 w-11/12 bg-muted/40 rounded-md" />
              </div>
            </div>
          </div>

          {/* Mock Status Pane Column */}
          <div className="hidden lg:flex flex-col h-full bg-card/40 border border-border/30 rounded-2xl p-4 space-y-5">
            <div className="border-b border-border/20 pb-3 shrink-0">
              <Skeleton className="h-5 w-24 bg-muted/50 rounded-lg" />
            </div>
            <div className="space-y-4 flex-1">
              <div className="flex items-center gap-4 bg-secondary/15 p-3 rounded-xl border border-border/10">
                <Skeleton className="h-12 w-12 bg-muted/50 rounded-full shrink-0" />
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-4 w-16 bg-muted/50 rounded-md" />
                  <Skeleton className="h-3.5 w-full bg-muted/40 rounded-md" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
