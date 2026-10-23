
import re
import hashlib
import unicodedata
from pathlib import Path

import pymupdf


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def make_id(number, heading):
    value = f"{number}|{heading}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def content_hash(text):
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)

    nodes = []
    section_map = {}
    current_node = None

    heading_pattern = re.compile(
        r"^(\d+(?:\.\d+)*)\.\s+([A-Z][A-Za-z].*)$"
    )

    subsection_pattern = re.compile(
        r"^(\d+(?:\.\d+)+)\s+([A-Z][A-Za-z].*)$"
    )

    ignored_starts = (
        "Normal:",
        "Elevated:",
        "Hypertension Stage",
        "Hypertensive Crisis:",
    )

    for page_number, page in enumerate(doc, start=1):
        page_text = page.get_text("text")

        for raw_line in page_text.splitlines():
            line = normalize_text(raw_line)

            if not line:
                continue

            match = heading_pattern.match(line)

            if not match:
                match = subsection_pattern.match(line)

            if match:
                number, heading = match.groups()

                # Avoid treating classification list items as headings.
                if heading.startswith(ignored_starts):
                    match = None

            if match:
                number, heading = match.groups()

                node = {
                    "id": make_id(number, heading),
                    "section_number": number,
                    "heading": heading,
                    "level": number.count(".") + 1,
                    "page": page_number,
                    "body": "",
                    "parent_id": None,
                    "children": [],
                    "synthetic": False,
                }

                nodes.append(node)
                section_map[number] = node
                current_node = node

            elif current_node is not None:
                current_node["body"] += line + "\n"

    # Create missing intermediate parent sections.
    existing_numbers = set(section_map.keys())
    synthetic_nodes = []

    for node in list(nodes):
        parts = node["section_number"].split(".")

        for size in range(1, len(parts)):
            parent_number = ".".join(parts[:size])

            if parent_number in existing_numbers:
                continue

            parent_parts = parent_number.split(".")

            synthetic = {
                "id": make_id(
                    parent_number,
                    f"[Missing heading: {parent_number}]",
                ),
                "section_number": parent_number,
                "heading": f"[Missing heading: {parent_number}]",
                "level": len(parent_parts),
                "page": node["page"],
                "body": "",
                "parent_id": None,
                "children": [],
                "synthetic": True,
            }

            synthetic_nodes.append(synthetic)
            existing_numbers.add(parent_number)
            section_map[parent_number] = synthetic

    # Insert synthetic sections before their first descendant.
    for synthetic in sorted(
        synthetic_nodes,
        key=lambda item: item["level"],
    ):
        descendant_prefix = synthetic["section_number"] + "."
        insert_at = next(
            (
                index
                for index, node in enumerate(nodes)
                if node["section_number"].startswith(descendant_prefix)
            ),
            len(nodes),
        )
        nodes.insert(insert_at, synthetic)

    # Rebuild the complete parent-child hierarchy.
    for node in nodes:
        node["parent_id"] = None
        node["children"] = []

    for node in nodes:
        parts = node["section_number"].split(".")

        for size in range(len(parts) - 1, 0, -1):
            parent_number = ".".join(parts[:size])
            parent = section_map.get(parent_number)

            if parent is not None:
                node["parent_id"] = parent["id"]

                if node["id"] not in parent["children"]:
                    parent["children"].append(node["id"])

                break

    # Calculate content hashes after parsing and hierarchy creation.
    for node in nodes:
        node["body"] = node["body"].strip()
        node["content_hash"] = content_hash(
            node["heading"] + "\n" + node["body"]
        )

    doc.close()
    return nodes


if __name__ == "__main__":
    pdf_path = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "ct200_manual.pdf"
)
    nodes = parse_pdf(pdf_path)

    print("Extracted section nodes:", len(nodes))
    print()

    for node in nodes:
        print(
            f'{node["section_number"]} | {node["heading"]} | '
            f'level={node["level"]} | parent={node["parent_id"]}'
        )
