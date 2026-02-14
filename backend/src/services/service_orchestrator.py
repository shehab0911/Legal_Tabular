"""
Business logic services for Legal Tabular Review.
Orchestrates document ingestion, extraction, review, evaluation,
diff highlighting, and annotation workflows.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
from difflib import SequenceMatcher

from src.storage.repository import DatabaseRepository
from src.services.document_parser import DocumentParser, DocumentChunker
from src.services.field_extractor import FieldExtractor
from src.models.schema import (
    ProjectStatus, DocumentStatus, ExtractionStatus, FieldType, TaskStatus
)

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project management."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        field_template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create new project."""
        project = self.repo.create_project(name, description, field_template_id)
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'document_count': 0,
            'extraction_count': 0,
            'field_template_id': project.field_template_id,
        }

    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """Get project information with stats."""
        project = self.repo.get_project(project_id)
        if not project:
            return None

        documents = self.repo.list_project_documents(project_id)
        extractions = self.repo.list_extractions_by_project(project_id)
        
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'document_count': len(documents),
            'extraction_count': len(extractions),
            'field_template_id': project.field_template_id,
        }

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        field_template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update project."""
        update_data = {}
        if name:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if field_template_id:
            update_data['field_template_id'] = field_template_id

        project = self.repo.update_project(project_id, **update_data)
        if not project:
            return None
        
        documents = self.repo.list_project_documents(project_id)
        extractions = self.repo.list_extractions_by_project(project_id)

        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'document_count': len(documents),
            'extraction_count': len(extractions),
            'field_template_id': project.field_template_id,
        }

    def list_projects(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List all projects."""
        projects = self.repo.list_projects(skip, limit)
        return [
            {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'status': p.status.value,
                'created_at': p.created_at.isoformat(),
            }
            for p in projects
        ]


class DocumentService:
    """Service for document management and parsing."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo
        self.parser = DocumentParser()
        self.chunker = DocumentChunker()

    def ingest_document(
        self,
        project_id: str,
        filename: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Ingest and parse document."""
        try:
            logger.info(f"Starting ingestion for {filename} in project {project_id}")
            
            # Validate file format
            if not self.parser.is_supported(filename):
                raise ValueError(f"Unsupported file format: {filename}")

            # Get file type
            _, ext = filename.rsplit('.', 1)
            file_type = ext.lower()

            # Parse document
            try:
                content, metadata = self.parser.parse(file_path, file_type)
            except Exception as parse_error:
                logger.error(f"Error parsing document {filename}: {str(parse_error)}")
                # Create document with ERROR status
                import os
                file_size = os.path.getsize(file_path)
                try:
                    document = self.repo.create_document(
                        project_id=project_id,
                        filename=filename,
                        file_type=file_type,
                        file_path=file_path,
                        file_size=file_size,
                        content_text="",
                        parsed_metadata={"error": str(parse_error)},
                    )
                    self.repo.update_document_status(document.id, DocumentStatus.ERROR)
                    return {
                        'id': document.id,
                        'project_id': document.project_id,
                        'filename': document.filename,
                        'file_type': document.file_type,
                        'file_size': document.file_size,
                        'status': DocumentStatus.ERROR.value,
                        'chunk_count': 0,
                        'created_at': document.created_at.isoformat(),
                        'updated_at': document.updated_at.isoformat(),
                        'error': str(parse_error)
                    }
                except Exception as db_error:
                    logger.error(f"DB error while saving failed doc {filename}: {str(db_error)}")
                    raise db_error

            # Get file size
            import os
            file_size = os.path.getsize(file_path)

            # Create document record
            document = self.repo.create_document(
                project_id=project_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                content_text=content,
                parsed_metadata=metadata,
            )

            # Create chunks
            chunks_data = self.chunker.chunk(content, metadata)
            
            # Prepare chunks for bulk insert
            bulk_chunks = []
            for i, chunk_data in enumerate(chunks_data):
                bulk_chunks.append({
                    'document_id': document.id,
                    'chunk_index': i,
                    'text': chunk_data['text'],
                    'page_number': chunk_data.get('page_number'),
                    'section_title': chunk_data.get('section'),
                })
            
            # Bulk create chunks
            if bulk_chunks:
                self.repo.create_chunks_bulk(bulk_chunks)

            # Update document status
            self.repo.update_document_status(document.id, DocumentStatus.INDEXED)

            logger.info(f"Successfully ingested {filename}")
            return {
                'id': document.id,
                'project_id': document.project_id,
                'filename': document.filename,
                'file_type': document.file_type,
                'file_size': document.file_size,
                'status': DocumentStatus.INDEXED.value,
                'chunk_count': len(chunks_data),
                'created_at': document.created_at.isoformat(),
                'updated_at': document.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Critical error ingesting document {filename}: {str(e)}")
            # Attempt to record failure if possible, but re-raise to notify caller
            raise

    def list_project_documents(self, project_id: str) -> List[Dict[str, Any]]:
        """List documents in project."""
        documents = self.repo.list_project_documents(project_id)
        return [
            {
                'id': d.id,
                'filename': d.filename,
                'file_type': d.file_type,
                'file_size': d.file_size,
                'status': d.status.value,
                'created_at': d.created_at.isoformat(),
            }
            for d in documents
        ]


class ExtractionService:
    """Service for field extraction and normalization."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo
        self.extractor = FieldExtractor()

    def extract_fields_for_document(
        self,
        project_id: str,
        document_id: str,
        field_definitions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract fields from document."""
        try:
            # Get document and chunks
            document = self.repo.get_document(document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            chunks = self.repo.get_document_chunks(document_id)
            chunks_data = [
                {
                    'text': c.text,
                    'page_number': c.page_number,
                    'section': c.section_title or 'Main',
                }
                for c in chunks
            ]

            # Extract fields
            extraction_results = self.extractor.extract_fields(
                document_text=document.content_text,
                document_chunks=chunks_data,
                field_definitions=field_definitions,
                document_id=document_id,
            )

            # Store extraction results
            stored_results = []
            for result in extraction_results:
                extraction = self.repo.create_extraction(
                    project_id=project_id,
                    document_id=document_id,
                    field_name=result['field_name'],
                    field_type=result['field_type'],
                    extracted_value=result.get('extracted_value'),
                    raw_text=result.get('raw_text'),
                    normalized_value=result.get('normalized_value'),
                    confidence_score=result.get('confidence_score', 0.0),
                    extra_metadata=result.get('extraction_metadata', {}),
                )

                # Store citations
                for citation_data in result.get('citations', []):
                    self.repo.create_citation(
                        extraction_id=extraction.id,
                        document_id=document_id,
                        citation_text=citation_data['citation_text'],
                        page_number=citation_data.get('page_number'),
                        section_title=citation_data.get('section_title'),
                        relevance_score=citation_data.get('relevance_score', 0.0),
                    )

                # Create review state
                self.repo.create_review_state(
                    project_id=project_id,
                    extraction_id=extraction.id,
                    ai_value=extraction.extracted_value,
                )

                stored_results.append({
                    'id': extraction.id,
                    'field_name': extraction.field_name,
                    'extracted_value': extraction.extracted_value,
                    'normalized_value': extraction.normalized_value,
                    'confidence_score': extraction.confidence_score,
                    'status': extraction.status.value,
                })

            # Update document status
            self.repo.update_document_status(document_id, DocumentStatus.EXTRACTED)

            return stored_results

        except Exception as e:
            logger.error(f"Error extracting fields: {str(e)}")
            raise

    def extract_all_documents(
        self,
        project_id: str,
        field_definitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract fields from all documents in project."""
        documents = self.repo.list_project_documents(project_id)
        
        total_extracted = 0
        for document in documents:
            results = self.extract_fields_for_document(
                project_id=project_id,
                document_id=document.id,
                field_definitions=field_definitions,
            )
            total_extracted += len(results)

        return {
            'project_id': project_id,
            'documents_processed': len(documents),
            'total_fields_extracted': total_extracted,
        }


class ReviewService:
    """Service for review workflow and manual edits."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def update_extraction_review(
        self,
        extraction_id: str,
        status: str,
        manual_value: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update review state for extraction."""
        try:
            # Get extraction
            extraction = self.repo.get_extraction(extraction_id)
            if not extraction:
                raise ValueError(f"Extraction not found: {extraction_id}")

            # Get review state
            review_states = self.repo.list_pending_reviews(extraction.project_id)
            review_state = next(
                (r for r in review_states if r.extraction_id == extraction_id),
                None
            )

            if not review_state:
                # Create if doesn't exist
                review_state = self.repo.create_review_state(
                    extraction.project_id,
                    extraction_id,
                    extraction.extracted_value,
                )

            # Update review state
            update_data = {
                'status': ExtractionStatus[status],
                'manual_value': manual_value,
                'reviewer_notes': reviewer_notes,
                'reviewed_by': reviewed_by,
                'reviewed_at': datetime.now(timezone.utc),
            }

            review_state = self.repo.update_review_state(
                review_state.id,
                **update_data
            )

            # Update extraction status
            self.repo.update_extraction(
                extraction_id,
                status=ExtractionStatus[status],
            )

            return {
                'id': review_state.id,
                'extraction_id': extraction_id,
                'status': review_state.status.value,
                'ai_value': review_state.ai_value,
                'manual_value': review_state.manual_value,
                'reviewer_notes': review_state.reviewer_notes,
                'reviewed_at': review_state.reviewed_at.isoformat() if review_state.reviewed_at else None,
            }

        except Exception as e:
            logger.error(f"Error updating review: {str(e)}")
            raise

    def get_pending_reviews(self, project_id: str) -> List[Dict[str, Any]]:
        """Get pending reviews for project."""
        reviews = self.repo.list_pending_reviews(project_id)
        return [
            {
                'id': r.id,
                'extraction_id': r.extraction_id,
                'status': r.status.value,
                'ai_value': r.ai_value,
                'confidence_score': r.confidence_score,
            }
            for r in reviews
        ]


class ComparisonService:
    """Service for generating comparison tables."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def generate_comparison_table(self, project_id: str) -> Dict[str, Any]:
        """Generate comparison table for all documents."""
        try:
            documents = self.repo.list_project_documents(project_id)
            extractions = self.repo.list_extractions_by_project(project_id)

            if not documents or not extractions:
                return {
                    'project_id': project_id,
                    'document_count': len(documents),
                    'row_count': 0,
                    'rows': [],
                    'generation_timestamp': datetime.now(timezone.utc).isoformat(),
                }

            # Group extractions by field
            field_groups = {}
            for extraction in extractions:
                # Convert field name to Title Case for display (e.g. "audit_policy" -> "Audit Policy")
                raw_field_name = extraction.field_name
                # If the field name has underscores, replace them with spaces. 
                # Then convert to Title Case.
                if raw_field_name:
                    field_name = raw_field_name.replace('_', ' ').title()
                else:
                    field_name = "Unknown Field"
                
                if field_name not in field_groups:
                    field_groups[field_name] = {
                        'field_name': field_name,
                        'field_type': extraction.field_type,
                        'results': {},
                    }
                    
                doc_id = extraction.document_id
                # Top citations for this extraction (limit to 3, sorted by relevance)
                citations = []
                try:
                    citation_rows = self.repo.get_citations_for_extraction(extraction.id)[:3]
                    citations = [
                        {
                            'citation_text': c.citation_text,
                            'page_number': c.page_number,
                            'section_title': c.section_title,
                            'relevance_score': c.relevance_score,
                        }
                        for c in citation_rows
                    ]
                except Exception:
                    citations = []

                field_groups[field_name]['results'][doc_id] = {
                    'id': extraction.id,
                    'extracted_value': extraction.extracted_value,
                    'normalized_value': extraction.normalized_value,
                    'confidence_score': extraction.confidence_score,
                    'status': extraction.status.value,
                    'citations': citations,
                }

            # Create rows
            rows = [
                {
                    'field_name': group['field_name'],
                    'field_type': group['field_type'],
                    'document_results': {
                        doc.id: group['results'].get(doc.id, {
                            'extracted_value': 'N/A',
                            'confidence_score': 0.0,
                        })
                        for doc in documents
                    }
                }
                for group in field_groups.values()
            ]

            return {
                'project_id': project_id,
                'document_count': len(documents),
                'row_count': len(rows),
                'documents': [
                    {
                        'id': d.id,
                        'filename': d.filename,
                        'file_type': d.file_type,
                    }
                    for d in documents
                ],
                'rows': rows,
                'generation_timestamp': datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating comparison table: {str(e)}")
            raise


class EvaluationService:
    """Service for evaluating extraction quality."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def evaluate_extraction(
        self,
        project_id: str,
        document_id: str,
        field_name: str,
        human_value: Optional[str],
    ) -> Dict[str, Any]:
        """Evaluate extraction against human reference."""
        try:
            # Get AI extraction
            extractions = self.repo.list_extractions_by_project(
                project_id,
                field_name=field_name,
                document_id=document_id,
            )

            if not extractions:
                return {'status': 'extraction_not_found'}

            extraction = extractions[0]
            ai_value = extraction.normalized_value or extraction.extracted_value

            # Calculate match score
            match_score = self._calculate_match_score(ai_value, human_value)
            normalized_match = match_score > 0.8

            # Store evaluation
            evaluation = self.repo.create_evaluation(
                project_id=project_id,
                document_id=document_id,
                field_name=field_name,
                ai_value=ai_value,
                human_value=human_value,
                match_score=match_score,
                normalized_match=normalized_match,
            )

            return {
                'id': evaluation.id,
                'field_name': field_name,
                'ai_value': ai_value,
                'human_value': human_value,
                'match_score': match_score,
                'normalized_match': normalized_match,
            }

        except Exception as e:
            logger.error(f"Error evaluating extraction: {str(e)}")
            raise

    def evaluate_project_reviews(self, project_id: str) -> Dict[str, Any]:
        """Evaluate all reviewed extractions in the project."""
        try:
            reviews = self.repo.list_reviews_by_project(project_id)
            extractions = self.repo.list_extractions_by_project(project_id)
            
            # Map extractions by ID
            extraction_map = {e.id: e for e in extractions}
            
            count = 0
            for review in reviews:
                if review.status == ExtractionStatus.PENDING:
                    continue
                
                extraction = extraction_map.get(review.extraction_id)
                if not extraction:
                    continue
                
                human_value = None
                if review.status == ExtractionStatus.CONFIRMED:
                    # If confirmed, the human agrees with the AI (or the current value)
                    # Use extraction.normalized_value or extraction.extracted_value
                    human_value = extraction.normalized_value or extraction.extracted_value
                elif review.status == ExtractionStatus.MANUAL_UPDATED:
                    human_value = review.manual_value
                else:
                    # Skip REJECTED or others for now unless we have a clear human value
                    continue
                
                self.evaluate_extraction(
                    project_id=project_id,
                    document_id=extraction.document_id,
                    field_name=extraction.field_name,
                    human_value=human_value
                )
                count += 1
                
            return self.generate_evaluation_report(project_id)
            
        except Exception as e:
            logger.error(f"Error evaluating project reviews: {str(e)}")
            raise

    @staticmethod
    def _calculate_match_score(ai_value: Optional[str], human_value: Optional[str]) -> float:
        """Calculate similarity score between AI and human values."""
        if not ai_value or not human_value:
            return 0.0 if ai_value != human_value else 1.0

        # Simple string similarity
        ai_norm = str(ai_value).lower().strip()
        human_norm = str(human_value).lower().strip()

        if ai_norm == human_norm:
            return 1.0

        # Levenshtein distance
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, ai_norm, human_norm).ratio()
        return ratio

    def generate_evaluation_report(self, project_id: str) -> Dict[str, Any]:
        """Generate evaluation report for project."""
        try:
            metrics = self.repo.get_evaluation_metrics(project_id)
            evaluations = self.repo.list_evaluations(project_id)

            field_results = {}
            for evaluation in evaluations:
                field_name = evaluation.field_name
                if field_name not in field_results:
                    field_results[field_name] = {
                        'field_name': field_name,
                        'total': 0,
                        'matched': 0,
                        'accuracy': 0.0,
                    }

                field_results[field_name]['total'] += 1
                if evaluation.match_score > 0.8:
                    field_results[field_name]['matched'] += 1

            # Calculate accuracy per field
            for field_name in field_results:
                total = field_results[field_name]['total']
                matched = field_results[field_name]['matched']
                field_results[field_name]['accuracy'] = (
                    matched / total if total > 0 else 0.0
                )

            return {
                'project_id': project_id,
                'metrics': metrics,
                'field_results': list(field_results.values()),
                'summary': f"Extracted {metrics['total_fields']} fields with "
                          f"{metrics['field_accuracy']:.1%} accuracy",
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating evaluation report: {str(e)}")
            raise


class TaskService:
    """Service for managing async tasks."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def create_task(self, task_type: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Create async task."""
        task = self.repo.create_task(task_type, project_id)
        return {
            'task_id': task.id,
            'task_type': task.task_type,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
        }

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        task = self.repo.get_task(task_id)
        if not task:
            return None

        return {
            'task_id': task.id,
            'task_type': task.task_type,
            'project_id': task.project_id,
            'status': task.status.value,
            'result': task.result,
            'error_message': task.error_message,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        }

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update task status."""
        update_data = {'status': TaskStatus[status]}
        if result:
            update_data['result'] = result
        if error_message:
            update_data['error_message'] = error_message

        task = self.repo.update_task(task_id, **update_data)
        return self.get_task_status(task_id)


class DiffService:
    """Service for computing cross-document diff highlighting."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def compute_diff(self, project_id: str) -> Dict[str, Any]:
        """
        Compute differences across documents for each field.

        For each field, groups documents by their extracted value and
        identifies outlier values (values that differ from the majority).
        """
        documents = self.repo.list_project_documents(project_id)
        extractions = self.repo.list_extractions_by_project(project_id)

        if not documents or not extractions:
            return {
                'project_id': project_id,
                'field_diffs': [],
                'summary': {'total_fields': 0, 'fields_with_differences': 0},
            }

        # Group extractions by field
        field_map: Dict[str, List] = defaultdict(list)
        for ext in extractions:
            field_key = ext.field_name.replace('_', ' ').title()
            field_map[field_key].append(ext)

        doc_name_map = {d.id: d.filename for d in documents}
        field_diffs = []
        fields_with_diff = 0

        for field_name, field_exts in field_map.items():
            # Group by normalized or extracted value
            value_groups: Dict[str, List[str]] = defaultdict(list)
            doc_values = {}
            for ext in field_exts:
                val = (ext.normalized_value or ext.extracted_value or "N/A").strip()
                doc_label = doc_name_map.get(ext.document_id, ext.document_id)
                value_groups[val].append(doc_label)
                doc_values[doc_label] = {
                    'value': val,
                    'confidence': ext.confidence_score,
                    'document_id': ext.document_id,
                }

            # Determine majority value
            majority_value = max(value_groups.keys(), key=lambda v: len(value_groups[v]))
            majority_count = len(value_groups[majority_value])
            total_docs = sum(len(docs) for docs in value_groups.values())
            is_unanimous = len(value_groups) == 1

            # Build outlier list
            outliers = []
            if not is_unanimous:
                fields_with_diff += 1
                for val, docs in value_groups.items():
                    if val != majority_value:
                        for doc_label in docs:
                            outliers.append({
                                'document': doc_label,
                                'value': val,
                                'document_id': doc_values[doc_label]['document_id'],
                                'confidence': doc_values[doc_label]['confidence'],
                            })

            # Pairwise similarity matrix
            all_values = list(doc_values.keys())
            similarity_pairs = []
            for i in range(len(all_values)):
                for j in range(i + 1, len(all_values)):
                    v1 = doc_values[all_values[i]]['value']
                    v2 = doc_values[all_values[j]]['value']
                    sim = SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
                    similarity_pairs.append({
                        'doc_a': all_values[i],
                        'doc_b': all_values[j],
                        'similarity': round(sim, 3),
                    })

            field_diffs.append({
                'field_name': field_name,
                'is_unanimous': is_unanimous,
                'majority_value': majority_value,
                'majority_count': majority_count,
                'total_documents': total_docs,
                'unique_values': len(value_groups),
                'value_groups': {v: docs for v, docs in value_groups.items()},
                'outliers': outliers,
                'document_values': doc_values,
                'similarity_pairs': similarity_pairs,
            })

        return {
            'project_id': project_id,
            'field_diffs': field_diffs,
            'summary': {
                'total_fields': len(field_diffs),
                'fields_with_differences': fields_with_diff,
                'unanimity_rate': round(
                    (len(field_diffs) - fields_with_diff) / max(1, len(field_diffs)), 3
                ),
            },
        }


class AnnotationService:
    """Service for managing annotations on extracted fields."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def create_annotation(
        self,
        extraction_id: str,
        comment_text: str,
        annotated_by: str,
    ) -> Dict[str, Any]:
        """Create a new annotation."""
        annotation = self.repo.create_annotation(extraction_id, comment_text, annotated_by)
        return self._to_dict(annotation)

    def list_annotations_for_extraction(self, extraction_id: str) -> List[Dict[str, Any]]:
        """List all annotations for a specific extraction."""
        annotations = self.repo.list_annotations_for_extraction(extraction_id)
        return [self._to_dict(a) for a in annotations]

    def list_annotations_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List all annotations across a project."""
        annotations = self.repo.list_annotations_by_project(project_id)
        return [self._to_dict(a) for a in annotations]

    def update_annotation(self, annotation_id: str, comment_text: str) -> Dict[str, Any]:
        """Update an annotation."""
        annotation = self.repo.update_annotation(annotation_id, comment_text)
        if not annotation:
            raise ValueError(f"Annotation not found: {annotation_id}")
        return self._to_dict(annotation)

    def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation."""
        return self.repo.delete_annotation(annotation_id)

    @staticmethod
    def _to_dict(annotation) -> Dict[str, Any]:
        return {
            'id': annotation.id,
            'extraction_id': annotation.extraction_id,
            'comment_text': annotation.comment_text,
            'annotated_by': annotation.annotated_by,
            'created_at': annotation.created_at.isoformat(),
            'updated_at': annotation.updated_at.isoformat(),
        }


class ReExtractionService:
    """Service for triggering re-extraction when templates change."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo
        self.extraction_service = ExtractionService(repo)

    def re_extract_project(
        self,
        project_id: str,
        field_definitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Delete existing extractions for a project and re-extract all documents
        using the provided field definitions.
        """
        try:
            # 1. Delete old extractions + reviews + citations + annotations
            deleted_count = self.repo.delete_extractions_for_project(project_id)
            logger.info(f"Deleted {deleted_count} old extractions for project {project_id}")

            # 2. Re-extract all documents
            result = self.extraction_service.extract_all_documents(project_id, field_definitions)
            result['previous_extractions_deleted'] = deleted_count
            return result

        except Exception as e:
            logger.error(f"Error in re-extraction for project {project_id}: {str(e)}")
            raise
