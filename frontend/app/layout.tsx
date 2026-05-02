import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { Providers } from "./providers"
import { Sidebar } from "@/components/layout/sidebar"
import { AuthGuard } from "@/components/layout/auth-guard"

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: "AI 小说生成器",
  description: "基于大语言模型的智能小说写作助手",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
      style={{ colorScheme: "dark light" } as React.CSSProperties}
    >
      <body className="min-h-full flex bg-background text-foreground">
        {/* 关键：body 第一个子节点必须是同步脚本。
            浏览器解析到此处时立即执行，在 CSS 生效前就挂好 dark class，
            从而完全消除白屏闪烁。next-themes 脚本与此等效，不会被覆盖。 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})();
            `,
          }}
        />
        <Providers>
          <AuthGuard>
            <Sidebar />
            <main className="flex-1 overflow-auto p-4 pt-14 lg:p-6 lg:pt-6">{children}</main>
          </AuthGuard>
        </Providers>
      </body>
    </html>
  )
}
