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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
      suppressHydrationWarning
      style={{ colorScheme: "dark" } as React.CSSProperties}
    >
      <body className="min-h-full flex bg-background text-foreground">
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
