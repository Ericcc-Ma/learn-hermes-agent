const CHAPTERS = [
  { id: "01", slug: "s01_agent_loop", title: "Agent Loop + Memory", motto: "一个循环 + 一个记忆文件", layer: "记忆基础" },
  { id: "02", slug: "s02_background_memory_review", title: "Background Memory Review", motto: "每次对话结束，问自己学到了什么", layer: "实时学习" },
  { id: "03", slug: "s03_background_skill_review", title: "Background Skill Review", motto: "好方案不只用一次，沉淀为技能", layer: "实时学习" },
  { id: "04", slug: "s04_memory_system", title: "Memory System", motto: "记忆不该只有一个文件", layer: "记忆系统" },
  { id: "05", slug: "s05_skill_lifecycle", title: "Skill Lifecycle", motto: "技能有生老病死", layer: "技能管理" },
  { id: "06", slug: "s06_skill_creation", title: "Skill Creation Safety", motto: "什么该学，什么不该学", layer: "技能管理" },
  { id: "07", slug: "s07_curator_state", title: "Curator State", motto: "30 天不用就标记，规则说了算", layer: "长期维护" },
  { id: "08", slug: "s08_curator_llm", title: "Curator LLM", motto: "技能太多会乱，定期合并整理", layer: "长期维护" },
  { id: "09", slug: "s09_context_management", title: "Context Management", motto: "上下文满了就压，重要的事留在外面", layer: "上下文" },
  { id: "10", slug: "s10_insights", title: "Insights Engine", motto: "不知道用了多少 token，就无法优化", layer: "可观测" },
  { id: "11", slug: "s11_error_recovery", title: "Error Recovery", motto: "出错不是终点，是学习的起点", layer: "自愈" },
  { id: "12", slug: "s12_comprehensive", title: "Complete Agent", motto: "六层归位，一个会自己进化的 agent", layer: "集成" },
];

const SOURCE_MAP = [
  ["自学习入口", "agent/background_review.py", "记忆审查、技能审查、禁止捕获规则"],
  ["长期维护", "agent/curator.py", "stale/archive、LLM 合并、报告生成"],
  ["记忆系统", "agent/memory_manager.py", "FTS、外部 provider、上下文注入"],
  ["完整集成", "run_agent.py", "AIAgent 主类，把六层机制接回循环"],
];

export default function Home() {
  return (
    <main>
      <section className="border-b border-[#2b3036] bg-[#111418]">
        <div className="max-w-6xl mx-auto px-6 py-16 md:py-20 grid lg:grid-cols-[1.05fr_0.95fr] gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-[#193b3a] text-[#6ee7d8] text-xs font-medium mb-6">
              12 个递进课程 · 6 层自进化架构 · 支持多模型
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-normal text-white mb-6 leading-tight">
              从零复刻 Hermes Agent 的自学习系统
            </h1>
            <p className="text-lg md:text-xl text-[#b5bdc8] max-w-2xl mb-8 leading-relaxed">
              让 Agent 记住你、学习你、整理自己的技能库，并在每次对话后变得更懂项目。
              这不是 prompt chain 教程，而是自进化 Agent Harness 的工程拆解。
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="/demo"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-md bg-[#f0f3f6] text-[#111418] font-semibold text-sm hover:bg-white transition-colors"
              >
                看 30 秒 Demo
              </a>
              <a
                href="/chapters"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-md border border-[#4b5563] text-white font-semibold text-sm hover:border-[#6ee7d8] transition-colors"
              >
                开始学习
              </a>
              <a
                href="https://github.com/hongye/learn-hermes-agent"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-md border border-[#4b5563] text-white font-semibold text-sm hover:border-[#f6c177] transition-colors"
              >
                GitHub
              </a>
            </div>
          </div>

          <div className="relative min-w-0">
            <div className="rounded-lg border border-[#2b3036] bg-[#0b0d10] overflow-hidden shadow-2xl max-w-full">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[#2b3036] bg-[#171b21]">
                <span className="w-3 h-3 rounded-full bg-[#ef4444]" />
                <span className="w-3 h-3 rounded-full bg-[#f59e0b]" />
                <span className="w-3 h-3 rounded-full bg-[#10b981]" />
                <span className="ml-3 text-xs text-[#8b949e]">s12_comprehensive/code.py</span>
              </div>
              <pre className="m-0 rounded-none border-0 bg-[#0b0d10] text-sm max-w-full">
<code>{`User:
Stop using camelCase in Python files.
I always use snake_case.

Background Review:
✓ extract memory
✓ create skill
✓ persist knowledge

Next turn:
Agent loads matching skill before coding.`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      <section id="demo" className="max-w-6xl mx-auto px-6 py-14 border-b border-[#2b3036]">
        <div className="grid lg:grid-cols-[0.8fr_1.2fr] gap-8 min-w-0">
          <div>
            <p className="text-sm font-semibold text-[#f6c177] mb-2">30 秒 Demo</p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              先看完整闭环，再拆每一层
            </h2>
            <p className="text-[#a7b0bc] leading-relaxed">
              最终章把背景审查、记忆、技能、Curator、压缩、Insights 和错误恢复接到一个可运行 agent 里。
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-4 min-w-0">
            {[
              ["1", "纠正 Agent", "告诉它你的偏好或项目规则"],
              ["2", "自动沉淀", "后台审查写入 memory 和 skill"],
              ["3", "再次命中", "后续对话自动加载相关知识"],
            ].map(([step, title, desc]) => (
              <div key={step} className="p-5 rounded-lg bg-[#171b21] border border-[#2b3036]">
                <div className="w-8 h-8 rounded-md bg-[#193b3a] text-[#6ee7d8] flex items-center justify-center font-bold mb-4">
                  {step}
                </div>
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-[#a7b0bc]">{desc}</p>
              </div>
            ))}
          </div>
        </div>
        <pre className="mt-8 text-sm">
<code>{`python s12_comprehensive/code.py

# 输入：
Stop using camelCase in Python files — I always use snake_case.

# 多轮交互后：
/insights
/curator`}</code>
        </pre>
      </section>

      <section id="chapters" className="max-w-6xl mx-auto px-6 py-14 border-b border-[#2b3036]">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <p className="text-sm font-semibold text-[#6ee7d8] mb-2">学习路径</p>
            <h2 className="text-2xl md:text-3xl font-bold text-white">12 个递进课程</h2>
          </div>
          <p className="text-[#a7b0bc] max-w-xl">
            每章只加一个机制，循环保持不变。读者可以从最小记忆 agent 一路推进到完整自进化系统。
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {CHAPTERS.map((ch) => (
            <a
              key={ch.id}
              href={`/chapters#${ch.slug}`}
              className="p-5 rounded-lg bg-[#171b21] border border-[#2b3036] card-hover group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono text-[#6ee7d8]">s{ch.id}</span>
                <span className="text-[11px] text-[#f6c177]">{ch.layer}</span>
              </div>
              <h3 className="font-semibold text-white group-hover:text-[#6ee7d8] transition-colors mb-2">
                {ch.title}
              </h3>
              <p className="text-sm text-[#a7b0bc]">{ch.motto}</p>
            </a>
          ))}
        </div>
      </section>

      <section id="source-map" className="max-w-6xl mx-auto px-6 py-14 border-b border-[#2b3036]">
        <div className="grid lg:grid-cols-[0.8fr_1.2fr] gap-8 min-w-0">
          <div>
            <p className="text-sm font-semibold text-[#f6c177] mb-2">Hermes 源码地图</p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              从教学代码读回生产源码
            </h2>
            <p className="text-[#a7b0bc] leading-relaxed mb-5">
              每章都对应 Hermes 的真实模块。教程先压缩复杂度，源码地图再把你带回生产实现。
            </p>
            <a
              href="/source-map"
              className="inline-flex items-center px-5 py-3 rounded-md bg-[#193b3a] text-[#6ee7d8] font-semibold text-sm hover:bg-[#214947] transition-colors"
            >
              打开源码地图
            </a>
          </div>
          <div className="overflow-x-auto rounded-lg border border-[#2b3036] max-w-full min-w-0">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="bg-[#171b21] text-[#f0f3f6]">
                <tr>
                  <th className="text-left p-4 font-semibold">模块</th>
                  <th className="text-left p-4 font-semibold">源码入口</th>
                  <th className="text-left p-4 font-semibold">你会看到什么</th>
                </tr>
              </thead>
              <tbody>
                {SOURCE_MAP.map(([name, file, desc]) => (
                  <tr key={file} className="border-t border-[#2b3036] bg-[#111418]">
                    <td className="p-4 text-white">{name}</td>
                    <td className="p-4 font-mono text-[#6ee7d8]">{file}</td>
                    <td className="p-4 text-[#a7b0bc]">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-14">
        <div className="grid lg:grid-cols-[1fr_1fr] gap-6 min-w-0">
          <div className="p-6 rounded-lg bg-[#171b21] border border-[#2b3036] min-w-0">
            <h2 className="text-xl font-bold text-white mb-4">快速开始</h2>
            <pre className="text-sm">
<code>{`git clone https://github.com/hongye/learn-hermes-agent
cd learn-hermes-agent
pip install -r requirements.txt
cp .env.example .env
python s01_agent_loop/code.py`}</code>
            </pre>
          </div>
          <div className="p-6 rounded-lg bg-[#171b21] border border-[#2b3036] min-w-0">
            <h2 className="text-xl font-bold text-white mb-4">适合谁</h2>
            <ul className="space-y-3 text-[#a7b0bc]">
              <li>想读 Hermes Agent 源码，但需要学习路径的工程师</li>
              <li>想做长期运行、会记忆、会学习 agent 的开发者</li>
              <li>想把 prompt chain 升级成 agent harness 的团队</li>
            </ul>
          </div>
        </div>
      </section>
    </main>
  );
}
