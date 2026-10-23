
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import DocumentVersion, SectionNode
from app.parser import parse_pdf


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

MANUALS = {
    "v1": DATA_DIR / "ct200_manual.pdf",
    "v2": DATA_DIR / "ct200_manual_v2.pdf",
}


def ingest_manual(version_label: str) -> dict:
    if version_label not in MANUALS:
        raise ValueError("Version must be v1 or v2.")

    pdf_path = MANUALS[version_label]

    if not pdf_path.exists():
        raise FileNotFoundError(f"Manual not found: {pdf_path}")

    # Parse the PDF before opening a database transaction.
    parsed_nodes = parse_pdf(pdf_path)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_version = (
            db.query(DocumentVersion)
            .filter_by(version_label=version_label)
            .first()
        )

        # Do not overwrite a version that has already been ingested.
        if existing_version is not None:
            return {
                "message": "Version already exists; existing data preserved.",
                "version": version_label,
                "version_id": existing_version.id,
                "total_sections": len(existing_version.nodes),
            }

        version = DocumentVersion(
            version_label=version_label,
            source_filename=pdf_path.name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        db.add(version)
        db.flush()

        # First create every node so parent relationships can be stored.
        node_records = []

        for item in parsed_nodes:
            record = SectionNode(
                node_id=item["id"],
                section_number=item["section_number"],
                heading=item["heading"],
                level=item["level"],
                page=item.get("page"),
                body=item.get("body", ""),
                content_hash=item["content_hash"],
                synthetic=item.get("synthetic", False),
                version_id=version.id,
                parent_node_id=item.get("parent_id"),
            )

            db.add(record)
            node_records.append(record)

        db.commit()

        return {
            "message": "Manual ingested successfully.",
            "version": version_label,
            "version_id": version.id,
            "total_sections": len(node_records),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        choices=["v1", "v2"],
        required=True,
        help="Manual version to ingest",
    )
    args = parser.parse_args()

    result = ingest_manual(args.version)
    print(result)
