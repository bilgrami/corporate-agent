"""Tests for prompt loader module."""

from __future__ import annotations

from pathlib import Path

import pytest

from genai_cli.prompts.loader import PromptLoader


@pytest.fixture
def loader() -> PromptLoader:
    return PromptLoader()


@pytest.fixture
def sample_prompt(tmp_path: Path) -> Path:
    """Create a sample PROMPT.md file."""
    prompt_dir = tmp_path / "default"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "PROMPT.md"
    prompt_file.write_text(
        '---\n'
        'name: default\n'
        'description: >\n'
        '  Full-featured assistant with planning rules.\n'
        'metadata:\n'
        '  author: corporate-ai-cli\n'
        '  version: "1.0"\n'
        '  category: general\n'
        '---\n\n'
        'You are an AI coding assistant accessed via a CLI tool.\n\n'
        '## Rules\n'
        '- Never mention {agent_name} in code\n'
    )
    return prompt_file


class TestPromptLoader:
    def test_load_metadata(self, loader: PromptLoader, sample_prompt: Path) -> None:
        meta = loader.load_metadata(sample_prompt)
        assert meta is not None
        assert meta.name == "default"
        assert "planning rules" in meta.description.lower()
        assert meta.author == "corporate-ai-cli"
        assert meta.version == "1.0"
        assert meta.category == "general"

    def test_load_metadata_missing(self, loader: PromptLoader, tmp_path: Path) -> None:
        result = loader.load_metadata(tmp_path / "nonexistent.md")
        assert result is None

    def test_load_metadata_no_frontmatter(
        self, loader: PromptLoader, tmp_path: Path
    ) -> None:
        f = tmp_path / "PROMPT.md"
        f.write_text("No frontmatter here")
        result = loader.load_metadata(f)
        assert result is None

    def test_load_full(self, loader: PromptLoader, sample_prompt: Path) -> None:
        content = loader.load_full(sample_prompt)
        assert content is not None
        assert content.metadata.name == "default"
        assert "AI coding assistant" in content.body
        assert "{agent_name}" in content.body

    def test_metadata_source_path(
        self, loader: PromptLoader, sample_prompt: Path
    ) -> None:
        meta = loader.load_metadata(sample_prompt)
        assert meta is not None
        assert meta.source_path == sample_prompt

    def test_agent_name_substitution_in_body(
        self, loader: PromptLoader, sample_prompt: Path
    ) -> None:
        """Body should contain {agent_name} placeholder (substitution is done by registry)."""
        content = loader.load_full(sample_prompt)
        assert content is not None
        assert "{agent_name}" in content.body

    def test_load_all_bundled_prompts(self, loader: PromptLoader) -> None:
        """All 10 bundled PROMPT.md files should parse without error."""
        prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        if not prompts_dir.is_dir():
            pytest.skip("prompts/ directory not found")

        prompt_dirs = [d for d in prompts_dir.iterdir() if d.is_dir()]
        loaded = 0
        for prompt_dir in prompt_dirs:
            prompt_file = prompt_dir / "PROMPT.md"
            if prompt_file.is_file():
                meta = loader.load_metadata(prompt_file)
                assert meta is not None, f"Failed to parse {prompt_file}"
                assert meta.name, f"Empty name in {prompt_file}"
                assert meta.description, f"Empty description in {prompt_file}"

                # Also test full load
                content = loader.load_full(prompt_file)
                assert content is not None, f"Failed to load full {prompt_file}"
                assert content.body, f"Empty body in {prompt_file}"
                loaded += 1

        assert loaded == 10, f"Expected 10 bundled prompts, found {loaded}"

    def test_invalid_yaml_frontmatter(
        self, loader: PromptLoader, tmp_path: Path
    ) -> None:
        f = tmp_path / "PROMPT.md"
        f.write_text("---\ninvalid: yaml: :\n---\n\nbody\n")
        result = loader.load_metadata(f)
        # Should handle gracefully (None or valid parse)

    def test_name_fallback_to_dirname(
        self, loader: PromptLoader, tmp_path: Path
    ) -> None:
        """When name is missing from frontmatter, fall back to parent dir name."""
        prompt_dir = tmp_path / "my-prompt"
        prompt_dir.mkdir()
        f = prompt_dir / "PROMPT.md"
        f.write_text(
            '---\ndescription: Test prompt\nmetadata:\n'
            '  author: test\n  version: "1.0"\n  category: test\n---\n\n# Test\n'
        )
        meta = loader.load_metadata(f)
        assert meta is not None
        assert meta.name == "my-prompt"

    def test_tier1_metadata_compact(
        self, loader: PromptLoader, sample_prompt: Path
    ) -> None:
        """Tier 1 metadata should be small (~100 tokens)."""
        meta = loader.load_metadata(sample_prompt)
        assert meta is not None
        text = f"{meta.name} {meta.description} {meta.author} {meta.category}"
        assert len(text) < 500
