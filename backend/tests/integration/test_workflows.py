"""
Integration tests for service orchestrator workflows.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.storage.repository import DatabaseRepository
from src.services.service_orchestrator import (
    ProjectService, DocumentService, ExtractionService,
    ReviewService, ComparisonService, EvaluationService,
    TaskService, DiffService, AnnotationService, ReExtractionService,
)
from src.models.schema import ExtractionStatus, DocumentStatus


@pytest.fixture
def repo():
    return DatabaseRepository("sqlite:///")


@pytest.fixture
def services(repo):
    return {
        'project': ProjectService(repo),
        'document': DocumentService(repo),
        'review': ReviewService(repo),
        'comparison': ComparisonService(repo),
        'evaluation': EvaluationService(repo),
        'task': TaskService(repo),
        'diff': DiffService(repo),
        'annotation': AnnotationService(repo),
        'repo': repo,
    }


class TestProjectWorkflow:
    """Tests project CRUD lifecycle."""

    def test_create_and_get_project(self, services):
        ps = services['project']
        created = ps.create_project("Test Project", "A description")
        assert created['id'] is not None
        assert created['name'] == "Test Project"

        info = ps.get_project_info(created['id'])
        assert info['name'] == "Test Project"
        assert info['document_count'] == 0

    def test_update_project(self, services):
        ps = services['project']
        created = ps.create_project("Old Name")
        updated = ps.update_project(created['id'], name="New Name")
        assert updated['name'] == "New Name"

    def test_list_projects(self, services):
        ps = services['project']
        ps.create_project("P1")
        ps.create_project("P2")
        projects = ps.list_projects()
        assert len(projects) == 2


class TestDocumentIngestion:
    """Tests document ingestion workflow."""

    def test_ingest_txt_document(self, services):
        ps = services['project']
        ds = services['document']

        project = ps.create_project("Test")

        # Create a temp text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a legal agreement between Party A and Party B.\n")
            f.write("Effective Date: January 1, 2024.\n")
            f.write("The governing law shall be the State of Delaware.\n")
            f.flush()
            try:
                result = ds.ingest_document(project['id'], "agreement.txt", f.name)
                assert result['status'] == 'INDEXED'
                assert result['chunk_count'] >= 1
                assert result['filename'] == "agreement.txt"
            finally:
                os.unlink(f.name)

    def test_ingest_html_document(self, services):
        ps = services['project']
        ds = services['document']

        project = ps.create_project("Test")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<html><body><h1>Contract</h1><p>Between Tesla and Supplier.</p></body></html>")
            f.flush()
            try:
                result = ds.ingest_document(project['id'], "contract.html", f.name)
                assert result['status'] == 'INDEXED'
            finally:
                os.unlink(f.name)

    def test_unsupported_format(self, services):
        ds = services['document']
        ps = services['project']
        project = ps.create_project("Test")
        with pytest.raises(ValueError, match="Unsupported"):
            ds.ingest_document(project['id'], "data.xlsx", "/tmp/fake.xlsx")


class TestReviewWorkflow:
    """Tests review approve/reject/edit workflow."""

    def test_approve_review(self, services):
        repo = services['repo']
        review_svc = services['review']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "parties", "TEXT", "Tesla, Inc.")
        repo.create_review_state(project.id, ext.id, "Tesla, Inc.")

        result = review_svc.update_extraction_review(
            ext.id, "CONFIRMED", reviewed_by="reviewer1"
        )
        assert result['status'] == 'CONFIRMED'

    def test_reject_review(self, services):
        repo = services['repo']
        review_svc = services['review']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "parties", "TEXT", "Wrong Value")
        repo.create_review_state(project.id, ext.id, "Wrong Value")

        result = review_svc.update_extraction_review(
            ext.id, "REJECTED", reviewer_notes="Incorrect extraction", reviewed_by="reviewer1"
        )
        assert result['status'] == 'REJECTED'

    def test_manual_edit_review(self, services):
        repo = services['repo']
        review_svc = services['review']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "parties", "TEXT", "Partial Value")
        repo.create_review_state(project.id, ext.id, "Partial Value")

        result = review_svc.update_extraction_review(
            ext.id, "MANUAL_UPDATED",
            manual_value="Corrected Full Value",
            reviewed_by="editor1"
        )
        assert result['status'] == 'MANUAL_UPDATED'
        assert result['manual_value'] == "Corrected Full Value"


class TestComparisonTable:
    """Tests comparison table generation."""

    def test_generate_comparison_table(self, services):
        repo = services['repo']
        comp = services['comparison']

        project = repo.create_project("Test")
        doc1 = repo.create_document(project.id, "doc1.pdf", "pdf", "/tmp/1.pdf", 100, "C1")
        doc2 = repo.create_document(project.id, "doc2.pdf", "pdf", "/tmp/2.pdf", 200, "C2")

        repo.create_extraction(project.id, doc1.id, "parties", "TEXT", "Tesla and A")
        repo.create_extraction(project.id, doc2.id, "parties", "TEXT", "Tesla and B")
        repo.create_extraction(project.id, doc1.id, "term", "TEXT", "5 years")
        repo.create_extraction(project.id, doc2.id, "term", "TEXT", "3 years")

        table = comp.generate_comparison_table(project.id)
        assert table['document_count'] == 2
        assert table['row_count'] == 2
        assert len(table['rows']) == 2

    def test_empty_comparison_table(self, services):
        repo = services['repo']
        comp = services['comparison']
        project = repo.create_project("Test")
        table = comp.generate_comparison_table(project.id)
        assert table['row_count'] == 0


class TestDiffService:
    """Tests diff highlighting."""

    def test_compute_diff_with_differences(self, services):
        repo = services['repo']
        diff = services['diff']

        project = repo.create_project("Test")
        doc1 = repo.create_document(project.id, "doc1.pdf", "pdf", "/tmp/1.pdf", 100, "C1")
        doc2 = repo.create_document(project.id, "doc2.pdf", "pdf", "/tmp/2.pdf", 200, "C2")

        # Same field, different values
        repo.create_extraction(project.id, doc1.id, "governing_law", "TEXT",
                               extracted_value="Delaware", normalized_value="Delaware")
        repo.create_extraction(project.id, doc2.id, "governing_law", "TEXT",
                               extracted_value="Texas", normalized_value="Texas")

        result = diff.compute_diff(project.id)
        assert result['summary']['total_fields'] == 1
        assert result['summary']['fields_with_differences'] == 1
        assert len(result['field_diffs']) == 1
        assert result['field_diffs'][0]['is_unanimous'] is False
        assert len(result['field_diffs'][0]['outliers']) > 0

    def test_compute_diff_unanimous(self, services):
        repo = services['repo']
        diff = services['diff']

        project = repo.create_project("Test")
        doc1 = repo.create_document(project.id, "doc1.pdf", "pdf", "/tmp/1.pdf", 100, "C1")
        doc2 = repo.create_document(project.id, "doc2.pdf", "pdf", "/tmp/2.pdf", 200, "C2")

        repo.create_extraction(project.id, doc1.id, "governing_law", "TEXT",
                               extracted_value="Delaware", normalized_value="Delaware")
        repo.create_extraction(project.id, doc2.id, "governing_law", "TEXT",
                               extracted_value="Delaware", normalized_value="Delaware")

        result = diff.compute_diff(project.id)
        assert result['summary']['fields_with_differences'] == 0
        assert result['field_diffs'][0]['is_unanimous'] is True


class TestAnnotationService:
    """Tests annotation CRUD."""

    def test_annotation_lifecycle(self, services):
        repo = services['repo']
        ann_svc = services['annotation']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        ext = repo.create_extraction(project.id, doc.id, "parties", "TEXT", "Tesla")

        # Create
        ann = ann_svc.create_annotation(ext.id, "Risk: high", "reviewer1")
        assert ann['comment_text'] == "Risk: high"
        assert ann['annotated_by'] == "reviewer1"

        # List
        anns = ann_svc.list_annotations_for_extraction(ext.id)
        assert len(anns) == 1

        # Update
        updated = ann_svc.update_annotation(ann['id'], "Risk: medium after review")
        assert updated['comment_text'] == "Risk: medium after review"

        # Delete
        deleted = ann_svc.delete_annotation(ann['id'])
        assert deleted is True
        assert len(ann_svc.list_annotations_for_extraction(ext.id)) == 0


class TestEvaluationWorkflow:
    """Tests evaluation and metrics."""

    def test_evaluate_extraction(self, services):
        repo = services['repo']
        eval_svc = services['evaluation']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        repo.create_extraction(project.id, doc.id, "parties", "TEXT", "Tesla, Inc.")

        result = eval_svc.evaluate_extraction(project.id, doc.id, "parties", "Tesla, Inc.")
        assert result['match_score'] == 1.0
        assert result['normalized_match'] is True

    def test_evaluation_report(self, services):
        repo = services['repo']
        eval_svc = services['evaluation']

        project = repo.create_project("Test")
        doc = repo.create_document(project.id, "t.pdf", "pdf", "/tmp/t.pdf", 100, "Content")
        repo.create_extraction(project.id, doc.id, "f1", "TEXT", "Value A")
        repo.create_extraction(project.id, doc.id, "f2", "TEXT", "Value B")

        eval_svc.evaluate_extraction(project.id, doc.id, "f1", "Value A")
        eval_svc.evaluate_extraction(project.id, doc.id, "f2", "Totally Different")

        report = eval_svc.generate_evaluation_report(project.id)
        assert report['metrics']['total_fields'] == 2
        assert report['metrics']['matched_fields'] >= 1


class TestTaskService:
    """Tests task lifecycle."""

    def test_task_lifecycle(self, services):
        task_svc = services['task']
        repo = services['repo']

        project = repo.create_project("Test")
        task = task_svc.create_task("extract", project.id)
        assert task['status'] == 'QUEUED'

        updated = task_svc.update_task_status(task['task_id'], 'PROCESSING')
        assert updated['status'] == 'PROCESSING'

        completed = task_svc.update_task_status(
            task['task_id'], 'COMPLETED', result={"extracted": 10}
        )
        assert completed['status'] == 'COMPLETED'
        assert completed['result']['extracted'] == 10
