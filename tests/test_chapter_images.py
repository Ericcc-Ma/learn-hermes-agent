"""Checks for chapter architecture diagrams."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

NEW_CHAPTER_IMAGE_FILES = {
    "s13_cron_scheduler": "cron-scheduler.svg",
    "s14_gateway": "gateway-routing.svg",
    "s15_profiles": "profile-inheritance.svg",
    "s16_agent_teams": "agent-teams.svg",
    "s17_mcp_plugin": "mcp-plugin.svg",
    "s18_full_hermes": "full-hermes.svg",
    "s19_permission": "permission-pipeline.svg",
    "s20_hooks": "hook-system.svg",
    "s21_worktree": "worktree-isolation.svg",
    "s22_planning": "planning-dag.svg",
    "s23_autonomous": "autonomous-agents.svg",
    "s24_system_prompt": "system-prompt-assembly.svg",
}


def test_new_chapters_have_svg_diagrams():
    for chapter, image_name in NEW_CHAPTER_IMAGE_FILES.items():
        image_path = PROJECT_ROOT / chapter / "images" / image_name
        assert image_path.is_file(), f"Missing image: {image_path}"

        svg = image_path.read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<svg"), f"{image_path} is not an SVG"
        assert "</svg>" in svg, f"{image_path} is incomplete"
        assert len(svg) > 1000, f"{image_path} is too small to be a useful diagram"


def test_new_chapter_readmes_reference_diagrams():
    for chapter, image_name in NEW_CHAPTER_IMAGE_FILES.items():
        readme_path = PROJECT_ROOT / chapter / "README.md"
        readme = readme_path.read_text(encoding="utf-8")
        assert f"images/{image_name}" in readme, f"{readme_path} does not reference {image_name}"
