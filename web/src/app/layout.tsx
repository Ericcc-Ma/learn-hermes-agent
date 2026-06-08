import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Learn Hermes Agent - 自进化 Agent Harness 教程",
  description:
    "从零复刻 Hermes Agent 的自学习系统，24 个递进课程教你构建会记忆、会学习、会调度、会组队的 Agent Harness。",
  openGraph: {
    title: "Learn Hermes Agent",
    description: "从零复刻 Hermes Agent 的自学习系统",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="bg-[#0d1117] text-[#c9d1d9] antialiased min-h-screen font-sans">
        <nav className="border-b border-[#2b3036] bg-[#111418]/95 backdrop-blur sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-6 py-3 sm:py-0 sm:h-14 flex flex-wrap items-center justify-between gap-3">
            <Link href="/" className="font-bold text-lg text-white hover:text-[#58a6ff] transition-colors whitespace-nowrap">
              Learn Hermes Agent
            </Link>
            <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
              <Link href="/demo" className="text-[#a7b0bc] hover:text-white transition-colors whitespace-nowrap">
                Demo
              </Link>
              <Link href="/chapters" className="text-[#a7b0bc] hover:text-white transition-colors whitespace-nowrap">
                章节
              </Link>
              <Link href="/source-map" className="text-[#a7b0bc] hover:text-white transition-colors whitespace-nowrap">
                源码地图
              </Link>
              <a href="https://github.com/Ericcc-Ma/learn-hermes-agent" className="text-[#8b949e] hover:text-white transition-colors whitespace-nowrap">
                GitHub
              </a>
            </div>
          </div>
        </nav>
        {children}
        <footer className="border-t border-[#21262d] py-8 mt-20">
          <div className="max-w-6xl mx-auto px-6 text-center text-sm text-[#484f58]">
            <p>Learn Hermes Agent - Agency 来自模型，自进化来自 Harness。</p>
            <p className="mt-2">
              <a href="https://github.com/Ericcc-Ma/learn-hermes-agent" className="hover:text-[#58a6ff] transition-colors">GitHub</a>
              {" · "}MIT License
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
