"""
Database schema models for Legal Tabular Review System.
Defines all data structures, relationships, and status enumerations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

Base = declarative_base()


# ==================== ENUMERATIONS ====================

class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    CREATED = "CREATED"
    INGESTING = "INGESTING"
    INDEXING = "INDEXING"
    READY = "READY"
    EXTRACTING = "EXTRACTING"
    REVIEW_PENDING = "REVIEW_PENDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    INDEXED = "INDEXED"
    EXTRACTED = "EXTRACTED"
    ERROR = "ERROR"


class ExtractionStatus(str, Enum):
    """Field extraction status."""
    PENDING = "PENDING"
    EXTRACTED = "EXTRACTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    MANUAL_UPDATED = "MANUAL_UPDATED"
    MISSING_DATA = "MISSING_DATA"


class FieldType(str, Enum):
    """Field data types."""
    TEXT = "TEXT"
    DATE = "DATE"
    CURRENCY = "CURRENCY"
    PERCENTAGE = "PERCENTAGE"
    ENTITY = "ENTITY"
    BOOLEAN = "BOOLEAN"
    MULTI_SELECT = "MULTI_SELECT"
    FREEFORM = "FREEFORM"


class TaskStatus(str, Enum):
    """Async task processing status."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ==================== DATABASE MODELS ====================

class Project(Base):
    """Represents a review project containing multiple documents."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    field_template_id = Column(String(36), ForeignKey("field_templates.id"), nullable=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.CREATED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    field_template = relationship("FieldTemplate", back_populates="projects")
    extractions = relationship("ExtractionResult", back_populates="project", cascade="all, delete-orphan")
    review_states = relationship("ReviewState", back_populates="project", cascade="all, delete-orphan")
    evaluations = relationship("EvaluationResult", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    """Represents a legal document uploaded to a project."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(512), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, html, txt
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_text = Column(Text, nullable=False)
    parsed_metadata = Column(JSON, default={}, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="document", cascade="all, delete-orphan")
    extractions = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Represents indexed chunks of a document for retrieval."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(512), nullable=True)
    embedding = Column(JSON, nullable=True)  # Vector embedding for similarity search
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class FieldTemplate(Base):
    """Defines extractable fields and their validation rules."""
    __tablename__ = "field_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    fields = Column(JSON, nullable=False)  # List of FieldDefinition dicts
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="field_template")


class ExtractionResult(Base):
    """Stores extracted field values from documents."""
    __tablename__ = "extraction_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    field_name = Column(String(256), nullable=False)
    field_type = Column(SQLEnum(FieldType), nullable=False)
    extracted_value = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)
    status = Column(SQLEnum(ExtractionStatus), default=ExtractionStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="extractions")
    document = relationship("Document", back_populates="extractions")
    citations = relationship("Citation", back_populates="extraction", cascade="all, delete-orphan")
    review_state = relationship("ReviewState", back_populates="extraction", uselist=False, cascade="all, delete-orphan")


class Citation(Base):
    """Stores references to source text supporting extracted fields."""
    __tablename__ = "citations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    extraction_id = Column(String(36), ForeignKey("extraction_results.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(String(36), ForeignKey("document_chunks.id"), nullable=True)
    citation_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(512), nullable=True)
    relevance_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    extraction = relationship("ExtractionResult", back_populates="citations")
    document = relationship("Document", back_populates="citations")


class ReviewState(Base):
    """Tracks review status and manual edits for extracted fields."""
    __tablename__ = "review_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    extraction_id = Column(String(36), ForeignKey("extraction_results.id"), nullable=False, unique=True)
    status = Column(SQLEnum(ExtractionStatus), default=ExtractionStatus.PENDING, nullable=False)
    ai_value = Column(Text, nullable=True)
    manual_value = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(256), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="review_states")
    extraction = relationship("ExtractionResult", back_populates="review_state")


class Annotation(Base):
    """Stores annotations and comments on fields for collaboration."""
    __tablename__ = "annotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    extraction_id = Column(String(36), ForeignKey("extraction_results.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    annotated_by = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class Task(Base):
    """Tracks async processing tasks (ingestion, extraction, evaluation)."""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_type = Column(String(64), nullable=False)  # ingest, extract, evaluate
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.QUEUED, nullable=False)
    result = Column(JSON, default={}, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")


class EvaluationResult(Base):
    """Stores evaluation metrics comparing AI vs. human extraction."""
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    field_name = Column(String(256), nullable=False)
    ai_value = Column(Text, nullable=True)
    human_value = Column(Text, nullable=True)
    match_score = Column(Float, default=0.0, nullable=False)
    normalized_match = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="evaluations")
    document = relationship("Document")


# ==================== PYDANTIC MODELS (API SCHEMAS) ====================

class FieldDefinition(BaseModel):
    """Defines a single extractable field."""
    name: str = Field(..., description="Unique field identifier")
    display_name: str = Field(..., description="User-friendly field name")
    field_type: FieldType = Field(default=FieldType.TEXT, description="Data type of the field")
    description: str = Field("", description="Field documentation")
    required: bool = Field(default=False, description="Whether field is mandatory")
    normalization_rules: Optional[Dict[str, Any]] = Field(default=None, description="Normalization logic")
    validation_rules: Optional[Dict[str, Any]] = Field(default=None, description="Validation constraints")
    examples: Optional[List[str]] = Field(default=None, description="Example values")


class FieldTemplateCreate(BaseModel):
    """Request to create a field template."""
    name: str
    description: Optional[str] = None
    fields: List[FieldDefinition]


class FieldTemplateResponse(BaseModel):
    """Response containing field template information."""
    id: str
    name: str
    description: Optional[str]
    version: int
    fields: List[FieldDefinition]
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class DocumentMetadata(BaseModel):
    """Metadata extracted from documents."""
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    pages: Optional[int] = None
    language: Optional[str] = None


class CitationDTO(BaseModel):
    """Data transfer object for citations."""
    id: str
    citation_text: str
    page_number: Optional[int]
    section_title: Optional[str]
    relevance_score: float

    model_config = {"from_attributes": True}


class ExtractionResultDTO(BaseModel):
    """Data transfer object for extraction results."""
    id: str
    field_name: str
    field_type: FieldType
    extracted_value: Optional[str]
    raw_text: Optional[str]
    normalized_value: Optional[str]
    confidence_score: float
    status: ExtractionStatus
    citations: List[CitationDTO] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewStateDTO(BaseModel):
    """Data transfer object for review states."""
    id: str
    extraction_id: str
    status: ExtractionStatus
    ai_value: Optional[str]
    manual_value: Optional[str]
    reviewer_notes: Optional[str]
    confidence_score: float
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]

    model_config = {"from_attributes": True}


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = None
    field_template_id: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    """Request to update project."""
    name: Optional[str] = None
    description: Optional[str] = None
    field_template_id: Optional[str] = None


class ProjectResponse(BaseModel):
    """Complete project information."""
    id: str
    name: str
    description: Optional[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0
    extraction_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class DocumentUploadRequest(BaseModel):
    """Request to upload a document."""
    project_id: str
    filename: str


class DocumentResponse(BaseModel):
    """Document information."""
    id: str
    project_id: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TableRow(BaseModel):
    """Represents a row in the comparison table."""
    field_name: str
    field_type: FieldType
    document_results: Dict[str, ExtractionResultDTO]  # document_id -> result


class ComparisonTableResponse(BaseModel):
    """Complete comparison table for all documents."""
    project_id: str
    document_count: int
    row_count: int
    rows: List[TableRow]
    generation_timestamp: datetime


class ExtractionUpdateRequest(BaseModel):
    """Request to review/update extracted field."""
    status: ExtractionStatus
    manual_value: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None


class AnnotationCreateRequest(BaseModel):
    """Request to create an annotation."""
    extraction_id: str
    comment_text: str
    annotated_by: str = Field(default="anonymous", description="User creating the annotation")


class AnnotationUpdateRequest(BaseModel):
    """Request to update an annotation."""
    comment_text: str


class AnnotationResponse(BaseModel):
    """Response for an annotation."""
    id: str
    extraction_id: str
    comment_text: str
    annotated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskStatusResponse(BaseModel):
    """Status of an async task."""
    task_id: str
    task_type: str
    project_id: Optional[str]
    status: TaskStatus
    result: Dict[str, Any]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for a project."""
    total_fields: int
    matched_fields: int
    field_accuracy: float
    average_confidence: float
    coverage_percentage: float
    timestamp: datetime


class EvaluationReportResponse(BaseModel):
    """Complete evaluation report."""
    project_id: str
    metrics: EvaluationMetrics
    field_results: List[Dict[str, Any]]
    summary: str
