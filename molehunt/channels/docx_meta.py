"""Fingerprint DOCX package metadata with keyed revision IDs and a custom tag."""

from __future__ import annotations

import re
from collections.abc import Iterable
from copy import deepcopy
from io import BytesIO
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from lxml import etree

from molehunt.core.keys import digest

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
CUSTOM_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
CUSTOM_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CUSTOM_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"
PROPERTY_NAME = "MoleHuntTag"
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


def derive_rsid(key: bytes, employee_id: str) -> str:
    """Derive an eight-hex-digit OOXML revision identifier for an employee."""
    if not employee_id:
        raise ValueError("employee id must not be empty")
    return digest(key, "docx-rsid", employee_id)[:4].hex().upper()


def _run_rsid(key: bytes, employee_id: str, index: int) -> str:
    return digest(key, "docx-run-rsid", employee_id, index.to_bytes(8, "big"))[:4].hex().upper()


def _split_runs(document: etree._Element, key: bytes, employee_id: str) -> None:
    """Split eligible text runs at keyed word boundaries without changing text."""
    for paragraph_index, paragraph in enumerate(document.findall(f".//{{{W}}}p")):
        for run_index, run in enumerate(list(paragraph.findall(f"{{{W}}}r"))):
            text_nodes = run.findall(f"{{{W}}}t")
            if len(text_nodes) != 1 or any(
                etree.QName(child).localname not in {"rPr", "t"} for child in run
            ):
                continue
            text = text_nodes[0].text or ""
            boundaries = [
                match.end()
                for match in re.finditer(r"\s+", text)
                if match.start() > 0 and match.end() < len(text)
            ]
            if not boundaries:
                continue
            draw = digest(
                key,
                "docx-run-split",
                employee_id,
                paragraph_index.to_bytes(4, "big"),
                run_index.to_bytes(4, "big"),
            )
            split_at = boundaries[int.from_bytes(draw[:4], "big") % len(boundaries)]
            second = deepcopy(run)
            first_text = text_nodes[0]
            second_text = second.find(f"{{{W}}}t")
            first_text.text = text[:split_at]
            second_text.text = text[split_at:]
            first_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            run.addnext(second)


def _xml(data: bytes, name: str) -> etree._Element:
    try:
        return etree.fromstring(data, parser=_PARSER)
    except etree.XMLSyntaxError as error:
        raise ValueError(f"invalid DOCX XML part: {name}") from error


def _serialize(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _stamp_settings(settings: etree._Element, root_id: str, rsids: Iterable[str]) -> None:
    settings.set(f"{{{W}}}rsidRoot", root_id)
    settings.set(f"{{{W}}}rsidRDefault", root_id)
    collection = settings.find(f"{{{W}}}rsids")
    if collection is None:
        collection = etree.SubElement(settings, f"{{{W}}}rsids")
    existing = {
        node.get(f"{{{W}}}val")
        for node in collection.findall(f"{{{W}}}rsid")
    }
    for value in sorted(set(rsids) | {root_id}):
        if value not in existing:
            etree.SubElement(collection, f"{{{W}}}rsid").set(f"{{{W}}}val", value)


def _stamp_document(document: etree._Element, key: bytes, employee_id: str) -> list[str]:
    values: list[str] = []
    for paragraph_index, paragraph in enumerate(document.findall(f".//{{{W}}}p")):
        paragraph_id = _run_rsid(key, employee_id, paragraph_index)
        paragraph.set(f"{{{W}}}rsidP", paragraph_id)
        paragraph.set(f"{{{W}}}rsidR", derive_rsid(key, employee_id))
        values.append(paragraph_id)
    for run_index, run in enumerate(document.findall(f".//{{{W}}}r")):
        run_id = _run_rsid(key, employee_id, run_index + 0x100000)
        run.set(f"{{{W}}}rsidR", run_id)
        run.set(f"{{{W}}}rsidRPr", run_id)
        values.append(run_id)
    return values


def _custom_properties(data: bytes | None, value: str) -> bytes:
    if data is None:
        root = etree.Element(f"{{{CP}}}Properties", nsmap={"cp": CP, "vt": VT})
    else:
        root = _xml(data, "docProps/custom.xml")
    properties = root.findall(f"{{{CP}}}property")
    matches = [prop for prop in properties if prop.get("name") == PROPERTY_NAME]
    if len(matches) > 1:
        for duplicate in matches[1:]:
            root.remove(duplicate)
    if matches:
        prop = matches[0]
        for child in list(prop):
            prop.remove(child)
    else:
        next_pid = max((int(prop.get("pid", "1")) for prop in properties), default=1) + 1
        prop = etree.SubElement(root, f"{{{CP}}}property")
        prop.set("fmtid", CUSTOM_FMTID)
        prop.set("pid", str(next_pid))
        prop.set("name", PROPERTY_NAME)
    etree.SubElement(prop, f"{{{VT}}}lpwstr").text = value
    return _serialize(root)


def _ensure_relationship(data: bytes) -> bytes:
    root = _xml(data, "_rels/.rels")
    if any(rel.get("Type") == CUSTOM_REL_TYPE for rel in root.findall(f"{{{REL}}}Relationship")):
        return data
    used_ids = {rel.get("Id") for rel in root.findall(f"{{{REL}}}Relationship")}
    index = 1
    while f"rId{index}" in used_ids:
        index += 1
    relation = etree.SubElement(root, f"{{{REL}}}Relationship")
    relation.set("Id", f"rId{index}")
    relation.set("Type", CUSTOM_REL_TYPE)
    relation.set("Target", "docProps/custom.xml")
    return _serialize(root)


def _ensure_content_type(data: bytes) -> bytes:
    root = _xml(data, "[Content_Types].xml")
    exists = any(
        item.get("PartName") == "/docProps/custom.xml"
        for item in root.findall(f"{{{CT}}}Override")
    )
    if not exists:
        override = etree.SubElement(root, f"{{{CT}}}Override")
        override.set("PartName", "/docProps/custom.xml")
        override.set("ContentType", CUSTOM_CONTENT_TYPE)
    return _serialize(root)


def embed_docx_metadata(docx_data: bytes, key: bytes, employee_id: str) -> bytes:
    """Add per-employee rsid metadata, run IDs, and a custom document property."""
    if not employee_id:
        raise ValueError("employee id must not be empty")
    try:
        with ZipFile(BytesIO(docx_data)) as source:
            infos = source.infolist()
            parts = {info.filename: source.read(info.filename) for info in infos}
    except (BadZipFile, OSError) as error:
        raise ValueError("input is not a valid DOCX package") from error
    required = {"word/settings.xml", "word/document.xml", "_rels/.rels", "[Content_Types].xml"}
    if not required.issubset(parts):
        raise ValueError("DOCX package is missing required OOXML parts")

    root_id = derive_rsid(key, employee_id)
    document = _xml(parts["word/document.xml"], "word/document.xml")
    _split_runs(document, key, employee_id)
    run_ids = _stamp_document(document, key, employee_id)
    settings = _xml(parts["word/settings.xml"], "word/settings.xml")
    _stamp_settings(settings, root_id, run_ids)
    parts["word/document.xml"] = _serialize(document)
    parts["word/settings.xml"] = _serialize(settings)
    parts["_rels/.rels"] = _ensure_relationship(parts["_rels/.rels"])
    parts["[Content_Types].xml"] = _ensure_content_type(parts["[Content_Types].xml"])
    parts["docProps/custom.xml"] = _custom_properties(
        parts.get("docProps/custom.xml"), employee_id
    )

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
        for info in infos:
            package.writestr(info, parts.pop(info.filename))
        if "docProps/custom.xml" in parts:
            info = ZipInfo("docProps/custom.xml", date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            package.writestr(info, parts.pop("docProps/custom.xml"))
    return output.getvalue()
