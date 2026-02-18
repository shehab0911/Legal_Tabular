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

## System Screenshots

### Project Management
![Project List](system%20picture/Project%20list_First%20One.png)
*Main project dashboard showing all legal document review projects*

### Document Upload & Extraction
![Upload and Extraction](system%20picture/Upload%20Documents%20and%20Extraction_2nd.png)
*Upload multiple documents and initiate AI-powered field extraction*

### Comparison Table View
![Comparison Table](system%20picture/Comparison%20Table_2nd.png)
*Side-by-side field comparison with confidence scores and citations*

### Citation Display
![Citation System](system%20picture/Citation.png)
*Detailed citation view showing source text, page numbers, and relevance scores*

### Diff Highlighting
![Diff Highlighting](system%20picture/Diff_Highlighting_4th.png)
*Cross-document difference detection with outlier identification*

### Review Workflow
![Review Section](system%20picture/Review%20Section_5th.png)
*Field-by-field review with approve/reject/manual update options*

### Annotations
![Annotation System](system%20picture/Annotation_6th.png)
*Collaborative review comments and risk flags on extracted fields*

### Evaluation Reports
![Evaluation](system%20picture/Evaluation_7th.png)
*Extraction quality metrics and field-level accuracy analysis*

### Template Management
![Templates](system%20picture/Reextraction%20and%20Template_8th.png)
*Field template creation and management with re-extraction capabilities*

## Development

### Backend Development
```bash
cd backend
pip install -r requirements-dev.txt  # includes testing dependencies
python -m pytest tests/            # run tests
python -m black src/               # code formatting
python -m ruff src/                # linting
```

### Frontend Development
```bash
cd frontend
npm run lint                       # ESLint
npm run type-check                 # TypeScript checking
npm run build                      # Production build
```

## Deployment

### Docker Production
```bash
cd docker
docker-compose -f docker-compose.yml up -d
```

### Manual Deployment
See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions.

## License

MIT License - see [LICENSE](LICENSE) file for details.