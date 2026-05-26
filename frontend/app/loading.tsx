import { Skeleton } from "@/components/ui/skeleton"

export default function HomeLoading() {
  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10 animate-fade-in">
      {/* 🚀 Hero Banner Skeleton */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-950/20 via-purple-950/10 to-background border border-border/40 p-8 md:p-10">
        <div className="max-w-2xl space-y-4">
          <Skeleton className="h-6 w-36 bg-primary/20 rounded-full" />
          <Skeleton className="h-10 w-96 bg-muted/50 rounded-2xl" />
          <Skeleton className="h-4 w-11/12 bg-muted/40 rounded-lg" />
          <Skeleton className="h-4 w-2/3 bg-muted/40 rounded-lg" />
          <div className="flex gap-3 pt-2">
            <Skeleton className="h-10 w-32 bg-primary/30 rounded-xl" />
            <Skeleton className="h-10 w-36 bg-muted/50 rounded-xl" />
          </div>
        </div>
      </div>

      {/* 📊 Telemetry Card Grid Mock */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4 rounded-2xl border border-border/30 bg-card/40 backdrop-blur-md">
            <Skeleton className="h-10 w-10 bg-muted/50 rounded-xl shrink-0" />
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-3 w-16 bg-muted/40 rounded-md" />
              <Skeleton className="h-6 w-24 bg-muted/50 rounded-lg" />
            </div>
          </div>
        ))}
      </div>

      {/* 📋 Project List Grid Mock */}
      <div className="space-y-5">
        <div className="flex justify-between items-center">
          <Skeleton className="h-6 w-32 bg-muted/50 rounded-lg" />
          <Skeleton className="h-5 w-40 bg-muted/40 rounded-md" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="glass-card border border-border/30 rounded-2xl p-5 h-[210px] flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <Skeleton className="h-6 w-36 bg-muted/50 rounded-lg" />
                  <Skeleton className="h-5 w-12 bg-muted/40 rounded-full" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-3.5 w-full bg-muted/40 rounded-md" />
                  <Skeleton className="h-3.5 w-full bg-muted/40 rounded-md" />
                  <Skeleton className="h-3.5 w-4/5 bg-muted/40 rounded-md" />
                </div>
              </div>
              
              <div className="flex justify-between items-center border-t border-border/20 pt-3">
                <Skeleton className="h-4 w-28 bg-muted/40 rounded-md" />
                <Skeleton className="h-7 w-7 bg-muted/40 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
