import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Learn Hermes Agent — Build a Self-Evolving Agent",
  description:
    "12 progressive lessons teaching you to build a self-evolving agent from scratch. Multi-provider LLM support.",
  openGraph: {
    title: "Learn Hermes Agent",
    description: "Build a Self-Evolving Agent Harness from Scratch",
    type: "website",
  },
};

const CHAPTERS = [
  { id: "s01", title: "Agent Loop + Memory", motto: "One loop + one memory file = the simplest learning agent" },
  { id: "s02", title: "Background Memory Review", motto: "After every conversation, ask 'what did I learn?'" },
  { id: "s03", title: "Background Skill Review", motto: "Good solutions aren't one-offs — distill them into skills" },
  { id: "s04", title: "Memory System Deep Dive", motto: "Memory shouldn't be just one file" },
  { id: "s05", title: "Skill Lifecycle", motto: "Skills have a lifecycle" },
  { id: "s06", title: "Skill Creation Safety", motto: "What to learn, what not to learn — rules exist" },
  { id: "s07", title: "Curator: Auto Transitions", motto: "30 days unused → stale, rules decide" },
  { id: "s08", title: "Curator: LLM Merge", motto: "Too many skills get messy — merge them periodically" },
  { id: "s09", title: "Context Management", motto: "Context fills up — compress it, protect what matters" },
  { id: "s10", title: "Insights Engine", motto: "You can't optimize what you don't measure" },
  { id: "s11", title: "Error Recovery", motto: "Errors are learning starting points" },
  { id: "s12", title: "Complete Self-Evolving Agent", motto: "Six layers, one self-evolving agent" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0d1117] text-[#c9d1d9] antialiased min-h-screen font-sans">
        <nav className="border-b border-[#21262d] bg-[#161b22] sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
            <a href="/" className="font-bold text-lg text-white hover:text-[#58a6ff] transition-colors">
              Learn Hermes Agent
            </a>
            <div className="flex gap-4 text-sm">
              <a href="https://github.com/hongye/learn-hermes-agent" className="text-[#8b949e] hover:text-white transition-colors">
                GitHub
              </a>
              <a href="#chapters" className="text-[#8b949e] hover:text-white transition-colors">
                Chapters
              </a>
            </div>
          </div>
        </nav>
        {children}
        <footer className="border-t border-[#21262d] py-8 mt-20">
          <div className="max-w-6xl mx-auto px-6 text-center text-sm text-[#484f58]">
            <p>Learn Hermes Agent — Build the harness that learns. The model will do the rest.</p>
            <p className="mt-2">
              <a href="https://github.com/hongye/learn-hermes-agent" className="hover:text-[#58a6ff] transition-colors">GitHub</a>
              {" · "}MIT License
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
