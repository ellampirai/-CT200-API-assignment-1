
from pathlib import Path

from app.parser import parse_pdf


PDF_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "ct200_manual.pdf"
)


def test_main_sections_have_no_parent():
    nodes = parse_pdf(PDF_PATH)

    main_sections = [
        node for node in nodes
        if node["level"] == 1
    ]

    assert len(main_sections) == 8
    assert all(
        node["parent_id"] is None
        for node in main_sections
    )


def test_duplicate_heading_has_distinct_nodes():
    nodes = parse_pdf(PDF_PATH)

    duplicates = [
        node for node in nodes
        if node["heading"] == "Error Codes"
    ]

    assert len(duplicates) == 2
    assert duplicates[0]["id"] != duplicates[1]["id"]
    assert duplicates[0]["section_number"] == "4.2"
    assert duplicates[1]["section_number"] == "7.1"


def test_out_of_order_sections_are_preserved():
    nodes = parse_pdf(PDF_PATH)

    numbers = [
        node["section_number"]
        for node in nodes
    ]

    assert numbers.index("3.4") < numbers.index("3.3")


def test_deep_section_is_detected():
    nodes = parse_pdf(PDF_PATH)

    battery = next(
        node for node in nodes
        if node["section_number"] == "2.1.1.1"
    )

    assert battery["level"] == 4
