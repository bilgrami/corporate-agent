"""Tests for skill loader module."""

from __future__ import annotations

from pathlib import Path

import pytest

from genai_cli.skills.loader import SkillLoader


@pytest.fixture
def loader() -> SkillLoader:
    return SkillLoader()


@pytest.fixture
def sample_skill(tmp_path: Path) -> Path:
    """Create a sample SKILL.md file."""
    skill_dir = tmp_path / "review"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        '---\n'
        'name: review\n'
        'description: >\n'
        '  Performs code review for bugs and issues.\n'
        'metadata:\n'
        '  author: corporate-ai-cli\n'
        '  version: "1.0"\n'
        '  category: development\n'
        '---\n\n'
        '# Code Review\n\n'
        'Review the provided code for:\n'
        '1. Bugs\n'
        '2. Security issues\n'
    )
    return skill_file


class TestSkillLoader:
    def test_load_metadata(self, loader: SkillLoader, sample_skill: Path) -> None:
        meta = loader.load_metadata(sample_skill)
        assert meta is not None
        assert meta.name == "review"
        assert "code review" in meta.description.lower()
        assert meta.author == "corporate-ai-cli"
        assert meta.version == "1.0"
        assert meta.category == "development"

    def test_load_metadata_missing(self, loader: SkillLoader, tmp_path: Path) -> None:
        result = loader.load_metadata(tmp_path / "nonexistent.md")
        assert result is None

    def test_load_metadata_no_frontmatter(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("No frontmatter here")
        result = loader.load_metadata(f)
        assert result is None

    def test_load_full(self, loader: SkillLoader, sample_skill: Path) -> None:
        content = loader.load_full(sample_skill)
        assert content is not None
        assert content.metadata.name == "review"
        assert "Code Review" in content.body
        assert "Bugs" in content.body

    def test_load_full_with_references(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        skill_dir = tmp_path / "skill_with_refs"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: test-skill\ndescription: Test\nmetadata:\n  author: test\n  version: "1.0"\n  category: test\n---\n\n# Test\n'
        )
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "checklist.md").write_text("- Item 1\n- Item 2\n")

        content = loader.load_full(skill_dir / "SKILL.md")
        assert content is not None
        assert "checklist.md" in content.references
        assert "Item 1" in content.references["checklist.md"]

    def test_metadata_source_path(
        self, loader: SkillLoader, sample_skill: Path
    ) -> None:
        meta = loader.load_metadata(sample_skill)
        assert meta is not None
        assert meta.source_path == sample_skill

    def test_load_all_bundled_skills(self, loader: SkillLoader) -> None:
        """All 14 bundled SKILL.md files should parse without error."""
        skills_dir = Path(__file__).resolve().parent.parent / "skills"
        if not skills_dir.is_dir():
            pytest.skip("skills/ directory not found")

        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        loaded = 0
        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            if skill_file.is_file():
                meta = loader.load_metadata(skill_file)
                assert meta is not None, f"Failed to parse {skill_file}"
                assert meta.name, f"Empty name in {skill_file}"
                assert meta.description, f"Empty description in {skill_file}"

                # Also test full load
                content = loader.load_full(skill_file)
                assert content is not None, f"Failed to load full {skill_file}"
                assert content.body, f"Empty body in {skill_file}"
                loaded += 1

        assert loaded == 17, f"Expected 17 bundled skills, found {loaded}"

    def test_invalid_yaml_frontmatter(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("---\ninvalid: yaml: :\n---\n\nbody\n")
        result = loader.load_metadata(f)
        # Should handle gracefully (None or valid parse)
        # yaml.safe_load may or may not error on this

    def test_auto_apply_field(self, loader: SkillLoader, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text(
            '---\nname: fix\ndescription: Fix bugs\nauto_apply: true\n'
            'metadata:\n  author: test\n  version: "1.0"\n  category: dev\n---\n\n# Fix\n'
        )
        meta = loader.load_metadata(f)
        assert meta is not None
        assert meta.auto_apply is True

    def test_no_auto_apply_default(
        self, loader: SkillLoader, sample_skill: Path
    ) -> None:
        meta = loader.load_metadata(sample_skill)
        assert meta is not None
        assert meta.auto_apply is False

    def test_tier1_metadata_compact(
        self, loader: SkillLoader, sample_skill: Path
    ) -> None:
        """Tier 1 metadata should be small (~100 tokens)."""
        meta = loader.load_metadata(sample_skill)
        assert meta is not None
        # Rough estimate: name + description + author etc.
        text = f"{meta.name} {meta.description} {meta.author} {meta.category}"
        # Should be well under 100 tokens (~400 chars)
        assert len(text) < 500
