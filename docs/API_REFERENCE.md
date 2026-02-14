# API Reference & Examples

## API Overview

Base URL: `http://localhost:8000/api` (Development) or `https://yourdomain.com/api` (Production)

**Response Format**: All responses are JSON
**Authentication**: Currently no auth; add in production (see Section 8)
**Rate Limiting**: Will be added in production deployment

---

## Projects Endpoints

### 1. Create Project

**POST** `/projects`

**Request:**

```json
{
  "name": "Tesla Q1 Contract Review",
  "description": "Review of executive compensation agreements"
}
```

**Response:**

```json
{
  "id": "proj-001",
  "name": "Tesla Q1 Contract Review",
  "description": "Review of executive compensation agreements",
  "status": "CREATED",
  "field_template_id": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "document_count": 0,
  "extraction_count": 0
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Review",
    "description": "Test"
  }'
```

### 2. Get Project

**GET** `/projects/{project_id}`

**Response:**

```json
{
  "id": "proj-001",
  "name": "Tesla Q1 Contract Review",
  "description": "Review of executive compensation agreements",
  "status": "CREATED",
  "field_template_id": "tmpl-001",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:45:00Z",
  "metadata": {
    "document_count": 3,
    "extraction_count": 45,
    "pending_reviews": 5
  }
}
```

### 3. List All Projects

**GET** `/projects?skip=0&limit=10`

**Query Parameters:**

- `skip`: Number of projects to skip (default: 0)
- `limit`: Maximum results (default: 10, max: 100)
- `status`: Filter by status (CREATED, IN_PROGRESS, COMPLETED)

**Response:**

```json
{
  "total": 5,
  "items": [
    {
      "id": "proj-001",
      "name": "Tesla Q1 Contract Review",
      "status": "COMPLETED",
      "document_count": 3,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "proj-002",
      "name": "Apple Board Minutes",
      "status": "IN_PROGRESS",
      "document_count": 1,
      "created_at": "2024-01-10T14:20:00Z"
    }
  ]
}
```

### 4. Update Project

**PUT** `/projects/{project_id}`

**Request:**

```json
{
  "name": "Tesla Revised Contract Review",
  "description": "Updated review with legal team feedback",
  "field_template_id": "tmpl-002"
}
```

**Response:** Same as Get Project response

### 5. Delete Project

**DELETE** `/projects/{project_id}`

**Response:** `204 No Content`

---

## Documents Endpoints

### 6. Upload Document

**POST** `/projects/{project_id}/documents/upload`

**Request:** Multipart form-data

```
file: <binary PDF/DOCX/HTML/TXT file>
```

**Response:**

```json
{
  "id": "doc-001",
  "project_id": "proj-001",
  "filename": "contract_001.pdf",
  "file_format": "pdf",
  "file_path": "/uploads/proj-001/contract_001.pdf",
  "file_size_bytes": 245678,
  "page_count": 12,
  "status": "INDEXED",
  "chunk_count": 34,
  "created_at": "2024-01-15T10:31:00Z"
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/projects/proj-001/documents/upload \
  -F "file=@contract_001.pdf"
```

**Python Example:**

```python
import requests

with open('contract.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/projects/proj-001/documents/upload',
        files=files
    )
    print(response.json())
```

### 7. List Project Documents

**GET** `/projects/{project_id}/documents?skip=0&limit=20`

**Response:**

```json
{
  "total": 3,
  "items": [
    {
      "id": "doc-001",
      "filename": "contract_001.pdf",
      "file_format": "pdf",
      "file_size_bytes": 245678,
      "page_count": 12,
      "status": "INDEXED",
      "chunk_count": 34,
      "created_at": "2024-01-15T10:31:00Z"
    },
    {
      "id": "doc-002",
      "filename": "contract_002.docx",
      "file_format": "docx",
      "file_size_bytes": 156234,
      "status": "INDEXED",
      "chunk_count": 28,
      "created_at": "2024-01-15T10:32:00Z"
    }
  ]
}
```

---

## Field Templates Endpoints

### 8. Create Field Template

**POST** `/templates`

**Request:**

```json
{
  "name": "Employment Contract Template",
  "fields": [
    {
      "name": "effective_date",
      "display_name": "Effective Date",
      "field_type": "DATE",
      "description": "Start date of employment"
    },
    {
      "name": "salary",
      "display_name": "Annual Salary",
      "field_type": "CURRENCY",
      "description": "Base annual compensation"
    },
    {
      "name": "parties",
      "display_name": "Parties to Agreement",
      "field_type": "ENTITY",
      "description": "Company and employee names"
    },
    {
      "name": "job_title",
      "display_name": "Job Title",
      "field_type": "TEXT",
      "description": "Employee position"
    },
    {
      "name": "term_length_months",
      "display_name": "Contract Term (months)",
      "field_type": "NUMBER",
      "description": "Duration in months"
    }
  ]
}
```

**Response:**

```json
{
  "id": "tmpl-001",
  "name": "Employment Contract Template",
  "field_count": 5,
  "version": 1,
  "created_at": "2024-01-15T10:20:00Z",
  "fields": [
    {
      "name": "effective_date",
      "display_name": "Effective Date",
      "field_type": "DATE"
    },
    {
      "name": "salary",
      "display_name": "Annual Salary",
      "field_type": "CURRENCY"
    }
  ]
}
```

### 9. Get Template

**GET** `/templates/{template_id}`

### 10. List Templates

**GET** `/templates?skip=0&limit=10`

---

## Extraction Endpoints

### 11. Extract Fields (Async)

**POST** `/projects/{project_id}/extract`

**Request (Optional - uses project's template if not provided):**

```json
{
  "document_ids": ["doc-001", "doc-002"],
  "fields_to_extract": ["effective_date", "salary", "parties"]
}
```

**Response:** Task initiated

```json
{
  "task_id": "task-12345",
  "status": "started",
  "message": "Extraction started for 2 documents, 3 fields",
  "estimated_duration_seconds": 20
}
```

**Check Task Status:**

```bash
# GET /tasks/{task_id}
curl http://localhost:8000/api/tasks/task-12345
```

**Response:**

```json
{
  "id": "task-12345",
  "status": "completed",
  "progress": 100,
  "result": {
    "extraction_count": 6,
    "success_count": 5,
    "error_count": 1,
    "average_confidence": 0.87
  }
}
```

### 12. List Extractions for Project

**GET** `/projects/{project_id}/extractions?skip=0&limit=50`

**Query Parameters:**

- `document_id`: Filter by document
- `field_name`: Filter by field name
- `status`: PENDING, CONFIRMED, REJECTED, MANUAL_UPDATED
- `min_confidence`: Only return if confidence > this value

**Response:**

```json
{
  "total": 15,
  "items": [
    {
      "id": "ext-001",
      "project_id": "proj-001",
      "document_id": "doc-001",
      "field_name": "effective_date",
      "extracted_value": "January 15, 2024",
      "raw_text": "Effective Date: January 15, 2024",
      "normalized_value": "2024-01-15",
      "confidence_score": 0.92,
      "status": "PENDING",
      "created_at": "2024-01-15T10:32:00Z",
      "citations": [
        {
          "id": "cite-001",
          "citation_text": "This Agreement is effective as of January 15, 2024",
          "relevance_score": 0.95,
          "page_number": 1,
          "document_chunk_id": "chunk-001"
        }
      ]
    },
    {
      "id": "ext-002",
      "project_id": "proj-001",
      "document_id": "doc-001",
      "field_name": "salary",
      "extracted_value": "$150,000 per year",
      "raw_text": "Annual Compensation: $150,000 per year",
      "normalized_value": "USD 150000",
      "confidence_score": 0.88,
      "status": "PENDING",
      "created_at": "2024-01-15T10:32:00Z",
      "citations": []
    }
  ]
}
```

---

## Review Endpoints

### 13. Get Pending Reviews

**GET** `/projects/{project_id}/reviews/pending?skip=0&limit=20`

**Response:**

```json
{
  "total": 5,
  "items": [
    {
      "extraction_id": "ext-001",
      "field_name": "effective_date",
      "document_filename": "contract_001.pdf",
      "ai_value": "2024-01-15",
      "ai_confidence": 0.92,
      "manual_value": null,
      "status": "PENDING",
      "created_at": "2024-01-15T10:32:00Z"
    },
    {
      "extraction_id": "ext-002",
      "field_name": "salary",
      "document_filename": "contract_001.pdf",
      "ai_value": "USD 150000",
      "ai_confidence": 0.88,
      "manual_value": null,
      "status": "PENDING",
      "created_at": "2024-01-15T10:32:00Z"
    }
  ]
}
```

### 14. Review Extraction

**PUT** `/extractions/{extraction_id}/review`

**Request:**

```json
{
  "action": "CONFIRMED"
}
```

**Possible actions:**

- `CONFIRMED`: Accept AI extraction
- `REJECTED`: Mark as incorrect
- `MANUAL_UPDATED`: Accept with manual modification

**Request (for MANUAL_UPDATED):**

```json
{
  "action": "MANUAL_UPDATED",
  "manual_value": "January 20, 2024",
  "notes": "Corrected based on signature page"
}
```

**Response:**

```json
{
  "extraction_id": "ext-001",
  "field_name": "effective_date",
  "status": "CONFIRMED",
  "ai_value": "2024-01-15",
  "manual_value": null,
  "reviewed_by": "john@company.com",
  "reviewed_at": "2024-01-15T11:00:00Z"
}
```

---

## Comparison Table Endpoints

### 15. Get Comparison Table

**GET** `/projects/{project_id}/table`

**Response:**

```json
{
  "project_id": "proj-001",
  "generated_at": "2024-01-15T11:05:00Z",
  "row_count": 5,
  "document_count": 3,
  "rows": [
    {
      "field_name": "effective_date",
      "display_name": "Effective Date",
      "field_type": "DATE",
      "document_results": {
        "doc-001": {
          "value": "2024-01-15",
          "confidence": 0.92,
          "status": "CONFIRMED",
          "citation_text": "Effective as of January 15, 2024"
        },
        "doc-002": {
          "value": "2024-02-01",
          "confidence": 0.85,
          "status": "CONFIRMED",
          "citation_text": null
        },
        "doc-003": {
          "value": null,
          "confidence": 0,
          "status": "NOT_FOUND",
          "citation_text": null
        }
      }
    },
    {
      "field_name": "salary",
      "display_name": "Annual Salary",
      "field_type": "CURRENCY",
      "document_results": {
        "doc-001": {
          "value": "USD 150000",
          "confidence": 0.88,
          "status": "CONFIRMED"
        },
        "doc-002": {
          "value": "USD 175000",
          "confidence": 0.92,
          "status": "CONFIRMED"
        },
        "doc-003": {
          "value": "USD 125000",
          "confidence": 0.78,
          "status": "PENDING"
        }
      }
    }
  ]
}
```

### 16. Export Comparison Table to CSV

**GET** `/projects/{project_id}/table/export-csv`

**Response:** Plain text CSV file

**Example CSV:**

```
Field,Display Name,Doc: contract_001.pdf,Doc: contract_002.docx,Doc: contract_003.pdf
effective_date,Effective Date,2024-01-15 (92%),2024-02-01 (85%),N/A
salary,Annual Salary,USD 150000 (88%),USD 175000 (92%),USD 125000 (78%)
parties,Parties,ABC Corp & John Doe,ABC Corp & Jane Smith,XYZ Ltd & John Doe
job_title,Job Title,Chief Financial Officer,Vice President,Consultant
term_length_months,Term (months),36 (95%),24 (87%),12 (72%)
```

---

## Evaluation Endpoints

### 17. Evaluate Project

**POST** `/projects/{project_id}/evaluate`

**Request (optional - can auto-evaluate based on similarity):**

```json
{
  "gold_standard_data": [
    {
      "document_id": "doc-001",
      "field_name": "effective_date",
      "correct_value": "2024-01-15"
    },
    {
      "document_id": "doc-001",
      "field_name": "salary",
      "correct_value": "USD 150000"
    }
  ]
}
```

**Response:**

```json
{
  "task_id": "eval-task-001",
  "status": "started",
  "message": "Evaluation started"
}
```

### 18. Get Evaluation Report

**GET** `/projects/{project_id}/evaluation-report`

**Response:**

```json
{
  "project_id": "proj-001",
  "generated_at": "2024-01-15T11:10:00Z",
  "summary": {
    "total_fields_extracted": 15,
    "fields_with_high_confidence": 13,
    "fields_with_manual_updates": 2,
    "fields_with_errors": 1
  },
  "metrics": {
    "average_confidence_score": 0.87,
    "extraction_accuracy": 0.93,
    "coverage_percentage": 0.95,
    "inter_document_consistency": 0.82
  },
  "field_metrics": [
    {
      "field_name": "effective_date",
      "field_type": "DATE",
      "extraction_count": 3,
      "successful_extractions": 3,
      "average_confidence": 0.92,
      "similarity_score": 0.98
    },
    {
      "field_name": "salary",
      "field_type": "CURRENCY",
      "extraction_count": 3,
      "successful_extractions": 3,
      "average_confidence": 0.86,
      "similarity_score": 0.45,
      "variance_notes": "Wide salary range across documents"
    }
  ]
}
```

---

## System Endpoints

### 19. Health Check

**GET** `/health`

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T11:15:00Z",
  "database": "connected",
  "version": "1.0.0"
}
```

### 20. Get API Status

**GET** `/status`

**Response:**

```json
{
  "status": "operational",
  "timestamp": "2024-01-15T11:15:00Z",
  "database_status": "connected",
  "active_tasks": 2,
  "uptime_seconds": 86400,
  "memory_usage_mb": 256
}
```

---

## Error Responses

### Standard Error Response Format

**Response (4xx/5xx):**

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid file format. Supported: pdf, docx, html, txt",
  "details": {
    "field": "file_format",
    "value": "exe",
    "allowed": ["pdf", "docx", "html", "txt"]
  },
  "timestamp": "2024-01-15T11:15:00Z",
  "request_id": "req-abc123"
}
```

### Common Error Codes

| Code             | Status | Meaning                   |
| ---------------- | ------ | ------------------------- |
| VALIDATION_ERROR | 422    | Request validation failed |
| NOT_FOUND        | 404    | Resource not found        |
| ALREADY_EXISTS   | 409    | Resource already exists   |
| ACCESS_DENIED    | 403    | Insufficient permissions  |
| INTERNAL_ERROR   | 500    | Server error              |

---

## Python SDK Example

```python
# legal_review_client.py
import requests
from typing import List, Optional

class LegalReviewClient:
    def __init__(self, base_url='http://localhost:8000/api'):
        self.base_url = base_url

    def create_project(self, name: str, description: str) -> dict:
        response = requests.post(
            f"{self.base_url}/projects",
            json={"name": name, "description": description}
        )
        return response.json()

    def upload_document(self, project_id: str, file_path: str) -> dict:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/projects/{project_id}/documents/upload",
                files=files
            )
        return response.json()

    def extract_fields(self, project_id: str) -> str:
        response = requests.post(
            f"{self.base_url}/projects/{project_id}/extract"
        )
        data = response.json()
        return data['task_id']

    def get_comparison_table(self, project_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/table"
        )
        return response.json()

    def review_extraction(self, extraction_id: str, action: str, manual_value: Optional[str] = None) -> dict:
        payload = {"action": action}
        if manual_value:
            payload["manual_value"] = manual_value

        response = requests.put(
            f"{self.base_url}/extractions/{extraction_id}/review",
            json=payload
        )
        return response.json()

    def get_evaluation(self, project_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/evaluation-report"
        )
        return response.json()

# Usage Example
if __name__ == "__main__":
    client = LegalReviewClient()

    # Create project
    project = client.create_project(
        "Q1 Contracts",
        "Review all Q1 contracts"
    )
    print(f"Created project: {project['id']}")

    # Upload documents
    doc1 = client.upload_document(project['id'], "contract1.pdf")
    doc2 = client.upload_document(project['id'], "contract2.pdf")
    print(f"Uploaded {doc1['filename']} and {doc2['filename']}")

    # Extract fields
    task_id = client.extract_fields(project['id'])
    print(f"Extraction task started: {task_id}")

    # Get comparison table
    table = client.get_comparison_table(project['id'])
    print(f"Comparison table: {table['row_count']} rows × {table['document_count']} docs")

    # Review extractions
    for row in table['rows']:
        for doc_id, result in row['document_results'].items():
            if result['status'] == 'PENDING':
                client.review_extraction(result['extraction_id'], 'CONFIRMED')

    # Get evaluation
    evaluation = client.get_evaluation(project['id'])
    print(f"Average confidence: {evaluation['metrics']['average_confidence_score']:.2%}")
```

---

## Testing API with Postman

1. **Import API Collection**
   - Use Postman's API import feature
   - Import from `docs/postman_collection.json`

2. **Set Environment Variables**

   ```
   base_url = http://localhost:8000/api
   project_id = proj-001
   ```

3. **Run Workflow**
   - Create Project
   - Upload Document
   - Create Template
   - Extract Fields
   - Review Extractions
   - Get Comparison Table
   - Export to CSV
   - Get Evaluation

---

## Rate Limiting (Production)

Production deployments will implement:

- 1000 requests/minute per API key
- 10 requests/second per IP address
- Response header: `X-RateLimit-Remaining`

---

## API Versioning

Current version: `v1` (at `/api/v1/`)

Future versions will be available at `/api/v2/`, `/api/v3/`, etc. with backward compatibility maintained.
