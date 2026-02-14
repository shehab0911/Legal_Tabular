"""
API endpoint tests using FastAPI TestClient.
"""
import os
import sys
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Override DATABASE_URL before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_legal_review.db"

from fastapi.testclient import TestClient
from app import app


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up test database after each test."""
    yield
    db_path = "./test_legal_review.db"
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestProjectEndpoints:
    def test_create_project(self, client):
        resp = client.post("/projects", json={
            "name": "Test Project",
            "description": "A test project"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_get_project(self, client):
        create_resp = client.post("/projects", json={"name": "Test"})
        project_id = create_resp.json()["id"]

        resp = client.get(f"/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    def test_get_nonexistent_project(self, client):
        resp = client.get("/projects/nonexistent")
        assert resp.status_code in (400, 404)

    def test_list_projects(self, client):
        client.post("/projects", json={"name": "P1"})
        client.post("/projects", json={"name": "P2"})
        resp = client.get("/projects")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_update_project(self, client):
        create_resp = client.post("/projects", json={"name": "Old"})
        project_id = create_resp.json()["id"]
        resp = client.put(f"/projects/{project_id}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_delete_project(self, client):
        create_resp = client.post("/projects", json={"name": "ToDelete"})
        project_id = create_resp.json()["id"]
        resp = client.delete(f"/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"


class TestFieldTemplateEndpoints:
    def test_create_template(self, client):
        resp = client.post("/field-templates", json={
            "name": "Standard",
            "description": "Standard template",
            "fields": [
                {"name": "parties", "display_name": "Parties", "field_type": "TEXT", "description": "Parties"}
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Standard"

    def test_list_templates(self, client):
        client.post("/field-templates", json={
            "name": "T1", "fields": [{"name": "f1", "display_name": "F1", "field_type": "TEXT"}]
        })
        resp = client.get("/field-templates")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_update_template(self, client):
        create_resp = client.post("/field-templates", json={
            "name": "Original",
            "fields": [{"name": "f1", "display_name": "F1", "field_type": "TEXT"}]
        })
        template_id = create_resp.json()["id"]
        resp = client.put(f"/field-templates/{template_id}", json={
            "name": "Updated",
            "fields": [
                {"name": "f1", "display_name": "F1", "field_type": "TEXT"},
                {"name": "f2", "display_name": "F2", "field_type": "DATE"}
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["version"] == 2


class TestDocumentUploadEndpoint:
    def test_upload_txt_document(self, client):
        # Create project first
        project_resp = client.post("/projects", json={"name": "Upload Test"})
        project_id = project_resp.json()["id"]

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test legal agreement.\nBetween Party A and Party B.")
            f.flush()
            try:
                with open(f.name, 'rb') as upload_file:
                    resp = client.post(
                        f"/projects/{project_id}/documents/upload",
                        files={"file": ("test_agreement.txt", upload_file, "text/plain")}
                    )
                assert resp.status_code == 200
                data = resp.json()
                assert data["filename"] == "test_agreement.txt"
                assert data["status"] in ("INDEXED", "UPLOADED")
            finally:
                os.unlink(f.name)

    def test_list_documents(self, client):
        project_resp = client.post("/projects", json={"name": "Doc List Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/documents")
        assert resp.status_code == 200


class TestComparisonTableEndpoints:
    def test_get_empty_table(self, client):
        project_resp = client.post("/projects", json={"name": "Table Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/table")
        assert resp.status_code == 200
        assert resp.json()["row_count"] == 0

    def test_export_csv(self, client):
        project_resp = client.post("/projects", json={"name": "CSV Test"})
        project_id = project_resp.json()["id"]
        resp = client.post(f"/projects/{project_id}/table/export-csv")
        assert resp.status_code == 200
        assert resp.json()["format"] == "csv"

    def test_export_excel(self, client):
        project_resp = client.post("/projects", json={"name": "Excel Test"})
        project_id = project_resp.json()["id"]
        resp = client.post(f"/projects/{project_id}/table/export-excel")
        assert resp.status_code == 200
        assert resp.json()["format"] == "xlsx"


class TestDiffEndpoint:
    def test_get_diff_empty(self, client):
        project_resp = client.post("/projects", json={"name": "Diff Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/diff")
        assert resp.status_code == 200
        assert resp.json()["summary"]["total_fields"] == 0


class TestAnnotationEndpoints:
    def test_list_project_annotations_empty(self, client):
        project_resp = client.post("/projects", json={"name": "Ann Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/annotations")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestReviewEndpoints:
    def test_get_pending_reviews_empty(self, client):
        project_resp = client.post("/projects", json={"name": "Review Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/reviews/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestEvaluationEndpoints:
    def test_get_evaluation_report(self, client):
        project_resp = client.post("/projects", json={"name": "Eval Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/evaluation-report")
        assert resp.status_code == 200

    def test_get_extractions_empty(self, client):
        project_resp = client.post("/projects", json={"name": "Ext Test"})
        project_id = project_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/extractions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestTaskEndpoint:
    def test_get_nonexistent_task(self, client):
        resp = client.get("/tasks/nonexistent")
        assert resp.status_code in (400, 404)
