const CHAPTERS = [
  ["s01_agent_loop", "agent_loop.py", "Agent Loop + Memory", "一个循环 + 一个记忆文件 = 最简单的学习 agent"],
  ["s02_background_memory_review", "background_memory_review.py", "Background Memory Review", "每次对话结束，问自己学到了什么"],
  ["s03_background_skill_review", "background_skill_review.py", "Background Skill Review", "好方案不只用一次，沉淀为技能"],
  ["s04_memory_system", "memory_system.py", "Memory System", "记忆不该只有一个文件"],
  ["s05_skill_lifecycle", "skill_lifecycle.py", "Skill Lifecycle", "技能有生老病死"],
  ["s06_skill_creation", "skill_creation.py", "Skill Creation Safety", "什么该学、什么不该学，有规则"],
  ["s07_curator_state", "curator_state.py", "Curator State", "30 天不用就标记，90 天归档"],
  ["s08_curator_llm", "curator_llm.py", "Curator LLM", "技能太多会乱，定期合并整理"],
  ["s09_context_management", "context_management.py", "Context Management", "上下文满了就压，重要的事留在外面"],
  ["s10_insights", "insights.py", "Insights Engine", "不知道用了多少 token，就无法优化"],
  ["s11_error_recovery", "error_recovery.py", "Error Recovery", "出错不是终点，是学习的起点"],
  ["s12_comprehensive", "comprehensive.py", "Complete Self-Evolving Agent", "六层归位，一个会自己进化的 agent"],
  ["s13_cron_scheduler", "cron_scheduler.py", "Cron Scheduler", "定好时间，agent 自己醒来干活"],
  ["s14_gateway", "gateway.py", "Gateway", "一个 gateway，连接所有平台"],
  ["s15_profiles", "profiles.py", "Multi-Profile System", "一套 Hermes，多个人设"],
  ["s16_agent_teams", "agent_teams.py", "Agent Teams", "一个搞不定，组队来"],
  ["s17_mcp_plugin", "mcp_plugin.py", "MCP Plugin", "能力不够？接上 MCP"],
  ["s18_full_hermes", "full_hermes.py", "Full Hermes", "全部机制，一个完整 Hermes"],
  ["s19_permission", "permission.py", "Permission System", "先划边界，再给自由"],
  ["s20_hooks", "hooks.py", "Hook System", "挂在循环上，不写进循环里"],
  ["s21_worktree", "worktree.py", "Worktree Isolation", "各干各的目录，互不干扰"],
  ["s22_planning", "planning.py", "Planning System", "没计划的 agent 走哪算哪"],
  ["s23_autonomous", "autonomous.py", "Autonomous Agents", "自己看板，有活就认领"],
  ["s24_system_prompt", "system_prompt.py", "System Prompt Assembly", "prompt 是拼出来的，不是写死的"],
];

export default function ChaptersPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      <div className="mb-10">
        <p className="text-sm font-semibold text-[#6ee7d8] mb-2">学习路径</p>
        <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-5">24 个递进课程</h1>
        <p className="text-lg text-[#a7b0bc] max-w-3xl leading-relaxed">
          每章一个文件夹，每章一个可运行 Python 文件。从 s01 到 s24 读，最后会得到完整 Hermes harness。
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {CHAPTERS.map(([slug, file, title, motto], index) => (
          <section id={slug} key={slug} className="p-5 rounded-lg bg-[#171b21] border border-[#2b3036] scroll-mt-20">
            <div className="flex items-center justify-between gap-3 mb-3">
              <span className="text-xs font-mono text-[#6ee7d8]">s{String(index + 1).padStart(2, "0")}</span>
              <span className="text-xs text-[#f6c177]">{slug}</span>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
            <p className="text-sm text-[#a7b0bc] mb-4">{motto}</p>
            <pre className="text-sm">
<code>{`python ${slug}/${file}`}</code>
            </pre>
          </section>
        ))}
      </div>
    </main>
  );
}
