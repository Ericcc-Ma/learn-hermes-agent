const SOURCE_ROWS = [
  ["s01", "最小循环 + 记忆", "run_agent.py", "AIAgent 主类和主循环"],
  ["s02-s03", "背景审查", "agent/background_review.py", "记忆审查、技能审查、禁止捕获规则"],
  ["s04", "记忆系统", "agent/memory_manager.py", "记忆 provider 编排、FTS、上下文注入"],
  ["s05-s06", "技能管理", "tools/skill_usage.py", "技能使用遥测、生命周期、来源管理"],
  ["s07-s08", "Curator", "agent/curator.py", "stale/archive、LLM 合并、报告生成"],
  ["s09", "上下文管理", "agent/context_compressor.py", "压缩模板、剩余工作、辅助模型"],
  ["s10", "Insights", "agent/insights.py", "token、成本、工具模式、平台维度"],
  ["s11", "错误恢复", "agent/conversation_loop.py", "重试、降级、上下文溢出恢复"],
  ["s12", "完整集成", "toolsets.py", "工具注册、工具集分发、生产入口"],
];

export default function SourceMapPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      <div className="mb-10">
        <p className="text-sm font-semibold text-[#f6c177] mb-2">Hermes 源码地图</p>
        <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-5">
          教学章节如何对应生产源码
        </h1>
        <p className="text-lg text-[#a7b0bc] max-w-3xl leading-relaxed">
          这张表把 `learn-hermes-agent` 的 12 个章节，对齐到 `NousResearch/hermes-agent` 的核心源码入口。
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-[#2b3036]">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-[#171b21] text-[#f0f3f6]">
            <tr>
              <th className="text-left p-4 font-semibold">章节</th>
              <th className="text-left p-4 font-semibold">教学目标</th>
              <th className="text-left p-4 font-semibold">Hermes 源码入口</th>
              <th className="text-left p-4 font-semibold">重点</th>
            </tr>
          </thead>
          <tbody>
            {SOURCE_ROWS.map(([lesson, goal, file, focus]) => (
              <tr key={`${lesson}-${file}`} className="border-t border-[#2b3036] bg-[#111418]">
                <td className="p-4 text-[#6ee7d8] font-mono">{lesson}</td>
                <td className="p-4 text-white">{goal}</td>
                <td className="p-4 text-[#f6c177] font-mono">{file}</td>
                <td className="p-4 text-[#a7b0bc]">{focus}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="mt-8 p-6 rounded-lg bg-[#171b21] border border-[#2b3036]">
        <h2 className="text-xl font-bold text-white mb-3">推荐读法</h2>
        <p className="text-[#a7b0bc] leading-relaxed">
          先跑 `s12_comprehensive/code.py` 看完整效果，再回到 `run_agent.py` 看集成点，随后读
          `agent/background_review.py`、`agent/curator.py`、`agent/memory_manager.py`。
        </p>
      </section>
    </main>
  );
}
