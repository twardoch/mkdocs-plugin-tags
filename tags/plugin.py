# --------------------------------------------
# Main part of the plugin
#
# JL Diaz (c) 2019
# MIT License
# --------------------------------------------
from collections import defaultdict
from pathlib import Path

import jinja2
import yaml
from jinja2.ext import Extension
from mkdocs.config.config_options import Type
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File

try:
    from pymdownx.slugs import uslugify_cased_encoded as slugify
except ImportError:
    from markdown.extensions.toc import slugify


def slugify_this(text: str) -> str:
    return slugify(text, "-")  # type: ignore[no-any-return]


class SlugifyExtension(Extension):
    def __init__(self, environment: jinja2.Environment) -> None:
        super().__init__(environment)
        environment.filters["slugify"] = slugify_this


class TagsPlugin(BasePlugin):
    """
    Creates "tags.md" file containing a list of the pages grouped by tags

    It uses the info in the YAML metadata of each page, for the pages which
    provide a "tags" keyword (whose value is a list of strings)
    """

    config_scheme = (
        ("tags_filename", Type(str, default="tags.md")),
        ("tags_folder", Type(str, default="aux")),
        ("tags_template", Type(str)),
    )

    def __init__(self) -> None:
        self.metadata: List[Optional[Dict[str, Any]]] = []
        self.tags_filename: Path = Path("tags.md")
        self.tags_folder: Path = Path("aux")
        self.tags_template: Optional[Path] = None

    def on_nav(
        self, nav: Any, config: Any, files: Any
    ) -> None:  # TODO: Add specific mkdocs types
        # nav.items.insert(1, nav.items.pop(-1))
        pass

    def on_config(self, config: Any) -> None:  # TODO: Add specific mkdocs types
        # Re assign the options
        self.tags_filename = Path(
            self.config.get("tags_filename") or str(self.tags_filename)
        )
        self.tags_folder = Path(
            self.config.get("tags_folder") or str(self.tags_folder)
        )
        # Make sure that the tags folder is absolute, and exists
        if not self.tags_folder.is_absolute():
            self.tags_folder = Path(config["docs_dir"]) / ".." / self.tags_folder
        if not self.tags_folder.exists():
            self.tags_folder.mkdir(parents=True, exist_ok=True)

        tags_template_config = self.config.get("tags_template")
        if tags_template_config:
            self.tags_template = Path(tags_template_config)

    def on_files(
        self, files: Any, config: Any
    ) -> None:  # TODO: Add specific mkdocs types
        # Scan the list of files to extract tags from meta
        for f in files:
            if not f.src_path.endswith(".md"):
                continue
            meta = get_metadata(f.src_path, config["docs_dir"])
            if meta: # Ensure meta is not None before appending
                self.metadata.append(meta)

        # Create new file with tags
        self.generate_tags_file()

        # New file to add to the build
        new_file = File(
            path=str(self.tags_filename),
            src_dir=str(self.tags_folder),
            dest_dir=config["site_dir"],
            use_directory_urls=False,
        )
        files.append(new_file)

    def generate_tags_page(self, data: DefaultDict[str, List[Dict[str, Any]]]) -> str:
        if self.tags_template is None:
            templ_path = Path(__file__).parent / "templates"
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templ_path)),
                extensions=[SlugifyExtension],
            )
            templ = environment.get_template("tags.md.template")
        else:
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    searchpath=str(self.tags_template.parent)
                ),
                extensions=[SlugifyExtension],
            )
            templ = environment.get_template(str(self.tags_template.name))
        stags = sorted(data.items(), key=lambda t: t[0].lower())
        dtags: Dict[str, List[Tuple[str, List[Dict[str, Any]]]]] = {} # More specific type
        for stag in stags:
            try:
                tagletter = stag[0][0].upper()
                if tagletter not in dtags:
                    dtags[tagletter] = [stag]
                else:
                    dtags[tagletter].append(stag)
            except IndexError:  # Handles empty tag strings
                pass
        ldtags = sorted(dtags.items())
        output_text = templ.render(
            tags=ldtags,
        )
        return output_text

    def generate_tags_file(self) -> None:
        if self.metadata:
            # Filter out None values from self.metadata before sorting
            valid_metadata = [m for m in self.metadata if m is not None]
            sorted_meta = sorted(
                valid_metadata, key=lambda e: e.get("year", 5000)
            )
        else:
            sorted_meta = [] # Should be an empty list if metadata is empty

        tag_dict: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in sorted_meta:
            # e is already confirmed to be a dict here by prior filtering and sorting
            if "title" not in e: # Should not happen if get_metadata ensures title
                e["title"] = "Untitled"

            tags = e.get("topic-tags", e.get("topic-auto", e.get("tags", [])))
            if isinstance(tags, list): # Ensure tags is a list
                for tag in tags:
                    if isinstance(tag, str): # Ensure tag is a string
                        tag_dict[tag].append(e)
            elif isinstance(tags, str): # Handle case where tags might be a single string
                tag_dict[tags].append(e)


        t = self.generate_tags_page(tag_dict)

        with (self.tags_folder / self.tags_filename).open("w", encoding="utf-8") as f:
            f.write(t)


from typing import Any, Optional, Union, DefaultDict, List, Dict, Tuple # Added for type hints

# Helper functions


def get_metadata(name: str, path: str) -> Optional[Dict[str, Any]]:
    # Extract metadata from the yaml at the beginning of the file
    def extract_yaml(f: Any) -> str: # TODO: Add specific file type
        result = []
        c = 0
        for line in f:
            if line.strip() == "---":
                c += 1
                continue
            if c == 2:
                break
            if c == 1:
                result.append(line)
        return "".join(result)

    filename = Path(path) / Path(name)
    with filename.open(encoding="utf-8") as f:
        meta: dict = {}
        metadata_str = extract_yaml(f)
        if metadata_str:
            try:
                meta = yaml.load(metadata_str, Loader=yaml.FullLoader)
                if not isinstance(meta, dict): # Ensure meta is a dict
                    # Potentially log a warning here if it's not a dict
                    return None
                meta["filename"] = name
            except yaml.YAMLError:  # Catch specific YAML errors
                # Potentially log an error here
                return None
            return meta
    return None
