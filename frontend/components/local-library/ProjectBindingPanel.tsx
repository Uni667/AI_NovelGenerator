import { Link, Shield } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function ProjectBindingPanel() {
  return (
    <Card className="glass-panel border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-base flex items-center gap-2">
          <Link className="w-4 h-4 text-primary" /> 项目绑定说明
        </CardTitle>
        <CardDescription className="text-xs">
          将本地参考书库绑定到创作项目，为生成流程提供素材支持。
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-6 flex items-center justify-center h-[120px]">
        <div className="text-sm text-muted-foreground bg-muted/20 px-4 py-2 rounded-lg border border-dashed border-border/50 text-center space-y-1">
          <p>请前往对应的 <strong>项目详情页</strong> -{">"} <strong>本地参考库</strong> 标签</p>
          <p className="text-xs">在项目内部进行参考书绑定及各项规则抽取（风格圣经、场景模板等）的独立配置。</p>
        </div>
      </CardContent>
    </Card>
  )
}
