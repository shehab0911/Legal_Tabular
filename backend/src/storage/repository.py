"""
Database repository layer for all database operations.
"""

from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional, Dict, Any
import logging
import time
import functools

from src.models.schema import (
    Base, Project, Document, DocumentChunk, FieldTemplate, ExtractionResult,
    Citation, ReviewState, Annotation, Task, EvaluationResult,
    ProjectStatus, DocumentStatus, ExtractionStatus, TaskStatus
)
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def retry_on_lock(max_retries=5, delay=1.0):
    """Decorator to retry database operations on lock error."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and retries < max_retries:
                        retries += 1
                        sleep_time = delay * retries
                        logger.warning(f"Database locked in {func.__name__}, retrying in {sleep_time}s ({retries}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                    raise
        return wrapper
    return decorator


class DatabaseRepository:
    """Repository pattern for all database operations."""

    def __init__(self, database_url: str):
        """Initialize database connection."""
        if "sqlite" in database_url:
            # Optimize SQLite for concurrency
            self.engine = create_engine(
                database_url, 
                echo=False,
                connect_args={'check_same_thread': False, 'timeout': 60}  # Increased timeout
            )
            # Enable WAL mode
            try:
                with self.engine.connect() as connection:
                    connection.execute(text("PRAGMA journal_mode=WAL;"))
                    connection.execute(text("PRAGMA synchronous=NORMAL;"))
            except Exception as e:
                logger.warning(f"Could not set SQLite PRAGMA: {e}")
        else:
            self.engine = create_engine(database_url, echo=False)

        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get new database session."""
        return self.SessionLocal()

    # ==================== PROJECT OPERATIONS ====================

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        field_template_id: Optional[str] = None,
    ) -> Project:
        """Create new project."""
        session = self.get_session()
        try:
            project = Project(
                name=name,
                description=description,
                field_template_id=field_template_id,
                status=ProjectStatus.CREATED,
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
        finally:
            session.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        session = self.get_session()
        try:
            return session.query(Project).filter(Project.id == project_id).first()
        finally:
            session.close()

    def list_projects(self, skip: int = 0, limit: int = 100) -> List[Project]:
        """List all projects."""
        session = self.get_session()
        try:
            return session.query(Project).offset(skip).limit(limit).all()
        finally:
            session.close()

    def update_project(
        self,
        project_id: str,
        **kwargs
    ) -> Optional[Project]:
        """Update project."""
        session = self.get_session()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                for key, value in kwargs.items():
                    if hasattr(project, key):
                        setattr(project, key, value)
                session.commit()
                session.refresh(project)
            return project
        finally:
            session.close()

    @retry_on_lock()
    def delete_project(self, project_id: str) -> bool:
        """Delete project and related data."""
        session = self.get_session()
        try:
            # Enable foreign key support for this session to ensure cascades work if supported
            if "sqlite" in str(self.engine.url):
                session.execute(text("PRAGMA foreign_keys=ON"))

            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                # Manually delete related tasks to avoid FK constraint issues if cascade fails
                session.query(Task).filter(Task.project_id == project_id).delete(synchronize_session=False)
                
                session.delete(project)
                session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== DOCUMENT OPERATIONS ====================

    @retry_on_lock()
    def create_document(
        self,
        project_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        file_size: int,
        content_text: str,
        parsed_metadata: Dict[str, Any] = None,
    ) -> Document:
        """Create new document."""
        session = self.get_session()
        try:
            doc = Document(
                project_id=project_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                content_text=content_text,
                parsed_metadata=parsed_metadata or {},
                status=DocumentStatus.UPLOADED,
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            return doc
        finally:
            session.close()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        session = self.get_session()
        try:
            return session.query(Document).filter(Document.id == document_id).first()
        finally:
            session.close()

    def list_project_documents(self, project_id: str) -> List[Document]:
        """List all documents in project."""
        session = self.get_session()
        try:
            return session.query(Document).filter(Document.project_id == project_id).all()
        finally:
            session.close()

    def update_document_status(self, document_id: str, status: DocumentStatus) -> Optional[Document]:
        """Update document status."""
        session = self.get_session()
        try:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = status
                session.commit()
                session.refresh(doc)
            return doc
        finally:
            session.close()

    # ==================== DOCUMENT CHUNK OPERATIONS ====================

    def create_chunk(
        self,
        document_id: str,
        chunk_index: int,
        text: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        extra_metadata: Dict[str, Any] = None,
    ) -> DocumentChunk:
        """Create document chunk."""
        session = self.get_session()
        try:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                text=text,
                page_number=page_number,
                section_title=section_title,
                extra_metadata=extra_metadata or {},
            )
            session.add(chunk)
            session.commit()
            session.refresh(chunk)
            return chunk
        finally:
            session.close()

    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for document."""
        session = self.get_session()
        try:
            return session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).all()
        finally:
            session.close()

    @retry_on_lock()
    def create_chunks_bulk(self, chunks_data: List[Dict[str, Any]]) -> bool:
        """Create multiple chunks in bulk."""
        session = self.get_session()
        try:
            chunks = [
                DocumentChunk(
                    document_id=chunk['document_id'],
                    chunk_index=chunk['chunk_index'],
                    text=chunk['text'],
                    page_number=chunk.get('page_number'),
                    section_title=chunk.get('section_title'),
                )
                for chunk in chunks_data
            ]
            session.bulk_save_objects(chunks)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error bulk creating chunks: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== FIELD TEMPLATE OPERATIONS ====================

    def create_field_template(
        self,
        name: str,
        fields: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> FieldTemplate:
        """Create field template."""
        session = self.get_session()
        try:
            template = FieldTemplate(
                name=name,
                description=description,
                fields=fields,
            )
            session.add(template)
            session.commit()
            session.refresh(template)
            return template
        finally:
            session.close()

    def get_field_template(self, template_id: str) -> Optional[FieldTemplate]:
        """Get field template by ID."""
        session = self.get_session()
        try:
            return session.query(FieldTemplate).filter(FieldTemplate.id == template_id).first()
        finally:
            session.close()

    def list_field_templates(self) -> List[FieldTemplate]:
        """List all field templates."""
        session = self.get_session()
        try:
            return session.query(FieldTemplate).filter(FieldTemplate.is_active == True).all()
        finally:
            session.close()

    def update_field_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
    ) -> Optional[FieldTemplate]:
        """Update and version field template."""
        session = self.get_session()
        try:
            template = session.query(FieldTemplate).filter(FieldTemplate.id == template_id).first()
            if template:
                # Create new version
                old_version = template.version
                template.version = old_version + 1
                if name:
                    template.name = name
                if description is not None:
                    template.description = description
                if fields:
                    template.fields = fields
                session.commit()
                session.refresh(template)
            return template
        finally:
            session.close()

    # ==================== EXTRACTION RESULT OPERATIONS ====================

    def create_extraction(
        self,
        project_id: str,
        document_id: str,
        field_name: str,
        field_type: str,
        extracted_value: Optional[str] = None,
        raw_text: Optional[str] = None,
        normalized_value: Optional[str] = None,
        confidence_score: float = 0.0,
        extra_metadata: Dict[str, Any] = None,
    ) -> ExtractionResult:
        """Create extraction result."""
        session = self.get_session()
        try:
            extraction = ExtractionResult(
                project_id=project_id,
                document_id=document_id,
                field_name=field_name,
                field_type=field_type,
                extracted_value=extracted_value,
                raw_text=raw_text,
                normalized_value=normalized_value,
                confidence_score=confidence_score,
                status=ExtractionStatus.EXTRACTED,
                extra_metadata=extra_metadata or {},
            )
            session.add(extraction)
            session.commit()
            session.refresh(extraction)
            return extraction
        finally:
            session.close()

    def get_extraction(self, extraction_id: str) -> Optional[ExtractionResult]:
        """Get extraction by ID."""
        session = self.get_session()
        try:
            return session.query(ExtractionResult).filter(
                ExtractionResult.id == extraction_id
            ).first()
        finally:
            session.close()

    def list_extractions_by_project(
        self,
        project_id: str,
        field_name: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> List[ExtractionResult]:
        """List extractions for project."""
        session = self.get_session()
        try:
            query = session.query(ExtractionResult).filter(
                ExtractionResult.project_id == project_id
            )
            if field_name:
                query = query.filter(ExtractionResult.field_name == field_name)
            if document_id:
                query = query.filter(ExtractionResult.document_id == document_id)
            return query.all()
        finally:
            session.close()

    def update_extraction(
        self,
        extraction_id: str,
        **kwargs
    ) -> Optional[ExtractionResult]:
        """Update extraction."""
        session = self.get_session()
        try:
            extraction = session.query(ExtractionResult).filter(
                ExtractionResult.id == extraction_id
            ).first()
            if extraction:
                for key, value in kwargs.items():
                    if hasattr(extraction, key):
                        setattr(extraction, key, value)
                session.commit()
                session.refresh(extraction)
            return extraction
        finally:
            session.close()

    # ==================== CITATION OPERATIONS ====================

    def create_citation(
        self,
        extraction_id: str,
        document_id: str,
        citation_text: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        relevance_score: float = 0.0,
        chunk_id: Optional[str] = None,
    ) -> Citation:
        """Create citation."""
        session = self.get_session()
        try:
            citation = Citation(
                extraction_id=extraction_id,
                document_id=document_id,
                citation_text=citation_text,
                page_number=page_number,
                section_title=section_title,
                relevance_score=relevance_score,
                chunk_id=chunk_id,
            )
            session.add(citation)
            session.commit()
            session.refresh(citation)
            return citation
        finally:
            session.close()

    def get_citations_for_extraction(self, extraction_id: str) -> List[Citation]:
        """Get all citations for extraction."""
        session = self.get_session()
        try:
            return session.query(Citation).filter(
                Citation.extraction_id == extraction_id
            ).order_by(Citation.relevance_score.desc()).all()
        finally:
            session.close()

    # ==================== REVIEW STATE OPERATIONS ====================

    def create_review_state(
        self,
        project_id: str,
        extraction_id: str,
        ai_value: Optional[str] = None,
    ) -> ReviewState:
        """Create review state."""
        session = self.get_session()
        try:
            review = ReviewState(
                project_id=project_id,
                extraction_id=extraction_id,
                ai_value=ai_value,
                status=ExtractionStatus.PENDING,
            )
            session.add(review)
            session.commit()
            session.refresh(review)
            return review
        finally:
            session.close()

    def get_review_state(self, review_id: str) -> Optional[ReviewState]:
        """Get review state."""
        session = self.get_session()
        try:
            return session.query(ReviewState).filter(ReviewState.id == review_id).first()
        finally:
            session.close()

    def update_review_state(
        self,
        review_id: str,
        **kwargs
    ) -> Optional[ReviewState]:
        """Update review state."""
        session = self.get_session()
        try:
            review = session.query(ReviewState).filter(ReviewState.id == review_id).first()
            if review:
                for key, value in kwargs.items():
                    if hasattr(review, key):
                        setattr(review, key, value)
                session.commit()
                session.refresh(review)
            return review
        finally:
            session.close()

    def list_pending_reviews(self, project_id: str) -> List[ReviewState]:
        """Get pending reviews for project."""
        session = self.get_session()
        try:
            return session.query(ReviewState).filter(
                and_(
                    ReviewState.project_id == project_id,
                    ReviewState.status == ExtractionStatus.PENDING,
                )
            ).all()
        finally:
            session.close()

    def list_reviews_by_project(self, project_id: str) -> List[ReviewState]:
        """Get all reviews for project."""
        session = self.get_session()
        try:
            return session.query(ReviewState).filter(
                ReviewState.project_id == project_id
            ).all()
        finally:
            session.close()

    # ==================== TASK OPERATIONS ====================

    def create_task(
        self,
        task_type: str,
        project_id: Optional[str] = None,
    ) -> Task:
        """Create async task."""
        session = self.get_session()
        try:
            task = Task(
                task_type=task_type,
                project_id=project_id,
                status=TaskStatus.QUEUED,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
        finally:
            session.close()

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        session = self.get_session()
        try:
            return session.query(Task).filter(Task.id == task_id).first()
        finally:
            session.close()

    def update_task(
        self,
        task_id: str,
        **kwargs
    ) -> Optional[Task]:
        """Update task."""
        session = self.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                session.commit()
                session.refresh(task)
            return task
        finally:
            session.close()

    # ==================== EVALUATION OPERATIONS ====================

    def create_evaluation(
        self,
        project_id: str,
        document_id: str,
        field_name: str,
        ai_value: Optional[str],
        human_value: Optional[str],
        match_score: float,
        normalized_match: bool = False,
        notes: Optional[str] = None,
    ) -> EvaluationResult:
        """Create evaluation result."""
        session = self.get_session()
        try:
            evaluation = EvaluationResult(
                project_id=project_id,
                document_id=document_id,
                field_name=field_name,
                ai_value=ai_value,
                human_value=human_value,
                match_score=match_score,
                normalized_match=normalized_match,
                notes=notes,
            )
            session.add(evaluation)
            session.commit()
            session.refresh(evaluation)
            return evaluation
        finally:
            session.close()

    def list_evaluations(
        self,
        project_id: str,
        document_id: Optional[str] = None,
    ) -> List[EvaluationResult]:
        """List evaluations."""
        session = self.get_session()
        try:
            query = session.query(EvaluationResult).filter(
                EvaluationResult.project_id == project_id
            )
            if document_id:
                query = query.filter(EvaluationResult.document_id == document_id)
            return query.all()
        finally:
            session.close()

    def get_evaluation_metrics(self, project_id: str) -> Dict[str, Any]:
        """Calculate evaluation metrics for project."""
        session = self.get_session()
        try:
            evaluations = session.query(EvaluationResult).filter(
                EvaluationResult.project_id == project_id
            ).all()
            
            if not evaluations:
                return {
                    'total_fields': 0,
                    'matched_fields': 0,
                    'field_accuracy': 0.0,
                    'average_confidence': 0.0,
                    'coverage_percentage': 0.0,
                }
            
            total = len(evaluations)
            matched = sum(1 for e in evaluations if e.match_score > 0.8)
            accuracy = matched / total if total > 0 else 0.0
            avg_confidence = sum(e.match_score for e in evaluations) / total if total > 0 else 0.0
            
            return {
                'total_fields': total,
                'matched_fields': matched,
                'field_accuracy': accuracy,
                'average_confidence': avg_confidence,
                'coverage_percentage': (matched / total * 100) if total > 0 else 0.0,
            }
        finally:
            session.close()

    # ==================== ANNOTATION OPERATIONS ====================

    def create_annotation(
        self,
        extraction_id: str,
        comment_text: str,
        annotated_by: str,
    ) -> Annotation:
        """Create annotation on an extraction."""
        session = self.get_session()
        try:
            annotation = Annotation(
                extraction_id=extraction_id,
                comment_text=comment_text,
                annotated_by=annotated_by,
            )
            session.add(annotation)
            session.commit()
            session.refresh(annotation)
            return annotation
        finally:
            session.close()

    def list_annotations_for_extraction(self, extraction_id: str) -> List[Annotation]:
        """List annotations for a specific extraction."""
        session = self.get_session()
        try:
            return session.query(Annotation).filter(
                Annotation.extraction_id == extraction_id
            ).order_by(Annotation.created_at.desc()).all()
        finally:
            session.close()

    def list_annotations_by_project(self, project_id: str) -> List[Annotation]:
        """List all annotations for a project via extraction results."""
        session = self.get_session()
        try:
            return session.query(Annotation).join(
                ExtractionResult, Annotation.extraction_id == ExtractionResult.id
            ).filter(
                ExtractionResult.project_id == project_id
            ).order_by(Annotation.created_at.desc()).all()
        finally:
            session.close()

    def update_annotation(self, annotation_id: str, comment_text: str) -> Optional[Annotation]:
        """Update an annotation comment."""
        session = self.get_session()
        try:
            annotation = session.query(Annotation).filter(Annotation.id == annotation_id).first()
            if annotation:
                annotation.comment_text = comment_text
                annotation.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(annotation)
            return annotation
        finally:
            session.close()

    def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation."""
        session = self.get_session()
        try:
            annotation = session.query(Annotation).filter(Annotation.id == annotation_id).first()
            if annotation:
                session.delete(annotation)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== BULK / RE-EXTRACTION OPERATIONS ====================

    def delete_extractions_for_project(self, project_id: str) -> int:
        """Delete all extractions, citations, review states for a project (for re-extraction)."""
        session = self.get_session()
        try:
            # Delete in FK order: annotations -> citations -> review_states -> extractions
            extraction_ids = [
                e.id for e in session.query(ExtractionResult.id).filter(
                    ExtractionResult.project_id == project_id
                ).all()
            ]
            if not extraction_ids:
                return 0

            session.query(Annotation).filter(
                Annotation.extraction_id.in_(extraction_ids)
            ).delete(synchronize_session=False)

            session.query(Citation).filter(
                Citation.extraction_id.in_(extraction_ids)
            ).delete(synchronize_session=False)

            session.query(ReviewState).filter(
                ReviewState.extraction_id.in_(extraction_ids)
            ).delete(synchronize_session=False)

            count = session.query(ExtractionResult).filter(
                ExtractionResult.project_id == project_id
            ).delete(synchronize_session=False)

            session.commit()
            return count
        except Exception as e:
            logger.error(f"Error deleting extractions for project {project_id}: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
