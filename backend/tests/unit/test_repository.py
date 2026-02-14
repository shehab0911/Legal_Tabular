"""
Unit tests for DatabaseRepository - all CRUD operations.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.storage.repository import DatabaseRepository
from src.models.schema import (
    ProjectStatus, DocumentStatus, ExtractionStatus, TaskStatus, FieldType
)


@pytest.fixture
def repo():
    """Create a fresh in-memory database for each test."""
    db = DatabaseRepository("sqlite:///")
    return db


class TestProjectOperations:
    def test_create_project(self, repo):
        project = repo.create_project("Test Project", "A test project")
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.status == ProjectStatus.CREATED

    def test_get_project(self, repo):
        created = repo.create_project("Test", "Desc")
        fetched = repo.get_project(created.id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_get_nonexistent_project(self, repo):
        assert repo.get_project("nonexistent-id") is None

    def test_list_projects(self, repo):
        repo.create_project("Project 1")
        repo.create_project("Project 2")
        repo.create_project("Project 3")
        projects = repo.list_projects()
        assert len(projects) == 3

    def test_update_project(self, repo):
        project = repo.create_project("Old Name")
        updated = repo.update_project(project.id, name="New Name")
        assert updated.name == "New Name"

    def test_delete_project(self, repo):
        project = repo.create_project("To Delete")
        assert repo.delete_project(project.id) is True
        assert repo.get_project(project.id) is None

    def test_delete_nonexistent_project(self, repo):
        assert repo.delete_project("nonexistent") is False


class TestDocumentOperations:
    def test_create_document(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(
            project_id=project.id,
            filename="test.pdf",
            file_type="pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            content_text="Test content",
        )
        assert doc.id is not None
        assert doc.filename == "test.pdf"
        assert doc.status == DocumentStatus.UPLOADED

    def test_list_project_documents(self, repo):
        project = repo.create_project("Test")
        repo.create_document(project.id, "doc1.pdf", "pdf", "/tmp/1.pdf", 100, "Content 1")
        repo.create_document(project.id, "doc2.html", "html", "/tmp/2.html", 200, "Content 2")
        docs = repo.list_project_documents(project.id)
        assert len(docs) == 2

    def test_update_document_status(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "test.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        updated = repo.update_document_status(doc.id, DocumentStatus.INDEXED)
        assert updated.status == DocumentStatus.INDEXED


class TestChunkOperations:
    def test_create_chunks_bulk(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "test.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        chunks_data = [
            {"document_id": doc.id, "chunk_index": 0, "text": "Chunk 0", "page_number": 1},
            {"document_id": doc.id, "chunk_index": 1, "text": "Chunk 1", "page_number": 1},
            {"document_id": doc.id, "chunk_index": 2, "text": "Chunk 2", "page_number": 2},
        ]
        result = repo.create_chunks_bulk(chunks_data)
        assert result is True
        chunks = repo.get_document_chunks(doc.id)
        assert len(chunks) == 3


class TestFieldTemplateOperations:
    def test_create_field_template(self, repo):
        template = repo.create_field_template(
            name="Standard Template",
            fields=[{"name": "parties", "display_name": "Parties", "field_type": "TEXT"}],
            description="A standard template",
        )
        assert template.id is not None
        assert template.version == 1
        assert len(template.fields) == 1

    def test_update_field_template_versions(self, repo):
        template = repo.create_field_template("Template", [{"name": "field1"}])
        updated = repo.update_field_template(
            template.id,
            fields=[{"name": "field1"}, {"name": "field2"}],
        )
        assert updated.version == 2
        assert len(updated.fields) == 2

    def test_list_templates(self, repo):
        repo.create_field_template("T1", [])
        repo.create_field_template("T2", [])
        templates = repo.list_field_templates()
        assert len(templates) == 2


class TestExtractionOperations:
    def test_create_extraction(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        extraction = repo.create_extraction(
            project_id=project.id,
            document_id=doc.id,
            field_name="parties",
            field_type="TEXT",
            extracted_value="Tesla and Panasonic",
            confidence_score=0.92,
        )
        assert extraction.id is not None
        assert extraction.extracted_value == "Tesla and Panasonic"
        assert extraction.status == ExtractionStatus.EXTRACTED

    def test_list_extractions_by_project(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        repo.create_extraction(project.id, doc.id, "field1", "TEXT", "val1", confidence_score=0.8)
        repo.create_extraction(project.id, doc.id, "field2", "DATE", "val2", confidence_score=0.9)
        extractions = repo.list_extractions_by_project(project.id)
        assert len(extractions) == 2

    def test_update_extraction(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "field1", "TEXT", "old_val")
        updated = repo.update_extraction(ext.id, extracted_value="new_val")
        assert updated.extracted_value == "new_val"


class TestReviewOperations:
    def test_create_review_state(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "field1", "TEXT", "val1")
        review = repo.create_review_state(project.id, ext.id, ai_value="val1")
        assert review.id is not None
        assert review.status == ExtractionStatus.PENDING

    def test_list_pending_reviews(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext1 = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ext2 = repo.create_extraction(project.id, doc.id, "f2", "TEXT", "v2")
        repo.create_review_state(project.id, ext1.id, "v1")
        repo.create_review_state(project.id, ext2.id, "v2")
        reviews = repo.list_pending_reviews(project.id)
        assert len(reviews) == 2

    def test_update_review_with_reviewer(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        review = repo.create_review_state(project.id, ext.id, "v1")
        updated = repo.update_review_state(
            review.id,
            status=ExtractionStatus.CONFIRMED,
            reviewed_by="john.doe",
        )
        assert updated.status == ExtractionStatus.CONFIRMED
        assert updated.reviewed_by == "john.doe"


class TestAnnotationOperations:
    def test_create_annotation(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ann = repo.create_annotation(ext.id, "Risk: high liability", "reviewer1")
        assert ann.id is not None
        assert ann.comment_text == "Risk: high liability"
        assert ann.annotated_by == "reviewer1"

    def test_list_annotations_for_extraction(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        repo.create_annotation(ext.id, "Comment 1", "user1")
        repo.create_annotation(ext.id, "Comment 2", "user2")
        anns = repo.list_annotations_for_extraction(ext.id)
        assert len(anns) == 2

    def test_update_annotation(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ann = repo.create_annotation(ext.id, "Old comment", "user1")
        updated = repo.update_annotation(ann.id, "Updated comment")
        assert updated.comment_text == "Updated comment"

    def test_delete_annotation(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ann = repo.create_annotation(ext.id, "To delete", "user1")
        assert repo.delete_annotation(ann.id) is True
        assert repo.delete_annotation(ann.id) is False  # Already deleted

    def test_list_annotations_by_project(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext1 = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ext2 = repo.create_extraction(project.id, doc.id, "f2", "TEXT", "v2")
        repo.create_annotation(ext1.id, "Ann 1", "user1")
        repo.create_annotation(ext2.id, "Ann 2", "user2")
        anns = repo.list_annotations_by_project(project.id)
        assert len(anns) == 2


class TestTaskOperations:
    def test_create_task(self, repo):
        project = repo.create_project("Test")
        task = repo.create_task("extract", project.id)
        assert task.id is not None
        assert task.status == TaskStatus.QUEUED

    def test_update_task(self, repo):
        project = repo.create_project("Test")
        task = repo.create_task("extract", project.id)
        updated = repo.update_task(task.id, status=TaskStatus.COMPLETED, result={"count": 5})
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"count": 5}


class TestEvaluationOperations:
    def test_create_evaluation(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ev = repo.create_evaluation(
            project.id, doc.id, "parties",
            ai_value="Tesla", human_value="Tesla, Inc.",
            match_score=0.85, normalized_match=True,
        )
        assert ev.id is not None
        assert ev.match_score == 0.85

    def test_get_evaluation_metrics(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        repo.create_evaluation(project.id, doc.id, "f1", "a", "b", 0.9, True)
        repo.create_evaluation(project.id, doc.id, "f2", "c", "d", 0.5, False)
        metrics = repo.get_evaluation_metrics(project.id)
        assert metrics['total_fields'] == 2
        assert metrics['matched_fields'] == 1
        assert metrics['field_accuracy'] == 0.5

    def test_empty_evaluation_metrics(self, repo):
        project = repo.create_project("Test")
        metrics = repo.get_evaluation_metrics(project.id)
        assert metrics['total_fields'] == 0
        assert metrics['field_accuracy'] == 0.0


class TestBulkOperations:
    def test_delete_extractions_for_project(self, repo):
        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext1 = repo.create_extraction(project.id, doc.id, "f1", "TEXT", "v1")
        ext2 = repo.create_extraction(project.id, doc.id, "f2", "TEXT", "v2")
        repo.create_review_state(project.id, ext1.id, "v1")
        repo.create_annotation(ext1.id, "Ann", "user")
        repo.create_citation(ext1.id, doc.id, "Citation text", relevance_score=0.9)

        count = repo.delete_extractions_for_project(project.id)
        assert count == 2
        assert len(repo.list_extractions_by_project(project.id)) == 0
