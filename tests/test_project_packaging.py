"""
Packaging checks for the public tutorial surface.

These tests guard the pieces that make the repository trustworthy and easy to
share: license, documentation entry points, and the web learning hub.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_license_file_matches_readme_badge():
    assert (PROJECT_ROOT / "LICENSE").is_file()


def test_readme_links_source_map_and_faq():
    readme = read_text("README.md")

    assert "Hermes 源码地图" in readme
    assert "docs/hermes-source-map.md" in readme
    assert "docs/faq.md" in readme


def test_web_readme_is_project_specific():
    web_readme = read_text("web/README.md")

    assert "Learn Hermes Agent" in web_readme
    assert "create-next-app" not in web_readme


def test_homepage_is_chinese_learning_hub():
    page = read_text("web/src/app/page.tsx")

    assert "从零复刻 Hermes Agent 的自学习系统" in page
    assert "Hermes 源码地图" in page
    assert "30 秒 Demo" in page


def test_homepage_uses_local_learning_routes():
    page = read_text("web/src/app/page.tsx")

    assert 'href="/demo"' in page
    assert 'href="/chapters"' in page
    assert 'href="/source-map"' in page
    assert "github.com/hongye/learn-hermes-agent/tree/main" not in page
    assert "github.com/hongye/learn-hermes-agent/blob/main/docs/hermes-source-map.md" not in page


def test_web_demo_chapters_and_source_map_pages_exist():
    demo = read_text("web/src/app/demo/page.tsx")
    chapters = read_text("web/src/app/chapters/page.tsx")
    source_map = read_text("web/src/app/source-map/page.tsx")

    assert "真实演示脚本" in demo
    assert "第一轮" in demo
    assert "后台审查" in demo
    assert "12 个递进课程" in chapters
    assert "s01_agent_loop" in chapters
    assert "Hermes 源码地图" in source_map
    assert "agent/background_review.py" in source_map


def test_mobile_navigation_does_not_split_link_text():
    layout = read_text("web/src/app/layout.tsx")

    assert "whitespace-nowrap" in layout
    assert "flex-wrap" in layout
