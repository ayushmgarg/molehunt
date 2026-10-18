"""OOXML explorer logic (Case 4): package tree, metadata, rsids, tracked changes.

A .docx is a ZIP of XML parts. We list every part with its size, read
docProps/core.xml (creator, lastModifiedBy, dates, revision), docProps/app.xml
(Template, TotalTime, Application), docProps/custom.xml properties, the rsid
list in word/settings.xml (rsidRoot first), a count of rsid values on runs and
paragraphs in word/document.xml, and tracked changes (w:ins / w:del with
author and date). Parsing never resolves entities or touches the network.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


@dataclass(frozen=True)
class OoxmlReport:
    """Everything the explorer panel displays for one DOCX package."""

    parts: tuple[tuple[str, int], ...]
    core: dict[str, str]
    app: dict[str, str]
    custom: dict[str, str]
    rsid_root: str | None
    settings_rsids: tuple[str, ...]
    content_rsids: tuple[tuple[str, int], ...]
    tracked_changes: tuple[tuple[str, str, str, str], ...]


def _children(root: etree._Element) -> dict[str, str]:
    return {etree.QName(child).localname: (child.text or "").strip() for child in root}


def explore_docx(path: str | Path) -> OoxmlReport:
    """Read the package parts and forensic metadata of a DOCX file."""
    try:
        with ZipFile(path) as package:
            names = package.namelist()
            parts = tuple((info.filename, info.file_size) for info in package.infolist())

            def xml(name: str) -> etree._Element | None:
                return etree.fromstring(package.read(name), _PARSER) if name in names else None

            core, app, custom = xml("docProps/core.xml"), xml("docProps/app.xml"), xml(
                "docProps/custom.xml")
            settings, document = xml("word/settings.xml"), xml("word/document.xml")
    except (BadZipFile, KeyError, etree.XMLSyntaxError) as error:
        raise ValueError(f"not a readable DOCX package: {error}") from error
    custom_props = {}
    if custom is not None:
        for prop in custom:
            custom_props[prop.get("name", "?")] = "".join(prop.itertext()).strip()
    rsid_root, settings_rsids = None, ()
    if settings is not None:
        rsid_root = settings.get(f"{{{W}}}rsidRoot")
        settings_rsids = tuple(node.get(f"{{{W}}}val") for node in settings.iter(f"{{{W}}}rsid"))
    usage: Counter = Counter()
    changes = []
    if document is not None:
        for node in document.iter():
            for attribute in ("rsidR", "rsidRPr", "rsidP"):
                value = node.get(f"{{{W}}}{attribute}")
                if value:
                    usage[value] += 1
            name = etree.QName(node).localname if isinstance(node.tag, str) else ""
            if name in {"ins", "del"}:
                text = "".join(node.itertext()).strip()
                changes.append((name, node.get(f"{{{W}}}author", ""),
                                node.get(f"{{{W}}}date", ""), text))
    return OoxmlReport(
        parts, _children(core) if core is not None else {},
        _children(app) if app is not None else {}, custom_props, rsid_root,
        settings_rsids, tuple(usage.most_common()), tuple(changes),
    )


def pretty_part(path: str | Path, part: str, limit: int = 20_000) -> str:
    """Indented XML of one package part (truncated for display)."""
    with ZipFile(path) as package:
        root = etree.fromstring(package.read(part), _PARSER)
    text = etree.tostring(root, pretty_print=True, encoding="unicode")
    return text if len(text) <= limit else text[:limit] + "\n... (truncated)"
