import json
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import (
    DocumentVersion,
    SectionNode,
    TestSelection,
    TestSelectionItem,
    TestGeneration,
)
from app.schemas import SelectionCreate, GenerateRequest
from app.llm import generate_cases

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CT200 API")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def check_generation_stale(
    db: Session,
    generation: TestGeneration,
) -> bool:
    """Check whether selected source content changed in the latest version."""

    selection = (
        db.query(TestSelection)
        .filter(TestSelection.id == generation.selection_id)
        .first()
    )

    if not selection:
        return True

    source_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == selection.version_id)
        .first()
    )

    if not source_version:
        return True

    latest_version = (
        db.query(DocumentVersion)
        .order_by(DocumentVersion.id.desc())
        .first()
    )

    if not latest_version or latest_version.id == source_version.id:
        return bool(generation.is_stale)

    for item in selection.items:
        latest_node = (
            db.query(SectionNode)
            .filter(
                SectionNode.version_id == latest_version.id,
                SectionNode.node_id == item.node_id,
            )
            .first()
        )

        if (
            not latest_node
            or latest_node.content_hash != item.content_hash
        ):
            if not generation.is_stale:
                generation.is_stale = True
                db.commit()
            return True

    if generation.is_stale:
        generation.is_stale = False
        db.commit()

    return False


@app.get("/")
def root():
    return {"message": "CT200 API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sections")
def get_sections(
    version: str = Query("v1"),
    db: Session = Depends(get_db),
):
    document_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == version)
        .first()
    )

    if not document_version:
        raise HTTPException(status_code=404, detail="Version not found")

    nodes = (
        db.query(SectionNode)
        .filter(SectionNode.version_id == document_version.id)
        .all()
    )

    return [
        {
            "node_id": node.node_id,
            "section_number": node.section_number,
            "heading": node.heading,
            "level": node.level,
            "page": node.page,
            "body": node.body,
            "content_hash": node.content_hash,
            "parent_node_id": node.parent_node_id,
        }
        for node in nodes
    ]


@app.get("/nodes/{node_id}")
def get_node(
    node_id: str,
    version: str = Query("v1"),
    db: Session = Depends(get_db),
):
    document_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == version)
        .first()
    )

    if not document_version:
        raise HTTPException(status_code=404, detail="Version not found")

    node = (
        db.query(SectionNode)
        .filter(
            SectionNode.version_id == document_version.id,
            SectionNode.node_id == node_id,
        )
        .first()
    )

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return {
        "node_id": node.node_id,
        "section_number": node.section_number,
        "heading": node.heading,
        "level": node.level,
        "page": node.page,
        "body": node.body,
        "content_hash": node.content_hash,
        "parent_node_id": node.parent_node_id,
        "version": document_version.version_label,
    }


@app.get("/search")
def search_nodes(
    q: str,
    version: str = Query("v1"),
    db: Session = Depends(get_db),
):
    document_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == version)
        .first()
    )

    if not document_version:
        raise HTTPException(status_code=404, detail="Version not found")

    search_term = f"%{q}%"

    nodes = (
        db.query(SectionNode)
        .filter(
            SectionNode.version_id == document_version.id,
            (
                SectionNode.heading.ilike(search_term)
                | SectionNode.body.ilike(search_term)
            ),
        )
        .all()
    )

    return [
        {
            "node_id": node.node_id,
            "section_number": node.section_number,
            "heading": node.heading,
            "body": node.body,
            "content_hash": node.content_hash,
        }
        for node in nodes
    ]


@app.get("/nodes/{node_id}/changes")
def node_changes(
    node_id: str,
    db: Session = Depends(get_db),
):
    versions = (
        db.query(DocumentVersion)
        .order_by(DocumentVersion.id.asc())
        .all()
    )

    results = []

    for version in versions:
        node = (
            db.query(SectionNode)
            .filter(
                SectionNode.version_id == version.id,
                SectionNode.node_id == node_id,
            )
            .first()
        )

        results.append(
            {
                "version": version.version_label,
                "exists": node is not None,
                "heading": node.heading if node else None,
                "content_hash": node.content_hash if node else None,
            }
        )

    return {"node_id": node_id, "versions": results}


@app.get("/compare")
def compare(
    version1: str = "v1",
    version2: str = "v2",
    db: Session = Depends(get_db),
):
    v1 = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == version1)
        .first()
    )
    v2 = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == version2)
        .first()
    )

    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")

    nodes1 = (
        db.query(SectionNode)
        .filter(SectionNode.version_id == v1.id)
        .all()
    )
    nodes2 = (
        db.query(SectionNode)
        .filter(SectionNode.version_id == v2.id)
        .all()
    )

    map1 = {node.node_id: node for node in nodes1}
    map2 = {node.node_id: node for node in nodes2}

    changes = []

    for node_id in sorted(set(map1) | set(map2)):
        old = map1.get(node_id)
        new = map2.get(node_id)

        if old is None:
            status = "added"
        elif new is None:
            status = "removed"
        elif old.content_hash != new.content_hash:
            status = "changed"
        else:
            status = "unchanged"

        if status != "unchanged":
            changes.append(
                {
                    "node_id": node_id,
                    "status": status,
                    "old_heading": old.heading if old else None,
                    "new_heading": new.heading if new else None,
                }
            )

    return {
        "old_version": version1,
        "new_version": version2,
        "total_changes": len(changes),
        "changes": changes,
    }


@app.post("/selections")
def create_selection(
    request: SelectionCreate,
    db: Session = Depends(get_db),
):
    version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.version_label == request.version)
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if len(set(request.node_ids)) != len(request.node_ids):
        raise HTTPException(
            status_code=400,
            detail="Duplicate node IDs are not allowed",
        )

    nodes = (
        db.query(SectionNode)
        .filter(
            SectionNode.version_id == version.id,
            SectionNode.node_id.in_(request.node_ids),
        )
        .all()
    )

    node_map = {node.node_id: node for node in nodes}
    missing = [
        node_id
        for node_id in request.node_ids
        if node_id not in node_map
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some nodes were not found in this version",
                "missing_node_ids": missing,
            },
        )

    selection = TestSelection(
        name=request.name,
        version_id=version.id,
        created_at=now_iso(),
    )

    db.add(selection)
    db.flush()

    for node_id in request.node_ids:
        node = node_map[node_id]

        db.add(
            TestSelectionItem(
                selection_id=selection.id,
                node_id=node.node_id,
                heading=node.heading,
                body_snapshot=node.body,
                content_hash=node.content_hash,
            )
        )

    db.commit()
    db.refresh(selection)

    return {
        "selection_id": selection.id,
        "name": selection.name,
        "version": version.version_label,
        "selected_node_ids": request.node_ids,
        "message": "Selection saved successfully.",
    }


@app.post("/generate")
def generate(
    request: GenerateRequest,
    db: Session = Depends(get_db),
):
    selection = (
        db.query(TestSelection)
        .filter(TestSelection.id == request.selection_id)
        .first()
    )

    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")

    if not request.force_new:
        existing = (
            db.query(TestGeneration)
            .filter(TestGeneration.selection_id == selection.id)
            .order_by(TestGeneration.id.desc())
            .first()
        )

        if existing:
            stale = check_generation_stale(db, existing)

            return {
                "generation_id": existing.id,
                "selection_id": selection.id,
                "test_cases": json.loads(
                    existing.output_json
                ).get("test_cases", []),
                "is_stale": stale,
                "message": "Existing generation returned.",
            }

    source_nodes = [
        {
            "node_id": item.node_id,
            "heading": item.heading,
            "body": item.body_snapshot,
            "content_hash": item.content_hash,
        }
        for item in selection.items
    ]

    try:
        output = generate_cases(source_nodes)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Test-case generation failed: {exc}",
        ) from exc

    generation = TestGeneration(
        selection_id=selection.id,
        output_json=output.model_dump_json(),
        created_at=now_iso(),
        is_stale=False,
    )

    db.add(generation)
    db.commit()
    db.refresh(generation)

    return {
        "generation_id": generation.id,
        "selection_id": selection.id,
        "test_cases": output.model_dump()["test_cases"],
        "is_stale": False,
        "message": "Test cases generated and saved successfully.",
    }


@app.get("/generations/{generation_id}")
def get_generation(
    generation_id: int,
    db: Session = Depends(get_db),
):
    generation = (
        db.query(TestGeneration)
        .filter(TestGeneration.id == generation_id)
        .first()
    )

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    stale = check_generation_stale(db, generation)
    selection = generation.selection

    source_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == selection.version_id)
        .first()
    )

    return {
        "generation_id": generation.id,
        "selection_id": selection.id,
        "selection_name": selection.name,
        "source_version": (
            source_version.version_label if source_version else None
        ),
        "source_nodes": [
            {
                "node_id": item.node_id,
                "heading": item.heading,
                "content_hash": item.content_hash,
            }
            for item in selection.items
        ],
        "test_cases": json.loads(
            generation.output_json
        ).get("test_cases", []),
        "created_at": generation.created_at,
        "is_stale": stale,
    }


@app.get("/selections/{selection_id}/generations")
def get_generations_by_selection(
    selection_id: int,
    db: Session = Depends(get_db),
):
    selection = (
        db.query(TestSelection)
        .filter(TestSelection.id == selection_id)
        .first()
    )

    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")

    source_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == selection.version_id)
        .first()
    )

    generations = (
        db.query(TestGeneration)
        .filter(TestGeneration.selection_id == selection_id)
        .order_by(TestGeneration.id.desc())
        .all()
    )

    results = []

    for generation in generations:
        stale = check_generation_stale(db, generation)
        payload = json.loads(generation.output_json)

        results.append(
            {
                "generation_id": generation.id,
                "selection_id": generation.selection_id,
                "is_stale": stale,
                "test_cases": payload.get("test_cases", []),
                "created_at": generation.created_at,
            }
        )

    return {
        "selection_id": selection.id,
        "selection_name": selection.name,
        "source_version": (
            source_version.version_label if source_version else None
        ),
        "generations": results,
    }


@app.get("/nodes/{node_id}/generations")
def get_generations_by_node(
    node_id: str,
    db: Session = Depends(get_db),
):
    selection_items = (
        db.query(TestSelectionItem)
        .filter(TestSelectionItem.node_id == node_id)
        .all()
    )

    if not selection_items:
        raise HTTPException(
            status_code=404,
            detail="No saved selections found for this node",
        )

    selection_ids = sorted(
        {item.selection_id for item in selection_items}
    )

    generations = (
        db.query(TestGeneration)
        .filter(TestGeneration.selection_id.in_(selection_ids))
        .order_by(TestGeneration.id.desc())
        .all()
    )

    results = []

    for generation in generations:
        stale = check_generation_stale(db, generation)
        payload = json.loads(generation.output_json)

        results.append(
            {
                "generation_id": generation.id,
                "selection_id": generation.selection_id,
                "node_id": node_id,
                "is_stale": stale,
                "test_cases": payload.get("test_cases", []),
                "created_at": generation.created_at,
            }
        )

    return {
        "node_id": node_id,
        "generations": results,
    }