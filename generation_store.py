
import json
from sqlalchemy.orm import Session

from app.models import TestGeneration


def save_generation(
    db: Session,
    selection_id: int,
    output: dict,
    is_stale: bool = False,
) -> TestGeneration:
    """Save generated test cases and their selection reference."""

    generation = TestGeneration(
        selection_id=selection_id,
        output_json=json.dumps(output),
        is_stale=is_stale,
    )

    db.add(generation)
    db.commit()
    db.refresh(generation)

    return generation


def get_generation(
    db: Session,
    generation_id: int,
) -> TestGeneration | None:
    """Retrieve a generation by its ID."""

    return (
        db.query(TestGeneration)
        .filter(TestGeneration.id == generation_id)
        .first()
    )


def get_generations_by_selection(
    db: Session,
    selection_id: int,
) -> list[TestGeneration]:
    """Retrieve all generations linked to a selection."""

    return (
        db.query(TestGeneration)
        .filter(TestGeneration.selection_id == selection_id)
        .order_by(TestGeneration.id.desc())
        .all()
    )
