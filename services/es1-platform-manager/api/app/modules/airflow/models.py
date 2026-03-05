"""Database models for the airflow module."""
from sqlalchemy import Column, String, Integer, TIMESTAMP, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from app.core.database import Base


class DagFile(Base):
    """DAG files managed by the platform.

    This table is the staging area for DAG source code. Platform-manager writes
    DAG files here (from templates or uploads), and Airflow's DatabaseDagBundle
    reads from it to load DAGs into Airflow's processing pipeline.

    Once Airflow parses a DAG, Airflow's own database becomes the source of truth
    for execution. This table remains the source of truth for the *source code*
    as managed by the platform.
    """

    __tablename__ = "dag_files"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    filename = Column(String(255), nullable=False, unique=True)
    dag_id = Column(String(255), nullable=True)  # Extracted from content, may be null for bundles
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    created_by = Column(String(100), nullable=False, server_default="platform")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dag_files_filename", "filename"),
        Index("idx_dag_files_dag_id", "dag_id"),
    )
