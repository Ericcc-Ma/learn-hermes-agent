const DEMO_STEPS = [
  {
    title: "第一轮：用户纠正 Agent",
    command: "Stop using camelCase in Python files — I always use snake_case.",
    result: "Agent 完成当前任务，同时把这次纠正保留在对话快照里。",
  },
  {
    title: "后台审查：提取记忆和技能",
    command: "Background Review -> extract memory -> create skill -> persist",
    result: "系统把“Python 使用 snake_case”写入长期记忆，并创建可复用技能。",
  },
  {
    title: "第二轮：自动命中",
    command: "Create a Python helper for parsing config keys.",
    result: "Agent 在回答前加载相关记忆/技能，直接按 snake_case 写代码。",
  },
];

export default function DemoPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      <div className="mb-10">
        <p className="text-sm font-semibold text-[#6ee7d8] mb-2">30 秒 Demo</p>
        <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-5">
          真实演示脚本：Agent 如何从一次纠正中学习
        </h1>
        <p className="text-lg text-[#a7b0bc] max-w-3xl leading-relaxed">
          这个 demo 对应 `s12_comprehensive/code.py` 的完整闭环：用户纠正、后台审查、记忆/技能持久化、下一轮自动加载。
        </p>
      </div>

      <section className="grid lg:grid-cols-[0.85fr_1.15fr] gap-6 items-start">
        <div className="space-y-4">
          {DEMO_STEPS.map((step, index) => (
            <div key={step.title} className="p-5 rounded-lg bg-[#171b21] border border-[#2b3036]">
              <div className="text-xs font-mono text-[#f6c177] mb-2">STEP {index + 1}</div>
              <h2 className="text-xl font-bold text-white mb-3">{step.title}</h2>
              <p className="text-sm text-[#a7b0bc] mb-4">{step.result}</p>
              <pre className="text-sm">
<code>{step.command}</code>
              </pre>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-[#2b3036] bg-[#0b0d10] overflow-hidden shadow-2xl min-w-0">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#2b3036] bg-[#171b21]">
            <span className="w-3 h-3 rounded-full bg-[#ef4444]" />
            <span className="w-3 h-3 rounded-full bg-[#f59e0b]" />
            <span className="w-3 h-3 rounded-full bg-[#10b981]" />
            <span className="ml-3 text-xs text-[#8b949e]">terminal demo</span>
          </div>
          <pre className="m-0 rounded-none border-0 bg-[#0b0d10] text-sm">
<code>{`$ python s12_comprehensive/code.py

You: Stop using camelCase in Python files — I always use snake_case.

Agent:
Understood. I will use snake_case for Python identifiers in this project.

[Background Review]
✓ memory: user prefers snake_case in Python
✓ skill: python-style-preferences created
✓ persisted to .memory/ and skills/

You: Create a Python helper for parsing config keys.

Agent loads:
- memory: Python identifiers should use snake_case
- skill: python-style-preferences

Agent writes:
def parse_config_key(raw_key: str) -> str:
    return raw_key.strip().lower().replace("-", "_")

You: /insights

Insights:
memory_hits: 1
skills_created: 1
skill_loads: 1`}</code>
          </pre>
        </div>
      </section>

      <section className="mt-10 p-6 rounded-lg bg-[#171b21] border border-[#2b3036]">
        <h2 className="text-xl font-bold text-white mb-4">在本地运行同款 Demo</h2>
        <pre className="text-sm">
<code>{`cd D:\\study\\learn-hermes-agent
python s12_comprehensive/code.py

# 输入：
Stop using camelCase in Python files — I always use snake_case.

# 多轮交互后：
/insights
/curator`}</code>
        </pre>
      </section>
    </main>
  );
}
