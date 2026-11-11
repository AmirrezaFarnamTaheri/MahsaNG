"""Diagnostic inventory for locally missing Android resource references.

This supplements, but never replaces, AAPT2 linking. AndroidX and dependency
resources may contribute definitions not present in app/src/main/res, so the
report is diagnostic rather than a mandatory pass/fail condition.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import xml.etree.ElementTree as ET

RE_KINDS = (
    "string", "array", "color", "drawable", "layout", "mipmap", "style",
    "dimen", "bool", "integer", "plurals", "font", "raw", "menu", "xml",
    "anim", "animator",
)
REF_PATTERN = re.compile(
    r"(?<![\w])@(" + "|".join(RE_KINDS) + r")/([A-Za-z_][A-Za-z0-9_.]*)"
)
EXTERNAL_STYLE_PREFIXES = (
    "Theme.AppCompat", "Theme.MaterialComponents", "TextAppearance.AppCompat",
    "Widget.AppCompat", "Widget.MaterialComponents",
)


def _defined_resources(res: Path) -> set[str]:
    declared: set[str] = set()
    if not res.is_dir():
        return declared
    for folder in res.iterdir():
        if not folder.is_dir():
            continue
        kind = folder.name.split("-", 1)[0]
        if kind == "values":
            for file in folder.glob("*.xml"):
                root = ET.parse(file).getroot()
                for element in root:
                    name = element.get("name")
                    if not name:
                        continue
                    item_type = element.tag
                    if item_type in ("string-array", "integer-array"):
                        item_type = "array"
                    elif item_type == "item":
                        item_type = element.get("type") or ""
                    declared.add(item_type + "/" + name)
        else:
            for file in folder.iterdir():
                if file.is_file():
                    stem = file.stem
                    if stem.endswith(".9"):
                        stem = stem[:-2]
                    declared.add(kind + "/" + stem)
    return declared


def audit_resources(res: Path) -> dict[str, list[str]]:
    definitions = _defined_resources(res)
    missing: dict[str, set[str]] = defaultdict(set)
    for path in res.rglob("*.xml"):
        contents = path.read_text(encoding="utf-8")
        for match in REF_PATTERN.finditer(contents):
            kind, name = match.groups()
            ref = kind + "/" + name
            if kind == "style" and name.startswith(EXTERNAL_STYLE_PREFIXES):
                continue
            if ref not in definitions:
                missing[ref].add(str(path.relative_to(res)))
    return {key: sorted(files) for key, files in sorted(missing.items())}


def main() -> None:
    res = Path(__file__).resolve().parents[1] / "app/src/main/res"
    missing = audit_resources(res)
    print("Locally unresolved app resource references: " + str(len(missing)))
    for reference, paths in missing.items():
        first_files = ", ".join(paths[:3])
        suffix = (" [+" + str(len(paths) - 3) + " more]") if len(paths) > 3 else ""
        print(f"  {reference}: {first_files}{suffix}")


if __name__ == "__main__":
    main()
