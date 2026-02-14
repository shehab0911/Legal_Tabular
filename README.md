# Legal Tabular Review System

Enterprise-grade system for extracting, comparing, and reviewing key fields from legal documents. Built with FastAPI (Python) backend and React (TypeScript) frontend.

## Features

### Core Capabilities
- **Multi-format Document Ingestion**: PDF, DOCX, HTML, TXT with chunked streaming upload
- **AI-Powered Field Extraction**: Groq LLM (primary) + Google Gemini (fallback) + heuristic patterns
- **Side-by-Side Comparison Table**: Compare extracted fields across multiple documents
- **Citation Tracking**: Source text references with relevance scoring and page numbers
- **Confidence Scoring**: Per-field extraction confidence with color-coded visualization

### Features
- **Excel/XLSX Export**: Styled spreadsheets with confidence color-coding and auto-fit columns
- **CSV Export**: Lightweight tabular export for analysis
- **Diff Highlighting**: Cross-document difference detection with outlier identification and similarity matrices
- **Annotation System**: Full CRUD for collaborative review comments on any extraction field
- **Field Template Management**: Create, edit, version, and assign extraction templates with re-extraction trigger
- **Review Workflow**: Approve, reject, or manually update extractions with audit trail (reviewed_by)
- **Evaluation Reports**: Extraction quality metrics with field-level accuracy breakdown
- **Background Task Processing**: Async extraction and evaluation with real-time status polling
- **Enterprise Middleware**: Request logging with IDs, rate limiting (200 req/min), response time headers

### Security & Performance
- **Rate Limiting**: Configurable per-IP rate limiting with X-RateLimit headers
- **Request Logging**: Every request logged with unique ID, method, path, status, and duration
- **CORS Configuration**: Configurable cross-origin resource sharing
- **SQLite WAL Mode**: Write-ahead logging for concurrent read/write performance
- **Retry on Lock**: Automatic retry with exponential backoff for database lock contention
- **Chunked File Upload**: Stream large files to disk without memory spikes

## Architecture

```
frontend/          # React + TypeScript + Vite + TailwindCSS
  src/
    components/    # UI components (7 feature panels)
    pages/         # Project list and detail pages
    services/      # API client with 10 API modules
    store/         # Zustand state management

backend/           # FastAPI + SQLAlchemy + Python 3.10+
  app.py           # FastAPI application with all endpoints
  src/
    models/        # SQLAlchemy ORM + Pydantic schemas
    services/      # Business logic (9 service classes)
    storage/       # Database repository pattern

docker/            # Docker Compose for production/dev
data/              # Sample legal documents for testing
docs/              # Architecture, API, deployment docs
```

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
# API available at http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

### Environment Variables
```bash
# LLM Configuration (optional - falls back to heuristics)
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key

# Database (default: SQLite)
DATABASE_URL=sqlite:///./legal_review.db
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/projects` | GET/POST | List/create projects |
| `/projects/{id}` | GET/PUT/DELETE | Project CRUD |
| `/projects/{id}/documents/upload` | POST | Upload document |
| `/projects/{id}/documents` | GET | List documents |
| `/projects/{id}/extract` | POST | Start field extraction |
| `/projects/{id}/re-extract` | POST | Re-extract with current template |
| `/projects/{id}/table` | GET | Get comparison table |
| `/projects/{id}/table/export-csv` | POST | Export to CSV |
| `/projects/{id}/table/export-excel` | POST | Export to XLSX |
| `/projects/{id}/diff` | GET | Cross-document diff |
| `/projects/{id}/reviews/pending` | GET | Pending reviews |
| `/projects/{id}/extractions` | GET | List extractions |
| `/projects/{id}/annotations` | GET | Project annotations |
| `/projects/{id}/evaluate` | POST | Start evaluation |
| `/projects/{id}/evaluation-report` | GET | Get eval report |
| `/extractions/{id}/review` | PUT | Review extraction |
| `/extractions/{id}/annotations` | GET | Field annotations |
| `/field-templates` | GET/POST | List/create templates |
| `/field-templates/{id}` | GET/PUT | Template CRUD |
| `/annotations` | POST | Create annotation |
| `/annotations/{id}` | PUT/DELETE | Update/delete annotation |
| `/tasks/{id}` | GET | Task status |

## Testing

```bash
cd backend
pytest -v  # Run all 111+ tests
```

### Test Coverage
- **Unit Tests**: Repository, document parser, field extractor
- **Integration Tests**: All API endpoints, full workflows
- **Workflow Tests**: End-to-end document ingestion and extraction
 
### QA Smoke Test
 
```bash
# Runs a minimal end-to-end verification (upload → extract → table)
python smoke_test.py
```
 
The script exercises:
- Project creation and document upload
- Extraction trigger and task status polling
- Retrieval of the comparison table

## Docker
 
```bash
cd docker
# Standard
docker-compose up -d

# Development
docker-compose -f docker-compose.dev.yml up -d

# Run a unique instance to avoid port/name conflicts
# Uses custom compose with distinct ports and an isolated project name
docker-compose -f docker-compose.run.yml -p legal_tabular_2 up -d
```
 
Ports for the unique instance:
- Backend: http://localhost:8002
- Frontend: http://localhost:5174
- Postgres: localhost:5434
- Redis: localhost:6380
 
Data volume for the unique instance:
- postgres_data_2 (separate from any other instance)

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Groq SDK, Google Generative AI
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Zustand, Axios
- **Database**: SQLite (dev), PostgreSQL (production)
- **AI/LLM**: Groq (Llama 3.3 70B), Google Gemini 1.5 Flash, heuristic fallback
- **Export**: openpyxl (Excel), csv (CSV), pandas (data processing)

## Sample Data

The `data/` directory contains sample legal documents for testing:
- Tesla SEC filings (HTML, PDF)
- Supply agreements (PDF)
- Contract exhibits (HTML)

## Screenshots

Below are screenshots captured from the running system as proof of the implemented features:
## Project List
![Project List](system%20picture/Project%20list_First%20One.png)
## Document Upload & Extraction
![Document Upload & Extraction](system%20picture/Upload%20Documents%20and%20Extraction_2nd.png)
## Comparison Table
![Comparison Table](system%20picture/Comparison%20Table_2nd.png)
## Diff Highlighting
![Diff Highlighting](system%20picture/Diff_Highlighting_4th.png)
## Review Section
![Review Section](system%20picture/Review%20Section_5th.png)
## Annotations
![Annotations](system%20picture/Annotation_6th.png)
## Evaluation
![Evaluation](system%20picture/Evaluation_7th.png)

## License

Proprietary - All rights reserved.
