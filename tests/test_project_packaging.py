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


def test_public_github_links_point_to_current_repository():
    public_files = [
        "README.md",
        "README.en.md",
        "web/src/app/page.tsx",
        "web/src/app/layout.tsx",
    ]
    combined = "\n".join(read_text(path) for path in public_files)

    assert "github.com/Ericcc-Ma/learn-hermes-agent" in combined
    assert "github.com/hongye/learn-hermes-agent" not in combined
    assert "hongye/learn-hermes-agent" not in combined


def test_web_demo_chapters_and_source_map_pages_exist():
    demo = read_text("web/src/app/demo/page.tsx")
    chapters = read_text("web/src/app/chapters/page.tsx")
    source_map = read_text("web/src/app/source-map/page.tsx")

    assert "真实演示脚本" in demo
    assert "第一轮" in demo
    assert "后台审查" in demo
    assert "24 个递进课程" in chapters
    assert "s01_agent_loop" in chapters
    assert "s24_system_prompt" in chapters
    assert "Hermes 源码地图" in source_map
    assert "agent/background_review.py" in source_map


def test_mobile_navigation_does_not_split_link_text():
    layout = read_text("web/src/app/layout.tsx")

    assert "whitespace-nowrap" in layout
    assert "flex-wrap" in layout


def test_web_copy_tracks_24_chapter_curriculum():
    homepage = read_text("web/src/app/page.tsx")
    demo = read_text("web/src/app/demo/page.tsx")
    chapters = read_text("web/src/app/chapters/page.tsx")
    source_map = read_text("web/src/app/source-map/page.tsx")
    layout = read_text("web/src/app/layout.tsx")

    assert "24 个递进课程" in homepage
    assert "s12_comprehensive/comprehensive.py" in homepage
    assert "s01_agent_loop/agent_loop.py" in homepage
    assert "s12_comprehensive/code.py" not in homepage
    assert "s01_agent_loop/code.py" not in homepage
    assert "24 个递进课程" in chapters
    assert "s24_system_prompt" in chapters
    assert "system_prompt.py" in chapters
    assert "24 个章节" in source_map
    assert "s24" in source_map
    assert "s12_comprehensive/comprehensive.py" in demo
    assert "s12_comprehensive/code.py" not in demo
    assert "24 个递进课程" in layout


def test_docs_track_24_chapter_curriculum():
    source_map = read_text("docs/hermes-source-map.md")
    faq = read_text("docs/faq.md")

    assert "24 个教学章节" in source_map
    assert "s24_system_prompt" in source_map
    assert "读者学完 24 章" in source_map
    assert "24 个能独立运行的小章节" in faq
    assert "s01_agent_loop/agent_loop.py" in faq
    assert "`s13` 到 `s18`" in faq
    assert "`s19` 到 `s24`" in faq
    assert "s01_agent_loop/code.py" not in faq


def test_markdown_links_to_local_readmes_exist():
    for readme_path in PROJECT_ROOT.glob("s*/README.md"):
        readme = readme_path.read_text(encoding="utf-8")
        if "README.en.md" in readme:
            assert (readme_path.parent / "README.en.md").is_file(), f"Broken English README link in {readme_path}"


def test_new_chapters_have_english_readmes():
    for chapter_num in range(13, 25):
        chapter_dir = next(PROJECT_ROOT.glob(f"s{chapter_num:02d}_*"))
        english_readme = chapter_dir / "README.en.md"
        chinese_readme = (chapter_dir / "README.md").read_text(encoding="utf-8")

        assert english_readme.is_file(), f"Missing English README for {chapter_dir.name}"
        assert "[English](README.en.md)" in chinese_readme
        text = english_readme.read_text(encoding="utf-8")
        assert "[中文](README.md)" in text
        assert "Try It" in text
        assert len(text) > 1200
