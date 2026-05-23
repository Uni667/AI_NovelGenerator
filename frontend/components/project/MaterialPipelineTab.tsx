"use client"

import { useState, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Loader2, UploadCloud, Zap, ShieldAlert, CheckCircle2, ChevronRight, FileJson } from "lucide-react"
import { api } from "@/lib/api-client"
import { useProjectContext } from "./ProjectContext"
import { toast } from "sonner"
import type { MaterialEntity, DiagnosisReport } from "@/lib/types"

const STEPS = [
  { id: 1, title: "1. 素材投喂", desc: "上传原始散乱设定" },
  { id: 2, title: "2. X光解构", desc: "AI剥离结构化数据" },
  { id: 3, title: "3. 平台体检", desc: "查漏补缺排雷" },
  { id: 4, title: "4. 优化入库", desc: "一键精修与装配" }
]

export function MaterialPipelineTab() {
  const { projectId } = useProjectContext()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [currentStep, setCurrentStep] = useState(1)
  const [rawText, setRawText] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [entities, setEntities] = useState<MaterialEntity[]>([])
  const [diagnoses, setDiagnoses] = useState<Record<string, DiagnosisReport>>({})
  const [optimizedContents, setOptimizedContents] = useState<Record<string, string>>({})

  // 步骤 1: 读取文件
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    
    setIsProcessing(true)
    try {
      let combinedText = ""
      for (let i = 0; i < files.length; i++) {
        const text = await files[i].text()
        combinedText += `\n\n--- 文件: ${files[i].name} ---\n\n${text}`
      }
      setRawText(combinedText)
      toast.success(`成功读取 ${files.length} 个文件，共 ${combinedText.length} 字`)
    } catch (err) {
      toast.error("读取文件失败")
    } finally {
      setIsProcessing(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  // 步骤 2: 解构
  const handleDeconstruct = async () => {
    if (!rawText.trim()) return toast.error("请先输入或上传素材")
    
    setIsProcessing(true)
    setCurrentStep(2)
    try {
      const res = await api.materials.decompose(projectId, rawText)
      setEntities(res.entities || [])
      toast.success(`成功解构出 ${res.entities?.length || 0} 个设定实体`)
      setCurrentStep(3) // 自动进入下一步
    } catch (err: any) {
      toast.error(err.message || "解构失败")
      setCurrentStep(1)
    } finally {
      setIsProcessing(false)
    }
  }

  // 步骤 3: 诊断
  const handleDiagnose = async () => {
    if (entities.length === 0) return
    
    setIsProcessing(true)
    try {
      const newDiagnoses: Record<string, DiagnosisReport> = {}
      // 串行诊断避免并发过高（实际生产环境可用 Promise.all 限制并发）
      for (const entity of entities) {
        const res = await api.materials.diagnose(projectId, entity)
        newDiagnoses[entity.id] = res.diagnosis
      }
      setDiagnoses(newDiagnoses)
      toast.success("全身体检完成")
      setCurrentStep(4)
    } catch (err: any) {
      toast.error(err.message || "体检失败")
    } finally {
      setIsProcessing(false)
    }
  }

  // 步骤 4: 优化单卡
  const handleOptimize = async (entity: MaterialEntity) => {
    const diag = diagnoses[entity.id]
    if (!diag) return toast.error("请先完成体检")
    
    try {
      toast.info(`正在优化: ${entity.title}...`)
      const res = await api.materials.optimize(projectId, entity, diag)
      setOptimizedContents(prev => ({ ...prev, [entity.id]: res.optimized_content }))
      toast.success(`${entity.title} 优化完成！`)
    } catch (err: any) {
      toast.error(err.message || "优化失败")
    }
  }

  const getTypeLabel = (type: string) => {
    const map: Record<string, string> = { character: "角色", world_rule: "世界观", plot_arc: "大纲片段", hook: "爽点钩子" }
    return map[type] || type
  }

  return (
    <div className="space-y-6">
      {/* 顶部进度条 */}
      <Card className="glass-panel border-border/40">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            {STEPS.map((step, idx) => (
              <div key={step.id} className="flex flex-col items-center flex-1 relative">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-500 z-10 ${
                  currentStep >= step.id ? "bg-primary text-primary-foreground shadow-[0_0_15px_oklch(0.68_0.19_285/0.5)]" : "bg-muted text-muted-foreground"
                }`}>
                  {step.id}
                </div>
                <div className="mt-3 text-center">
                  <p className={`text-sm font-bold ${currentStep >= step.id ? "text-foreground" : "text-muted-foreground"}`}>{step.title}</p>
                  <p className="text-xs text-muted-foreground mt-1">{step.desc}</p>
                </div>
                {idx < STEPS.length - 1 && (
                  <div className={`absolute top-5 left-[50%] right-[-50%] h-[2px] transition-all duration-1000 ${
                    currentStep > step.id ? "bg-primary" : "bg-border"
                  }`} />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 工作区 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[60vh]">
        {/* 左侧：输入/解构区 */}
        <Card className="glass-panel border-border/40 flex flex-col h-full">
          <CardHeader className="pb-4 border-b border-border/30">
            <div className="flex justify-between items-center">
              <CardTitle className="text-base font-bold">
                {currentStep === 1 ? "1. 投喂原始素材" : "提取结果预览"}
              </CardTitle>
              {currentStep === 1 && (
                <div>
                  <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" multiple accept=".txt,.md" />
                  <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
                    <UploadCloud className="w-4 h-4 mr-2" /> 导入文件
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 flex flex-col">
            {currentStep === 1 ? (
              <div className="p-4 flex-1 flex flex-col">
                <textarea
                  className="flex-1 w-full p-4 rounded-md bg-background/50 border border-input resize-none focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                  placeholder="在此处粘贴你的散乱废稿、脑洞设定，或者点击右上角上传多个txt文件..."
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                />
                <Button 
                  className="mt-4 w-full shadow-glow" 
                  onClick={handleDeconstruct} 
                  disabled={isProcessing || !rawText}
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileJson className="w-4 h-4 mr-2" />}
                  启动 AI 解构
                </Button>
              </div>
            ) : (
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {entities.map(ent => (
                    <div key={ent.id} className="p-4 rounded-lg border border-border bg-card/40 relative group transition-all hover:border-primary/40">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-bold text-primary">{ent.title}</h4>
                        <Badge variant="secondary">{getTypeLabel(ent.type)}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-3">{ent.content}</p>
                    </div>
                  ))}
                  {entities.length > 0 && currentStep === 3 && (
                    <Button className="w-full mt-4" onClick={handleDiagnose} disabled={isProcessing}>
                      {isProcessing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ShieldAlert className="w-4 h-4 mr-2" />}
                      开始 X光平台体检
                    </Button>
                  )}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* 右侧：诊断与优化工厂 */}
        <Card className="glass-panel border-border/40 flex flex-col h-full">
          <CardHeader className="pb-4 border-b border-border/30">
            <CardTitle className="text-base font-bold text-gradient-primary">
              体检与优化装配工厂
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-0">
            {currentStep < 4 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm flex-col gap-4">
                <Zap className="w-8 h-8 opacity-20" />
                <p>等待解构与体检完成...</p>
              </div>
            ) : (
              <ScrollArea className="h-full p-4">
                <div className="space-y-6">
                  {entities.map(ent => {
                    const diag = diagnoses[ent.id]
                    const optimized = optimizedContents[ent.id]
                    if (!diag) return null
                    
                    return (
                      <div key={ent.id} className="p-4 rounded-lg border border-border bg-card/60 shadow-sm relative">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-bold">{ent.title}</h4>
                          <div className="flex gap-2">
                            {diag.is_compliant ? (
                              <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">合规</Badge>
                            ) : (
                              <Badge variant="destructive">违规警告</Badge>
                            )}
                            {diag.has_toxic_tropes && (
                              <Badge variant="destructive" className="animate-pulse">包含毒点</Badge>
                            )}
                            <Badge variant="outline" className={diag.score >= 80 ? "text-emerald-400" : "text-amber-400"}>
                              评分: {diag.score}
                            </Badge>
                          </div>
                        </div>

                        {/* 体检报告区 */}
                        <div className="mb-4 space-y-2 text-xs bg-background/50 p-3 rounded border border-border/50">
                          {diag.issues.length > 0 && (
                            <p className="text-destructive"><span className="font-bold">❌ 缺陷:</span> {diag.issues.join("; ")}</p>
                          )}
                          {diag.missing_elements.length > 0 && (
                            <p className="text-amber-500"><span className="font-bold">⚠️ 缺失:</span> {diag.missing_elements.join("; ")}</p>
                          )}
                          <p className="text-emerald-400"><span className="font-bold">💡 建议:</span> {diag.suggestion}</p>
                        </div>

                        {/* 内容展示区 */}
                        <div className="mt-3">
                          <p className="text-sm text-muted-foreground mb-3 border-l-2 border-border pl-3">
                            {optimized || ent.content}
                          </p>
                          
                          <div className="flex justify-end gap-2">
                            {!optimized ? (
                              <Button size="sm" variant="secondary" onClick={() => handleOptimize(ent)} className="shadow-glow hover:-translate-y-0.5">
                                <Zap className="w-3 h-3 mr-1 text-primary" /> AI 一键优化
                              </Button>
                            ) : (
                              <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 flex items-center">
                                <CheckCircle2 className="w-3 h-3 mr-1" /> 已优化
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}

                  <div className="pt-6 border-t border-border mt-6">
                    <Button className="w-full shadow-glow" size="lg">
                      <UploadCloud className="w-4 h-4 mr-2" /> 同步至项目核心架构
                    </Button>
                  </div>
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
