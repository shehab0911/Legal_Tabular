# Troubleshooting & FAQ

## TROUBLESHOOTING GUIDE

### Backend Issues

#### 1. "ModuleNotFoundError: No module named 'src'"

**Problem:** Backend cannot find the src module

**Solutions:**

```bash
# Make sure you're in backend directory
cd backend

# Add backend to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or ensure the app.py has correct imports
# app.py should have:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

#### 2. "sqlite3.OperationalError: database is locked"

**Problem:** Database file is locked, typically from multiple simultaneous writes

**Solutions:**

```bash
# Use WAL mode for SQLite (Write-Ahead Logging)
# Add to database initialization:
sqlite_engine.execute("PRAGMA journal_mode=WAL")

# Or switch to PostgreSQL for production:
DATABASE_URL=postgresql://user:password@localhost/legal_review
```

#### 3. "Connection refused" when accessing API

**Problem:** Backend server not running

**Solutions:**

```bash
# Check if process is running
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Start with verbose output
uvicorn app:app --reload --port 8000 --log-level debug

# Check firewall
# Windows: netsh advfirewall firewall add rule name="Python 8000" dir=in action=allow protocol=tcp localport=8000
```

#### 4. "PDF parsing fails with corrupt file error"

**Problem:** Malformed or encrypted PDF

**Solutions:**

```python
# In document_parser.py, improve error handling:
def _parse_pdf(self, file_path: str) -> tuple[str, dict]:
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            # Check if encrypted
            if pdf_reader.is_encrypted:
                pdf_reader.decrypt('')  # Try empty password
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text, {'pages': len(pdf_reader.pages)}
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise ValueError(f"Cannot parse PDF: {e}")
```

#### 5. "Field extraction returns low confidence (< 0.3)"

**Problem:** LLM-based extraction not working well, or no heuristic match

**Solutions:**

```python
# Check if LLM API is configured:
import os
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not set, falling back to heuristics only")

# Improve heuristics in field_extractor.py:
def _extract_with_heuristics(self, text: str, chunks: List[dict], field_name: str, field_type: str):
    patterns = {
        'DATE': [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # MM/DD/YYYY
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
            # Add more patterns specific to your documents
        ],
        # ... expand for other field types
    }
```

#### 6. "Memory usage keeps growing"

**Problem:** Memory leak, probably in document processing or LLM calls

**Solutions:**

```python
# Add memory monitoring:
import psutil
import gc

def check_memory():
    process = psutil.Process()
    mb = process.memory_info().rss / 1024 / 1024
    if mb > 1000:  # 1GB threshold
        gc.collect()
        logger.warning(f"Memory usage high: {mb}MB, forcing garbage collection")

# Explicitly free resources in service orchestrator:
@app.post("/projects/{project_id}/extract")
async def extract_fields(project_id: str, background_tasks: BackgroundTasks):
    def cleanup():
        gc.collect()

    background_tasks.add_task(extract_worker, project_id)
    background_tasks.add_task(cleanup)
    return {"status": "started"}
```

#### 7. "Database migration from SQLite to PostgreSQL fails"

**Problem:** Schema or data incompatibility

**Solutions:**

```python
# Step-by-step migration script:
import sqlalchemy as sa
from sqlalchemy import text

def migrate_sqlite_to_postgres():
    # 1. Create tables in PostgreSQL
    pg_engine = create_engine('postgresql://...')
    Base.metadata.create_all(pg_engine)

    # 2. Export data from SQLite
    sqlite_engine = create_engine('sqlite:///legal_review.db')
    Session = sessionmaker(bind=sqlite_engine)
    sqlite_session = Session()

    # 3. Import data to PostgreSQL
    pg_session = sessionmaker(bind=pg_engine)()

    projects = sqlite_session.query(Project).all()
    for project in projects:
        pg_session.add(project)
    pg_session.commit()

    # 4. Verify counts
    sqlite_count = sqlite_session.query(Project).count()
    pg_count = pg_session.query(Project).count()
    assert sqlite_count == pg_count, f"Mismatch: {sqlite_count} vs {pg_count}"
```

---

### Frontend Issues

#### 8. "Blank page / whitespace only in browser"

**Problem:** React not mounting or build issues

**Solutions:**

```bash
# Clear node_modules and rebuild
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev

# Check browser console for errors
# Press F12, look for errors in Console tab

# Verify vite config
cat vite.config.ts  # Should have React plugin

# Check main.tsx
cat src/main.tsx  # Should have ReactDOM.createRoot()
```

#### 9. "API calls return 404 Not Found"

**Problem:** Frontend API URL incorrect or backend not running

**Solutions:**

```bash
# Check frontend .env
cat .env.local
# Should have: VITE_API_URL=http://localhost:8000/api

# Verify backend is running
curl http://localhost:8000/api/health

# Check API response headers
curl -v http://localhost:8000/api/projects

# Check CORS configuration in backend:
# app.py should have:
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_credentials=True,
)
```

#### 10. "CORS error: 'No 'Access-Control-Allow-Origin' header"

**Problem:** Backend CORS not configured for frontend URL

**Solutions:**

```python
# In backend/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Development
        "http://localhost:3000",      # Alternative dev port
        "https://yourdomain.com",     # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Or allow all (development only):
allow_origins=["*"]
```

#### 11. "File upload stuck / no progress"

**Problem:** File too large or network timeout

**Solutions:**

```python
# Increase timeouts in backend
# In app.py:
@app.post("/projects/{project_id}/documents/upload")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    MAX_FILE_SIZE = 104857600  # 100MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Process asynchronously
    background_tasks.add_task(process_document, project_id, contents)
    return {"status": "queued", "filename": file.filename}

# In frontend API client:
const apiClient = axios.create({
    timeout: 300000,  // 5 minutes
    maxBodyLength: 104857600,
    maxContentLength: 104857600,
});
```

#### 12. "Review changes not persisting"

**Problem:** Review state not saved to database

**Solutions:**

```python
# Verify database transaction:
@app.put("/extractions/{extraction_id}/review")
async def review_extraction(extraction_id: str, review_data: ReviewRequest):
    try:
        # Update extraction
        repo.update_extraction_review(
            extraction_id,
            review_data.action,
            review_data.manual_value
        )

        # Force commit
        repo.session.commit()

        # Verify update
        updated = repo.get_extraction(extraction_id)
        assert updated.status == review_data.action

        return {"status": "success"}
    except Exception as e:
        repo.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

#### 13. "Table data not updating after extraction"

**Problem:** Frontend state not refreshing or API returning stale data

**Solutions:**

```typescript
// In ProjectDetailPage.tsx
const handleExtractFields = async () => {
  try {
    const task = await extractionAPI.extract(projectId);

    // Poll for completion
    let completed = false;
    while (!completed) {
      const status = await taskAPI.getStatus(task.task_id);
      if (status.status === "completed") {
        completed = true;
        // Force refresh comparison table
        setRefreshKey((prev) => prev + 1);
        const table = await comparisonAPI.getTable(projectId);
        setTableData(table);
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  } catch (error) {
    console.error("Extraction failed:", error);
  }
};
```

---

### Deployment Issues

#### 14. "Docker container exits immediately"

**Problem:** Container process crashed

**Solutions:**

```bash
# Check logs
docker logs container_name

# Run interactively to see errors
docker run -it image_name /bin/bash

# Add healthcheck to Dockerfile:
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```

#### 15. "PostgreSQL connection refused in production"

**Problem:** Database not accessible from container

**Solutions:**

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection settings
psql -h localhost -U reviewer -d legal_review -c "SELECT 1"

# Check firewall
sudo ufw allow 5432/tcp

# Update docker-compose to use proper hostname
# Change from localhost to service name:
DATABASE_URL=postgresql://reviewer:password@postgres:5432/legal_review

# If using RDS/managed database, ensure security group permits connection
```

---

## FAQ (Frequently Asked Questions)

### Installation & Setup

**Q: Do I need PostgreSQL for development?**
A: No, the system uses SQLite by default for development. PostgreSQL is recommended for production (multi-user, better performance). Switch by setting `DATABASE_URL=postgresql://...`

**Q: Can I use Python 3.9?**
A: Probably, but officially tested on Python 3.10+ due to type hints and asyncio improvements. To try 3.9, remove type hint features or backport them with `from __future__ import annotations`.

**Q: How much disk space do I need?**
A: ~500MB for dependencies, then ~10MB per 1000 documents processed (based on typical contract sizes).

---

### Functionality

**Q: Can the system handle scanned PDFs (images)?**
A: Not currently. The system uses text extraction which doesn't work on image-based PDFs. To support this, add OCR:

```python
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

def extract_text_from_scanned_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image)
    return text
```

**Q: What field types are supported?**
A: Currently DATE, CURRENCY, ENTITY, TEXT, NUMBER. To add custom types:

```python
# In schema.py enums:
class FieldType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    PHONE = "PHONE"
    EMAIL = "EMAIL"

# Then add extraction pattern in field_extractor.py
```

**Q: How are citations found? Can I improve accuracy?**
A: Citations use Jaccard similarity between extracted value and document chunks. To improve:

```python
def _find_citations(self, extracted_value, chunks):
    # Current: Jaccard similarity
    # Improvement: Use context-aware matching
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer('all-MiniLM-L6-v2')
    extracted_embedding = model.encode(extracted_value)

    best_citations = []
    for chunk in chunks:
        similarity = cosine_similarity([extracted_embedding], [model.encode(chunk['text'])])[0][0]
        if similarity > 0.7:
            best_citations.append((chunk, similarity))

    return sorted(best_citations, key=lambda x: x[1], reverse=True)[:3]
```

**Q: Can I use a different LLM instead of OpenAI?**
A: Yes, modify the `_extract_with_llm` method:

```python
def _extract_with_llm(self, document_text, field_def):
    # Use Anthropic Claude:
    from anthropic import Anthropic
    client = Anthropic()
    message = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

    # Or use Ollama (local):
    import ollama
    response = ollama.generate(model='llama2', prompt=prompt)
    return response['response']
```

---

### Performance

**Q: How many documents can the system handle?**
A: Limited by disk space and database size. Tested with 1000+ documents. For 10,000+, consider:

- Partitioning documents by project
- Archiving old projects to separate database
- Using PostgreSQL with proper indexes (see DEPLOYMENT.md)

**Q: How long does extraction take?**
A: ~0.5-2 seconds per document depending on:

- Document size (10 page = ~1s)
- Number of fields (5 fields = ~1s vs 25 fields = ~2s)
- LLM availability (LLM = slower, heuristics = faster)

**Q: Can I process documents in parallel?**
A: Yes, using FastAPI's async:

```python
# Current: Sequential processing
# Improvement: Parallel chunks
import asyncio

async def extract_all_fields_parallel(document_text, fields, chunks):
    tasks = []
    for field in fields:
        task = asyncio.create_task(self.extract_field_async(document_text, field, chunks))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return results
```

---

### Data & Security

**Q: What happens to uploaded documents?**
A: Documents are stored in the configured storage location (default: `backend/uploaded_files/`). Text is extracted and stored in database; original files can be deleted after extraction.

**Q: Is my data encrypted?**
A: Not by default. For production, add:

```python
# Use encrypted database connection:
# DATABASE_URL=postgresql+psycopg2://user:pass@host/db?sslmode=require

# Add field-level encryption:
from Crypto.Cipher import AES
def encrypt_extraction(value):
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext = cipher.encrypt(value.encode())
    return ciphertext
```

**Q: Can I export data?**
A: Yes, CSV export is built-in. For other formats:

```python
# JSON export
import json
@app.get("/projects/{project_id}/export-json")
def export_json(project_id):
    table = ComparisonService(repo).generate_comparison_table(project_id)
    return json.dumps(table)

# Excel export
import openpyxl
@app.get("/projects/{project_id}/export-xlsx")
def export_xlsx(project_id):
    table = ComparisonService(repo).generate_comparison_table(project_id)
    wb = openpyxl.Workbook()
    # ... populate sheet
    return FileResponse("export.xlsx")
```

---

### Development

**Q: How do I add a new field type?**
A:

1. Add to `FieldType` enum in schema.py
2. Add extraction pattern in field_extractor.py
3. Add normalization logic in \_normalize_value()
4. Add test case in tests/

**Q: Can I modify the database schema?**
A: Yes, but this requires a migration:

```python
# Create migration script
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('extraction_result', sa.Column('quality_score', sa.Float))

def downgrade():
    op.drop_column('extraction_result', 'quality_score')

# Run: alembic upgrade head
```

**Q: How do I debug extraction issues?**
A: Add detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In field_extractor.py
logger = logging.getLogger(__name__)

def extract_fields(self, document_text, chunks, fields):
    logger.debug(f"Extracting {len(fields)} fields from {len(chunks)} chunks")
    logger.debug(f"Document text preview: {document_text[:500]}...")

    for field in fields:
        logger.debug(f"Processing field: {field['name']} ({field['field_type']})")
        # ... extraction logic
        logger.debug(f"  Result: confidence={result['confidence']}, citations={len(result['citations'])}")
```

---

### Integration

**Q: Can I integrate with my document management system?**
A: Yes, create a webhook or API adapter:

```python
# Example: Connect to SharePoint
from office365.runtime.auth.token_request import ClientCredentialTokenRequest
from office365.sharepoint.client_context import ClientContext

def sync_with_sharepoint(sharepoint_site, folder):
    ctx = ClientContext(sharepoint_site).with_credentials(...)

    # Get files from SharePoint
    for file in ctx.web.get_folder_by_server_relative_url(folder).get_files():
        # Download and process
        document = doc_service.ingest_document(project_id, file.name, file)
        # Extract fields
        extractions = ext_service.extract_fields_for_document(...)
```

**Q: Can I set up automated extraction from email?**
A: Yes, using a scheduled task:

```python
# Celery task scheduled daily
from celery import shared_task

@shared_task
def extract_from_email():
    import imaplib
    mail = imaplib.IMAP4_SSL('imapserver')
    mail.login('user@company.com', 'password')

    for attachment in get_attachments(mail, 'legal'):
        doc_service.ingest_document(project_id, attachment.filename, attachment)
        ext_service.extract_fields_for_document(project_id, doc_id)
```

---

## Getting Help

1. **Check the logs**: `docker logs container_name` or `tail -f backend.log`
2. **Search existing issues**: Check GitHub or internal docs
3. **Check the troubleshooting guide**: This document has solutions for common problems
4. **Enable debug logging**: Set `LOG_LEVEL=DEBUG` and review output
5. **Test with sample data**: Use files in `data/` folder to verify system works

## Reporting Issues

Include:

- Error message (full traceback)
- Steps to reproduce
- Environment (Python version, OS, docker version)
- Logs from time of error
- Sample file that triggers the issue (if applicable)
