const CHAPTERS = [
  { id: "01", slug: "s01_agent_loop", title: "Agent Loop + Memory", motto: "One loop + one memory file = the simplest learning agent", layer: "Memory Foundation" },
  { id: "02", slug: "s02_background_memory_review", title: "Background Memory Review", motto: "After every conversation, ask 'what did I learn?'", layer: "Real-time Learning" },
  { id: "03", slug: "s03_background_skill_review", title: "Background Skill Review", motto: "Good solutions aren't one-offs — distill them into skills", layer: "Real-time Learning" },
  { id: "04", slug: "s04_memory_system", title: "Memory System Deep Dive", motto: "Memory shouldn't be just one file", layer: "Memory System" },
  { id: "05", slug: "s05_skill_lifecycle", title: "Skill Lifecycle", motto: "Skills have a lifecycle", layer: "Skill Management" },
  { id: "06", slug: "s06_skill_creation", title: "Skill Creation Safety", motto: "What to learn, what not to learn — rules exist", layer: "Skill Management" },
  { id: "07", slug: "s07_curator_state", title: "Curator: Auto Transitions", motto: "30 days unused → stale, rules decide", layer: "Long-term Maintenance" },
  { id: "08", slug: "s08_curator_llm", title: "Curator: LLM Merge", motto: "Too many skills get messy — merge them periodically", layer: "Long-term Maintenance" },
  { id: "09", slug: "s09_context_management", title: "Context Management", motto: "Context fills up — compress it, protect what matters", layer: "Context Management" },
  { id: "10", slug: "s10_insights", title: "Insights Engine", motto: "You can't optimize what you don't measure", layer: "Data Analytics" },
  { id: "11", slug: "s11_error_recovery", title: "Error Recovery", motto: "Errors are learning starting points", layer: "Error Recovery" },
  { id: "12", slug: "s12_comprehensive", title: "Complete Self-Evolving Agent", motto: "Six layers, one self-evolving agent", layer: "Full Integration" },
];

const LAYERS = [
  { name: "Real-time Learning", chapters: "s02-s03", desc: "Background review extracts memories and skills from every conversation" },
  { name: "Skill Management", chapters: "s05-s06", desc: "Lifecycle states, umbrella structure, and safety guardrails" },
  { name: "Long-term Maintenance", chapters: "s07-s08", desc: "Curator auto-transitions and LLM-powered merging" },
  { name: "Memory System", chapters: "s01,s04", desc: "FTS5 full-text search, pluggable providers, cross-session knowledge" },
  { name: "Context Management", chapters: "s09", desc: "Intelligent compression that protects self-evolved knowledge" },
  { name: "Data Analytics", chapters: "s10", desc: "Quantify self-evolution with token/cost/tool analysis" },
];

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-20 md:py-32 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1a3a5c] text-[#58a6ff] text-xs font-medium mb-6">
          12 Progressive Lessons · 6 Self-Evolution Layers
        </div>
        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white mb-6">
          Build a{" "}
          <span className="gradient-text">Self-Evolving</span>{" "}
          Agent Harness
        </h1>
        <p className="text-lg md:text-xl text-[#8b949e] max-w-2xl mx-auto mb-8">
          Every conversation is a learning opportunity. Learn how to build an agent that
          automatically extracts knowledge, creates reusable skills, and gets smarter
          with every interaction.
        </p>
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          <span className="px-3 py-1 rounded-full bg-[#161b22] border border-[#21262d] text-xs text-[#8b949e]">
            Anthropic
          </span>
          <span className="px-3 py-1 rounded-full bg-[#161b22] border border-[#21262d] text-xs text-[#8b949e]">
            DeepSeek
          </span>
          <span className="px-3 py-1 rounded-full bg-[#161b22] border border-[#21262d] text-xs text-[#8b949e]">
            OpenAI
          </span>
          <span className="px-3 py-1 rounded-full bg-[#161b22] border border-[#21262d] text-xs text-[#8b949e]">
            Qwen / GLM / Moonshot
          </span>
          <span className="px-3 py-1 rounded-full bg-[#161b22] border border-[#21262d] text-xs text-[#8b949e]">
            Ollama
          </span>
        </div>
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="https://github.com/hongye/learn-hermes-agent"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-white text-black font-semibold text-sm hover:bg-[#e6e6e6] transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            View on GitHub
          </a>
          <a
            href="#chapters"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-[#30363d] text-white font-semibold text-sm hover:border-[#58a6ff] transition-colors"
          >
            Start Learning →
          </a>
        </div>
      </section>

      {/* Six Layers */}
      <section className="max-w-6xl mx-auto px-6 py-16 border-t border-[#21262d]">
        <h2 className="text-2xl font-bold text-white text-center mb-12">
          The Six-Layer Self-Evolution Architecture
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {LAYERS.map((layer, i) => (
            <div key={i} className="p-5 rounded-xl bg-[#161b22] border border-[#21262d] card-hover">
              <div className="text-xs text-[#58a6ff] mb-2">{layer.chapters}</div>
              <h3 className="font-semibold text-white mb-2">{layer.name}</h3>
              <p className="text-sm text-[#8b949e]">{layer.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Chapters Grid */}
      <section id="chapters" className="max-w-6xl mx-auto px-6 py-16 border-t border-[#21262d]">
        <h2 className="text-2xl font-bold text-white text-center mb-4">12 Progressive Lessons</h2>
        <p className="text-center text-[#8b949e] mb-12">
          Each chapter adds one self-evolution mechanism. Read in order from s01 to s12.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {CHAPTERS.map((ch) => (
            <a
              key={ch.id}
              href={`https://github.com/hongye/learn-hermes-agent/tree/main/${ch.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-5 rounded-xl bg-[#161b22] border border-[#21262d] card-hover group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-[#58a6ff]">s{ch.id}</span>
                <span className="text-[10px] text-[#484f58] uppercase">{ch.layer}</span>
              </div>
              <h3 className="font-semibold text-white group-hover:text-[#58a6ff] transition-colors mb-1">
                {ch.title}
              </h3>
              <p className="text-xs text-[#8b949e] italic">"{ch.motto}"</p>
            </a>
          ))}
        </div>
      </section>

      {/* Quick Start */}
      <section className="max-w-6xl mx-auto px-6 py-16 border-t border-[#21262d]">
        <h2 className="text-2xl font-bold text-white text-center mb-8">Quick Start</h2>
        <div className="max-w-2xl mx-auto">
          <pre className="text-sm mb-4">
<code>{`git clone https://github.com/hongye/learn-hermes-agent
cd learn-hermes-agent
pip install -r requirements.txt
cp .env.example .env  # Edit: choose LLM_PROVIDER and fill API key

# Use Anthropic (default)
python s01_agent_loop/code.py

# Use DeepSeek
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... MODEL_ID=deepseek-chat \\
  python s01_agent_loop/code.py

# Use Qwen / GLM / any OpenAI-compatible
LLM_PROVIDER=openai_compat LLM_BASE_URL=https://your-api.com/v1 \\
  python s01_agent_loop/code.py`}</code>
          </pre>
        </div>
      </section>

      {/* Philosophy */}
      <section className="max-w-6xl mx-auto px-6 py-16 border-t border-[#21262d] text-center">
        <blockquote className="text-xl md:text-2xl text-[#8b949e] italic max-w-2xl mx-auto">
          "Agency comes from the model. Self-evolution comes from the harness.
          Every conversation is a learning opportunity — knowledge learned is automatically
          distilled into reusable skills and memories."
        </blockquote>
        <p className="mt-6 text-sm text-[#484f58]">
          Build the harness that learns. The model will do the rest.
        </p>
      </section>
    </div>
  );
}
