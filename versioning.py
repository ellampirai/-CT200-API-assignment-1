
from app.parser import parse_pdf


def compare_versions(old_pdf, new_pdf):
    old_nodes = parse_pdf(old_pdf)
    new_nodes = parse_pdf(new_pdf)

    old_sections = {
        node["section_number"]: node
        for node in old_nodes
        if not node.get("synthetic", False)
    }

    new_sections = {
        node["section_number"]: node
        for node in new_nodes
        if not node.get("synthetic", False)
    }

    changes = []

    # Sections newly added or changed in the new manual.
    for number, new_node in new_sections.items():
        if number not in old_sections:
            changes.append({
                "section_number": number,
                "heading": new_node["heading"],
                "status": "added",
                "old_hash": None,
                "new_hash": new_node["content_hash"],
            })
        elif (
            old_sections[number]["content_hash"]
            != new_node["content_hash"]
        ):
            changes.append({
                "section_number": number,
                "heading": new_node["heading"],
                "status": "changed",
                "old_hash": old_sections[number]["content_hash"],
                "new_hash": new_node["content_hash"],
            })

    # Sections removed from the new manual.
    for number, old_node in old_sections.items():
        if number not in new_sections:
            changes.append({
                "section_number": number,
                "heading": old_node["heading"],
                "status": "removed",
                "old_hash": old_node["content_hash"],
                "new_hash": None,
            })

    return changes


if __name__ == "__main__":
    from pathlib import Path

    old_pdf = Path("../data/ct200_manual.pdf")
    new_pdf = Path("../data/ct200_manual_v2.pdf")

    changes = compare_versions(old_pdf, new_pdf)

    print("Version comparison results:")
    print("Total changes:", len(changes))

    for change in changes:
        print(
            f'{change["status"].upper()} | '
            f'{change["section_number"]} | '
            f'{change["heading"]}'
        )
