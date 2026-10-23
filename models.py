
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_label = Column(String(20), nullable=False, unique=True)
    source_filename = Column(String(255), nullable=False)
    created_at = Column(String(40), nullable=False)

    nodes = relationship(
        "SectionNode",
        back_populates="version",
        cascade="all, delete-orphan",
    )


class SectionNode(Base):
    __tablename__ = "section_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String(64), nullable=False)
    section_number = Column(String(50), nullable=False)
    heading = Column(String(500), nullable=False)
    level = Column(Integer, nullable=False)
    page = Column(Integer, nullable=True)
    body = Column(Text, nullable=False, default="")
    content_hash = Column(String(64), nullable=False)
    synthetic = Column(Boolean, nullable=False, default=False)

    version_id = Column(
        Integer,
        ForeignKey("document_versions.id"),
        nullable=False,
    )

    parent_node_id = Column(String(64), nullable=True)

    version = relationship(
        "DocumentVersion",
        back_populates="nodes",
    )

    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "node_id",
            name="uq_version_node",
        ),
    )


class TestSelection(Base):
    __tablename__ = "test_selections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    version_id = Column(
        Integer,
        ForeignKey("document_versions.id"),
        nullable=False,
    )

    created_at = Column(
        String(40),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    items = relationship(
        "TestSelectionItem",
        back_populates="selection",
        cascade="all, delete-orphan",
    )

    generations = relationship(
        "TestGeneration",
        back_populates="selection",
        cascade="all, delete-orphan",
    )


class TestSelectionItem(Base):
    __tablename__ = "test_selection_items"

    id = Column(Integer, primary_key=True, index=True)

    selection_id = Column(
        Integer,
        ForeignKey("test_selections.id"),
        nullable=False,
    )

    node_id = Column(String(64), nullable=False)
    heading = Column(String(500), nullable=False)
    body_snapshot = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)

    selection = relationship(
        "TestSelection",
        back_populates="items",
    )

    __table_args__ = (
        UniqueConstraint(
            "selection_id",
            "node_id",
            name="uq_selection_node",
        ),
    )


class TestGeneration(Base):
    __tablename__ = "test_generations"

    id = Column(Integer, primary_key=True, index=True)

    selection_id = Column(
        Integer,
        ForeignKey("test_selections.id"),
        nullable=False,
    )

    output_json = Column(Text, nullable=False)

    created_at = Column(
        String(40),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    is_stale = Column(Boolean, nullable=False, default=False)

    selection = relationship(
        "TestSelection",
        back_populates="generations",
    )
