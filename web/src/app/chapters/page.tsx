const CHAPTERS = [
  ["s01_agent_loop", "Agent Loop + Memory", "一个循环 + 一个记忆文件 = 最简单的学习 agent"],
  ["s02_background_memory_review", "Background Memory Review", "每次对话结束，问自己学到了什么"],
  ["s03_background_skill_review", "Background Skill Review", "好方案不只用一次，沉淀为技能"],
  ["s04_memory_system", "Memory System", "记忆不该只有一个文件"],
  ["s05_skill_lifecycle", "Skill Lifecycle", "技能有生老病死"],
  ["s06_skill_creation", "Skill Creation Safety", "什么该学、什么不该学，有规则"],
  ["s07_curator_state", "Curator State", "30 天不用就标记，90 天归档"],
  ["s08_curator_llm", "Curator LLM", "技能太多会乱，定期合并整理"],
  ["s09_context_management", "Context Management", "上下文满了就压，重要的事留在外面"],
  ["s10_insights", "Insights Engine", "不知道用了多少 token，就无法优化"],
  ["s11_error_recovery", "Error Recovery", "出错不是终点，是学习的起点"],
  ["s12_comprehensive", "Complete Self-Evolving Agent", "六层归位，一个会自己进化的 agent"],
];

export default function ChaptersPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      <div className="mb-10">
        <p className="text-sm font-semibold text-[#6ee7d8] mb-2">学习路径</p>
        <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-5">12 个递进课程</h1>
        <p className="text-lg text-[#a7b0bc] max-w-3xl leading-relaxed">
          每章一个文件夹，每章一个可运行 `code.py`。从 s01 到 s12 读，最后会得到一个完整自进化 Agent。
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {CHAPTERS.map(([slug, title, motto], index) => (
          <section id={slug} key={slug} className="p-5 rounded-lg bg-[#171b21] border border-[#2b3036] scroll-mt-20">
            <div className="flex items-center justify-between gap-3 mb-3">
              <span className="text-xs font-mono text-[#6ee7d8]">s{String(index + 1).padStart(2, "0")}</span>
              <span className="text-xs text-[#f6c177]">{slug}</span>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
            <p className="text-sm text-[#a7b0bc] mb-4">{motto}</p>
            <pre className="text-sm">
<code>{`python ${slug}/code.py`}</code>
            </pre>
          </section>
        ))}
      </div>
    </main>
  );
}
