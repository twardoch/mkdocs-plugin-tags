# SPDX-FileCopyrightText: 2024 Jules AI Agent
# SPDX-License-Identifier: MIT

from pathlib import Path
from tempfile import TemporaryDirectory
import yaml

import pytest

from tags.plugin import TagsPlugin, get_metadata


# Fixtures
@pytest.fixture
def mkdocs_config_base():
    """Minimal mkdocs.yml configuration for testing."""
    return {
        "site_name": "Test Site",
        "docs_dir": "docs", # Relative to a temporary test directory
        "plugins": ["tags"],
    }


@pytest.fixture
def plugin_config_base():
    """Minimal tags plugin configuration for testing."""
    return {
        "tags_folder": "tag_pages", # Relative to a temporary test directory
        "tags_filename": "all-tags.md",
    }


# Tests for get_metadata
def test_get_metadata_valid_yaml_header(tmp_path: Path):
    """Test get_metadata with a valid YAML header."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_content = """---
title: Test Page
tags:
  - tag1
  - tag2
year: 2024
---
# Content
"""
    md_file = docs_dir / "test_page.md"
    md_file.write_text(md_content, encoding="utf-8")

    metadata = get_metadata(name="test_page.md", path=str(docs_dir))

    assert metadata is not None
    assert metadata["title"] == "Test Page"
    assert "tag1" in metadata["tags"]
    assert "tag2" in metadata["tags"]
    assert metadata["year"] == 2024
    assert metadata["filename"] == "test_page.md"


def test_get_metadata_no_yaml_header(tmp_path: Path):
    """Test get_metadata with no YAML header."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_content = "# Content without YAML"
    md_file = docs_dir / "no_yaml_page.md"
    md_file.write_text(md_content, encoding="utf-8")

    metadata = get_metadata(name="no_yaml_page.md", path=str(docs_dir))
    assert metadata is None


def test_get_metadata_invalid_yaml_header(tmp_path: Path):
    """Test get_metadata with invalid YAML (e.g., a list instead of a dict)."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_content = """---
- item1
- item2
---
# Content
"""
    md_file = docs_dir / "invalid_yaml_page.md"
    md_file.write_text(md_content, encoding="utf-8")

    metadata = get_metadata(name="invalid_yaml_page.md", path=str(docs_dir))
    assert metadata is None # Expecting None as the loaded YAML is not a dict


def test_get_metadata_empty_file(tmp_path: Path):
    """Test get_metadata with an empty file."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_file = docs_dir / "empty_page.md"
    md_file.touch()

    metadata = get_metadata(name="empty_page.md", path=str(docs_dir))
    assert metadata is None


def test_get_metadata_file_not_found(tmp_path: Path):
    """Test get_metadata with a non-existent file."""
    docs_dir = tmp_path / "docs"
    # docs_dir.mkdir() # Don't create for this test, or create then try non-existent file

    with pytest.raises(FileNotFoundError):
        get_metadata(name="non_existent_page.md", path=str(docs_dir))


# Tests for TagsPlugin
class TestTagsPlugin:
    def test_plugin_initialization_default_config(self):
        """Test TagsPlugin initialization with default config."""
        plugin = TagsPlugin()
        assert plugin.tags_filename == Path("tags.md")
        assert plugin.tags_folder == Path("aux")
        assert plugin.tags_template is None

    def test_plugin_on_config_custom_values(self, mkdocs_config_base):
        """Test TagsPlugin.on_config with custom values."""
        plugin = TagsPlugin()
        plugin.config = { # Simulate loaded plugin config
            "tags_filename": "my-tags.md",
            "tags_folder": "generated/tags",
            "tags_template": "custom_tags_template.md",
        }

        # Create a temporary docs_dir for the test
        with TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "docs"
            docs_path.mkdir(parents=True, exist_ok=True)

            mkdocs_config_full = {**mkdocs_config_base, "docs_dir": str(docs_path)}
            plugin.on_config(mkdocs_config_full)

            assert plugin.tags_filename == Path("my-tags.md")
            # tags_folder should be relative to docs_dir/.. if not absolute
            expected_tags_folder = docs_path.parent / "generated/tags"
            assert plugin.tags_folder == expected_tags_folder
            assert expected_tags_folder.exists() # Check if folder was created
            assert plugin.tags_template == Path("custom_tags_template.md")

    def test_plugin_on_config_absolute_tags_folder(self, mkdocs_config_base, tmp_path: Path):
        """Test TagsPlugin.on_config with an absolute tags_folder path."""
        plugin = TagsPlugin()
        absolute_folder = tmp_path / "custom_absolute_tags"

        plugin.config = {
            "tags_folder": str(absolute_folder),
        }

        with TemporaryDirectory() as tmp_docs_dir_root:
            docs_path = Path(tmp_docs_dir_root) / "docs"
            docs_path.mkdir(parents=True, exist_ok=True)

            mkdocs_config_full = {**mkdocs_config_base, "docs_dir": str(docs_path)}
            plugin.on_config(mkdocs_config_full)

            assert plugin.tags_folder == absolute_folder
            assert absolute_folder.exists()


    def test_generate_tags_page_empty_data(self):
        """Test generate_tags_page with no tags data."""
        plugin = TagsPlugin()
        # Ensure default template path is valid for this test
        # This might require adjusting if the test running directory changes
        # For now, assuming it can find templates relative to plugin.py
        output = plugin.generate_tags_page(defaultdict(list))
        assert "# Contents grouped by tag" in output
        # Check that no tags are listed (specific content depends on template)
        assert "## <span class=" not in output # A bit fragile, depends on template

    def test_generate_tags_page_with_data(self, tmp_path: Path):
        """Test generate_tags_page with sample tag data."""
        plugin = TagsPlugin()

        # Sample metadata similar to what would be collected
        page1_meta = {"title": "Page One", "filename": "page1.md", "tags": ["cat", "dog"]}
        page2_meta = {"title": "Page Two", "filename": "page2.md", "tags": ["cat", "fish"]}

        tag_dict = defaultdict(list)
        tag_dict["cat"].append(page1_meta)
        tag_dict["cat"].append(page2_meta)
        tag_dict["dog"].append(page1_meta)
        tag_dict["fish"].append(page2_meta)

        output = plugin.generate_tags_page(tag_dict)

        assert "# Contents grouped by tag" in output
        assert "## <span class=\"tag\">cat</span>" in output
        assert "* [Page One](page1.md)" in output
        assert "* [Page Two](page2.md)" in output
        assert "## <span class=\"tag\">dog</span>" in output
        assert "## <span class=\"tag\">fish</span>" in output

    def test_generate_tags_file_creates_file(self, tmp_path: Path):
        """Test that generate_tags_file actually creates the tags file."""
        plugin = TagsPlugin()
        plugin.tags_folder = tmp_path / "my_tags_output"
        plugin.tags_filename = Path("final-tags.md")

        # Minimal on_config setup
        plugin.tags_folder.mkdir(parents=True, exist_ok=True)

        # Sample metadata
        page_meta = {"title": "Test", "filename": "test.md", "tags": ["sample"]}
        plugin.metadata = [page_meta] # type: ignore

        plugin.generate_tags_file()

        expected_file = plugin.tags_folder / plugin.tags_filename
        assert expected_file.exists()
        content = expected_file.read_text(encoding="utf-8")
        assert "## <span class=\"tag\">sample</span>" in content
        assert "* [Test](test.md)" in content

    # TODO: More tests for on_files, especially interaction with mkdocs File objects
    # TODO: Test with custom templates
    # TODO: Test slugify behavior if special characters are in tags
    # TODO: Test different configurations of tags_folder (relative, absolute)

# Example of how to run with hatch: hatch run test
# Example of how to run for coverage: hatch run test:cov
# Open htmlcov/index.html to see coverage report
