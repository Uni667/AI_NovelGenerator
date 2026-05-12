import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Docker 自托管使用 standalone 输出，仅包含运行时必需文件 */
  output: process.env.NEXT_STANDALONE === "true" ? "standalone" : undefined,

  /* 生产环境 API 地址，通过环境变量注入 */
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001",
  },

  /* 禁止在 production 中显示 Next.js 版本号 */
  poweredByHeader: false,
};

export default nextConfig;
