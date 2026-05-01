"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { login, register, setToken, setUser } from "@/lib/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { BookOpen } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [password2, setPassword2] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    if (!username.trim() || !password) {
      setError("请填写用户名和密码")
      return
    }
    if (isRegister && password !== password2) {
      setError("两次密码不一致")
      return
    }
    if (isRegister && password.length < 6) {
      setError("密码至少 6 位")
      return
    }
    setLoading(true)
    try {
      const fn = isRegister ? register : login
      const result = await fn(username.trim(), password)
      setToken(result.token)
      setUser({ user_id: result.user_id, username: result.username })
      router.replace("/")
    } catch (e: any) {
      setError(e.message || "操作失败")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2">
            <BookOpen className="h-10 w-10 text-primary" />
          </div>
          <CardTitle className="text-xl">AI 小说生成器</CardTitle>
          <CardDescription>{isRegister ? "创建新账户" : "登录你的账户"}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>用户名</Label>
              <Input value={username} onChange={e => setUsername(e.target.value)} placeholder="输入用户名" autoFocus />
            </div>
            <div>
              <Label>密码</Label>
              <Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="输入密码" />
            </div>
            {isRegister && (
              <div>
                <Label>确认密码</Label>
                <Input type="password" value={password2} onChange={e => setPassword2(e.target.value)} placeholder="再次输入密码" />
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "处理中..." : isRegister ? "注册" : "登录"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              {isRegister ? "已有账户？" : "没有账户？"}
              <button type="button" className="ml-1 text-primary hover:underline" onClick={() => { setIsRegister(!isRegister); setError("") }}>
                {isRegister ? "去登录" : "去注册"}
              </button>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
