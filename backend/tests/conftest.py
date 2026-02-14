"""Shared test fixtures and configuration for the Legal Tabular Review test suite."""

import os
import sys
import pytest
import tempfile

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.storage.repository import DatabaseRepository
from src.services.document_parser import DocumentParser, DocumentChunker
from src.services.field_extractor import FieldExtractor
from src.services.service_orchestrator import (
    ProjectService, DocumentService, ExtractionService,
    ReviewService, ComparisonService, EvaluationService, TaskService,
)
from src.models.schema import (
    ProjectStatus, DocumentStatus, ExtractionStatus, FieldType, TaskStatus,
)


# ---------------------------------------------------------------------------
# Default field definitions used across tests
# ---------------------------------------------------------------------------
DEFAULT_FIELDS = [
    {"name": "effective_date", "display_name": "Effective Date", "field_type": "DATE",
     "description": "The effective date of the agreement", "required": False},
    {"name": "parties", "display_name": "Parties", "field_type": "TEXT",
     "description": "The parties involved in the agreement", "required": False},
    {"name": "term", "display_name": "Term", "field_type": "TEXT",
     "description": "The term or duration of the agreement", "required": False},
    {"name": "governing_law", "display_name": "Governing Law", "field_type": "TEXT",
     "description": "The governing law jurisdiction", "required": False},
    {"name": "amount", "display_name": "Amount", "field_type": "CURRENCY",
     "description": "The monetary amount referenced", "required": False},
    {"name": "payment_terms", "display_name": "Payment Terms", "field_type": "TEXT",
     "description": "Payment terms or pricing schedule", "required": False},
    {"name": "dispute_resolution", "display_name": "Dispute Resolution", "field_type": "TEXT",
     "description": "Arbitration/mediation terms", "required": False},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_repo():
    """Create an in-memory SQLite repository for each test."""
    repo = DatabaseRepository("sqlite:///:memory:")
    yield repo


@pytest.fixture
def services(db_repo):
    """Return a dict of all service instances backed by the in-memory repo."""
    return {
        "project": ProjectService(db_repo),
        "document": DocumentService(db_repo),
        "extraction": ExtractionService(db_repo),
        "review": ReviewService(db_repo),
        "comparison": ComparisonService(db_repo),
        "evaluation": EvaluationService(db_repo),
        "task": TaskService(db_repo),
        "repo": db_repo,
    }


@pytest.fixture
def sample_project(db_repo):
    """Create a sample project with a default template."""
    project = db_repo.create_project("Test Project", "Automated test project")
    template = db_repo.create_field_template("Test Template", fields=DEFAULT_FIELDS)
    db_repo.update_project(project.id, field_template_id=template.id)
    project = db_repo.get_project(project.id)
    return project, template


@pytest.fixture
def sample_txt_file():
    """Create a temporary text file that simulates a legal document."""
    content = """SUPPLY AGREEMENT

This Supply Agreement ("Agreement") is entered into as of January 15, 2024
by and between Acme Corporation ("Buyer") and GlobalTech Inc. ("Seller").

1. TERM
The term of this Agreement shall commence on the Effective Date and continue
for a period of three (3) years unless terminated earlier.

2. PAYMENT TERMS
Buyer shall pay Seller within thirty (30) days of receipt of invoice.
The total contract value shall not exceed $5,000,000.

3. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.

4. DISPUTE RESOLUTION
Any disputes arising under this Agreement shall be resolved by binding
arbitration in Wilmington, Delaware under the rules of the AAA.

5. CONFIDENTIALITY
Each party agrees to maintain the confidentiality of all proprietary
information received from the other party.

6. TERMINATION
Either party may terminate this Agreement upon ninety (90) days written notice.

7. INDEMNIFICATION
Each party shall indemnify the other against all claims arising from
breach of this Agreement.

8. FORCE MAJEURE
Neither party shall be liable for delays caused by events beyond its
reasonable control including natural disasters and government actions.

IN WITNESS WHEREOF, the parties have executed this Agreement.
"""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_html_file():
    """Create a temporary HTML file simulating a legal document."""
    content = """<!DOCTYPE html>
<html><head><title>License Agreement</title></head>
<body>
<h1>SOFTWARE LICENSE AGREEMENT</h1>
<p>This Software License Agreement is made effective as of March 1, 2024
between TechVentures LLC ("Licensor") and DataFlow Corp ("Licensee").</p>

<h2>1. GRANT OF LICENSE</h2>
<p>Licensor grants Licensee a non-exclusive license to use the Software.</p>

<h2>2. TERM</h2>
<p>This Agreement is effective for two (2) years from the Effective Date.</p>

<h2>3. PAYMENT</h2>
<p>Licensee shall pay an annual fee of $250,000 payable within 30 days.</p>

<h2>4. GOVERNING LAW</h2>
<p>This Agreement shall be governed by the laws of the State of California.</p>

<h2>5. DISPUTE RESOLUTION</h2>
<p>Disputes shall be resolved by mediation in San Francisco, California.</p>

<h2>6. CONFIDENTIALITY</h2>
<p>Both parties shall maintain strict confidentiality of proprietary information.</p>

<h2>7. TERMINATION</h2>
<p>Either party may terminate with sixty (60) days written notice.</p>

<h2>8. LIMITATION OF LIABILITY</h2>
<p>Neither party's aggregate liability shall exceed $1,000,000.</p>
</body></html>
"""
    fd, path = tempfile.mkstemp(suffix=".html")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    yield path
    os.unlink(path)
