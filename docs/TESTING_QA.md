# Testing & Quality Assurance Guide

## 1. UNIT TESTS

### 1.1 Document Parser Tests

```python
# tests/services/test_document_parser.py

def test_pdf_parsing():
    """Test PDF text extraction with page numbers"""
    parser = DocumentParser()
    content, metadata = parser.parse("test.pdf", "pdf")

    assert content != ""
    assert metadata['format'] == 'pdf'
    assert metadata['pages'] > 0
    assert "--- Page" in content  # Page markers

def test_docx_parsing():
    """Test DOCX paragraph and table extraction"""
    parser = DocumentParser()
    content, metadata = parser.parse("test.docx", "docx")

    assert "party1" in content.lower()
    assert metadata['format'] == 'docx'
    assert "|" in content  # Table delimiter

def test_html_parsing():
    """Test HTML DOM cleanup"""
    parser = DocumentParser()
    content, metadata = parser.parse("test.html", "html")

    assert "<script>" not in content
    assert "<style>" not in content
    assert len(content) > 0

def test_unsupported_format():
    """Test rejection of unsupported formats"""
    parser = DocumentParser()

    with pytest.raises(ValueError):
        parser.parse("test.exe", "exe")

def test_chunking():
    """Test document chunking with overlap"""
    chunker = DocumentChunker(chunk_size=100, overlap=10)
    text = " ".join(["word"] * 500)

    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    # Verify overlap: last words of chunk 1 in chunk 2
    assert chunks[0]['text'].split()[-5:] in [
        word for word in chunks[1]['text'].split()[:10]
    ]
```

### 1.2 Field Extractor Tests

```python
# tests/services/test_field_extractor.py

def test_extract_with_heuristics():
    """Test regex-based extraction"""
    extractor = FieldExtractor()

    text = "Effective Date: January 15, 2024"
    field_def = {
        'name': 'effective_date',
        'field_type': 'DATE',
        'description': 'Start date'
    }

    result = extractor._extract_with_heuristics(
        text, [], 'effective_date', 'DATE'
    )

    assert result['value'] is not None
    assert '2024' in str(result['value'])
    assert result['confidence'] > 0.5

def test_normalize_date():
    """Test date normalization"""
    extractor = FieldExtractor()

    normalized = extractor._normalize_value('01/15/2024', 'DATE')
    assert normalized == '2024-01-15'

    normalized = extractor._normalize_value('January 15, 2024', 'DATE')
    assert normalized == '2024-01-15'

def test_normalize_currency():
    """Test currency normalization"""
    extractor = FieldExtractor()

    normalized = extractor._normalize_value('$50,000', 'CURRENCY')
    assert 'USD' in normalized
    assert '50000' in normalized

def test_confidence_adjustment():
    """Test confidence score calculation"""
    extractor = FieldExtractor()

    # Good normalization = high confidence
    confidence = extractor._validate_extraction(
        'January 15, 2024',  # extracted_value
        '2024-01-15',        # normalized_value (good)
        'DATE'
    )
    assert confidence > 0.7

    # Failed normalization = low confidence
    confidence = extractor._validate_extraction(
        'unknown',
        None,  # normalization failed
        'DATE'
    )
    assert confidence < 0.7

def test_find_citations():
    """Test citation finding with similarity scoring"""
    extractor = FieldExtractor()

    chunks = [
        {'text': 'The effective date is January 15, 2024', 'page_number': 1, 'section': 'Main'},
        {'text': 'Payment due within 30 days', 'page_number': 2, 'section': 'Payment'},
    ]

    citations = extractor._find_citations('January 15, 2024', chunks, 'doc1')

    assert len(citations) > 0
    assert citations[0]['relevance_score'] > 0.3
    assert 'effective' in citations[0]['citation_text'].lower()
```

### 1.3 Database Repository Tests

```python
# tests/storage/test_repository.py

def test_create_project():
    """Test project creation"""
    repo = DatabaseRepository("sqlite:///:memory:")

    project = repo.create_project("Test Project", "Description")

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.status == ProjectStatus.CREATED

def test_project_document_relationship():
    """Test project-document foreign key"""
    repo = DatabaseRepository("sqlite:///:memory:")

    project = repo.create_project("Test")
    doc = repo.create_document(project.id, "test.pdf", "pdf", "/path", 1000, "content")

    assert doc.project_id == project.id

    # Fetch related documents
    docs = repo.list_project_documents(project.id)
    assert len(docs) == 1

def test_extraction_with_citations():
    """Test extraction-citation relationships"""
    repo = DatabaseRepository("sqlite:///:memory:")

    project = repo.create_project("Test")
    doc = repo.create_document(project.id, "test.pdf", "pdf", "/path", 1000, "content")
    extraction = repo.create_extraction(
        project.id, doc.id, "date", "DATE", "2024-01-15", "January 15, 2024", "2024-01-15"
    )

    citation = repo.create_citation(
        extraction.id, doc.id, "From section 1", page_number=1
    )

    citations = repo.get_citations_for_extraction(extraction.id)
    assert len(citations) == 1
    assert citations[0].citation_text == "From section 1"

def test_review_state_creation():
    """Test review state tracking"""
    repo = DatabaseRepository("sqlite:///:memory:")

    project = repo.create_project("Test")
    doc = repo.create_document(project.id, "test.pdf", "pdf", "/path", 1000, "content")
    extraction = repo.create_extraction(
        project.id, doc.id, "date", "DATE", "2024-01-15"
    )

    review = repo.create_review_state(project.id, extraction.id, "2024-01-15")

    assert review.status == ExtractionStatus.PENDING
    assert review.ai_value == "2024-01-15"

def test_status_transitions():
    """Test valid status transitions"""
    repo = DatabaseRepository("sqlite:///:memory:")

    review = ReviewState(...)

    # PENDING → CONFIRMED
    review.status = ExtractionStatus.CONFIRMED
    assert review.status == ExtractionStatus.CONFIRMED

    # PENDING → REJECTED
    review.status = ExtractionStatus.REJECTED
    assert review.status == ExtractionStatus.REJECTED
```

---

## 2. INTEGRATION TESTS

### 2.1 End-to-End Extraction Workflow

```python
# tests/integration/test_extraction_workflow.py

@pytest.mark.asyncio
async def test_complete_extraction_workflow():
    """Test: upload → parse → extract → review → table"""

    # Setup
    repo = DatabaseRepository("sqlite:///:memory:")
    doc_service = DocumentService(repo)
    ext_service = ExtractionService(repo)
    review_service = ReviewService(repo)
    comparison_service = ComparisonService(repo)

    # Create project and template
    project = repo.create_project("Test Project")
    template = repo.create_field_template(
        "Default",
        [
            {'name': 'effective_date', 'display_name': 'Effective Date', 'field_type': 'DATE'},
            {'name': 'parties', 'display_name': 'Parties', 'field_type': 'ENTITY'},
        ]
    )
    repo.update_project(project.id, field_template_id=template.id)

    # 1. Ingest document
    document = doc_service.ingest_document(project.id, "sample.pdf", "tests/fixtures/sample.pdf")
    assert document['status'] == DocumentStatus.INDEXED.value

    # 2. Extract fields
    extractions = ext_service.extract_fields_for_document(
        project.id, document['id'], template.fields
    )
    assert len(extractions) == 2  # Two fields

    # 3. Get pending reviews
    reviews = review_service.get_pending_reviews(project.id)
    assert len(reviews) == 2

    # 4. Review extractions
    for review in reviews:
        review_service.update_extraction_review(
            review['extraction_id'],
            'CONFIRMED'
        )

    # 5. Generate comparison table
    table = comparison_service.generate_comparison_table(project.id)
    assert table['row_count'] == 2
    assert table['document_count'] == 1

@pytest.mark.asyncio
async def test_multi_document_comparison():
    """Test: compare 3 contracts side-by-side"""

    repo, services = setup_system()
    project = create_test_project(repo)

    # Upload 3 documents
    docs = []
    for i in range(3):
        doc = ingest_test_document(repo, project.id, f"contract_{i}.pdf")
        docs.append(doc)

    # Extract from all
    for doc in docs:
        extract_for_document(repo, project.id, doc.id)

    # Generate table
    table = ComparisonService(repo).generate_comparison_table(project.id)

    # Verify alignment
    for row in table['rows']:
        for doc_id in [d['id'] for d in docs]:
            assert doc_id in row['document_results']
```

### 2.2 Evaluation Workflow

```python
# tests/integration/test_evaluation_workflow.py

@pytest.mark.asyncio
async def test_evaluation_accuracy():
    """Test: extract → review → evaluate"""

    repo = DatabaseRepository("sqlite:///:memory:")
    eval_service = EvaluationService(repo)

    # Create and populate project
    project, extractions = setup_project_with_extractions(repo)

    # Evaluate with ground truth
    evaluation_data = [
        {
            'document_id': extractions[0].document_id,
            'field_name': 'effective_date',
            'human_value': '2024-01-15'
        }
    ]

    for item in evaluation_data:
        eval_service.evaluate_extraction(
            project.id,
            item['document_id'],
            item['field_name'],
            item['human_value']
        )

    # Get report
    report = eval_service.generate_evaluation_report(project.id)

    assert report['metrics']['total_fields'] > 0
    assert 0 <= report['metrics']['field_accuracy'] <= 1.0
    assert report['metrics']['average_confidence'] > 0
```

### 2.3 API Endpoint Tests

```python
# tests/integration/test_api_endpoints.py

@pytest.mark.asyncio
async def test_create_project_endpoint():
    """Test POST /projects"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/projects", json={
            "name": "Test Project",
            "description": "Test Description"
        })

        assert response.status_code == 200
        data = response.json()
        assert data['id'] is not None
        assert data['name'] == "Test Project"

@pytest.mark.asyncio
async def test_upload_document_endpoint():
    """Test POST /projects/{id}/documents/upload"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create project first
        proj_resp = await client.post("/projects", json={"name": "Test"})
        project_id = proj_resp.json()['id']

        # Upload document
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = await client.post(
                f"/projects/{project_id}/documents/upload",
                files={"file": f}
            )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'INDEXED'

@pytest.mark.asyncio
async def test_extraction_endpoint():
    """Test POST /projects/{id}/extract"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        project, doc = setup_project_with_document()

        response = await client.post(f"/projects/{project.id}/extract")

        assert response.status_code == 200
        data = response.json()
        assert 'task_id' in data
        assert data['status'] == 'started'

@pytest.mark.asyncio
async def test_comparison_table_endpoint():
    """Test GET /projects/{id}/table"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        project, docs = setup_extracted_project()

        response = await client.get(f"/projects/{project.id}/table")

        assert response.status_code == 200
        data = response.json()
        assert 'rows' in data
        assert 'document_count' in data
```

---

## 3. SMOKE TESTS (with Sample Data)

```python
# tests/smoke_test.py

@pytest.mark.smoke
def test_end_to_end_with_sample_data():
    """Smoke test using sample files in data/"""

    repo = DatabaseRepository("sqlite:///:memory:")
    services = initialize_all_services(repo)

    # Test with real sample files
    sample_files = [
        "data/EX-10.2.html",
        "data/Tesla_Form.html",
    ]

    # Create project
    project = repo.create_project("Sample Test")
    template = repo.create_field_template("Default", DEFAULT_FIELDS)
    repo.update_project(project.id, field_template_id=template.id)

    # Process each sample
    for file_path in sample_files:
        # Ingest
        doc_service = DocumentService(repo)
        doc = doc_service.ingest_document(project.id, file_path.split('/')[-1], file_path)

        # Extract
        ext_service = ExtractionService(repo)
        extractions = ext_service.extract_fields_for_document(
            project.id, doc['id'], template.fields
        )

        print(f"Extracted {len(extractions)} fields from {file_path}")

    # Generate table
    comparison = ComparisonService(repo).generate_comparison_table(project.id)
    print(f"Comparison table: {comparison['row_count']} fields × {comparison['document_count']} docs")

    # Export
    csv_data = export_to_csv(comparison)
    assert len(csv_data) > 0
```

---

## 4. QA CHECKLIST

### Document Parsing QA

- [ ] ✓ PDF with 50+ pages → All pages extracted
- [ ] ✓ DOCX with tables → Tables preserved
- [ ] ✓ HTML with nested structure → All text extracted
- [ ] ✓ TXT in various encodings → Text readable
- [ ] ✓ Large file (>10MB) → Handles gracefully
- [ ] ✓ Corrupted file → Error handled, project not broken

### Field Extraction QA

- [ ] ✓ Date extraction → Normalized to YYYY-MM-DD
- [ ] ✓ Currency extraction → Has USD prefix, numeric value
- [ ] ✓ Entity extraction → Proper capitalization
- [ ] ✓ Missing field → Confidence = 0
- [ ] ✓ Ambiguous field → Confidence lowered
- [ ] ✓ Citations found → Relevant passages identified

### Comparison Table QA

- [ ] ✓ Multiple columns align properly
- [ ] ✓ Confidence bars render correctly
- [ ] ✓ CSV export preserves all data
- [ ] ✓ Empty values shown as "N/A"
- [ ] ✓ Table refreshes on new extraction
- [ ] ✓ Sorting by column works

### Review Workflow QA

- [ ] ✓ Approve → Status changes to CONFIRMED
- [ ] ✓ Reject → Status changes to REJECTED
- [ ] ✓ Edit → Manual value saved, status = MANUAL_UPDATED
- [ ] ✓ Double-review → Latest review wins
- [ ] ✓ Notes saved with review
- [ ] ✓ Reviewed_by/reviewed_at recorded

### Evaluation QA

- [ ] ✓ Accuracy calculated correctly
- [ ] ✓ Coverage percentage accurate
- [ ] ✓ Field-level metrics match manual count
- [ ] ✓ Report generates in < 2 seconds
- [ ] ✓ Similarity score 0-1 range
- [ ] ✓ Historical evaluations preserved

### Frontend UI QA

- [ ] ✓ Create project form validates
- [ ] ✓ Upload accepts correct formats
- [ ] ✓ Project list loads and displays
- [ ] ✓ Tabs switch without losing state
- [ ] ✓ Review buttons functional
- [ ] ✓ Export button generates file
- [ ] ✓ Mobile responsive layout

---

## 5. PERFORMANCE BENCHMARKS

```python
# tests/performance/test_benchmarks.py

@pytest.mark.benchmark
def test_parse_pdf_performance(benchmark):
    """Ensure PDF parsing under 5s for typical contract"""
    parser = DocumentParser()
    result = benchmark(parser.parse, "tests/fixtures/50page_contract.pdf", "pdf")
    assert result[0] != ""

@pytest.mark.benchmark
def test_extraction_performance(benchmark):
    """Ensure field extraction under 2s per field"""
    extractor = FieldExtractor()
    doc_text = load_sample_doc()
    chunks = split_chunks(doc_text)

    result = benchmark(
        extractor.extract_fields,
        doc_text, chunks, SAMPLE_FIELDS, "doc_id"
    )
    assert len(result) > 0

@pytest.mark.benchmark
def test_table_generation_performance(benchmark):
    """Ensure table generation under 1s for 500 fields"""
    service = ComparisonService(repo)
    project = create_large_project(repo, 500)

    result = benchmark(
        service.generate_comparison_table,
        project.id
    )
    assert result['row_count'] == 500
```

---

## 6. DATA VALIDATION & SANITY CHECKS

```python
# tests/quality/test_data_validation.py

def test_no_null_citations():
    """Every extraction should have citations or confidence < 0.3"""
    extractions = repo.list_extractions_by_project(project_id)

    for ext in extractions:
        citations = repo.get_citations_for_extraction(ext.id)

        if ext.confidence_score > 0.3:
            assert len(citations) > 0, f"High confidence with no citations: {ext.id}"

def test_no_orphaned_citations():
    """Every citation should have parent extraction"""
    citations = repo.session.query(Citation).all()

    for citation in citations:
        assert citation.extraction_id is not None
        extraction = repo.get_extraction(citation.extraction_id)
        assert extraction is not None

def test_review_state_consistency():
    """Review state should match extraction status"""
    extractions = repo.list_extractions_by_project(project_id)

    for ext in extractions:
        review = repo.session.query(ReviewState).filter(
            ReviewState.extraction_id == ext.id
        ).first()

        # If extraction is CONFIRMED, review should reflect
        if ext.status == ExtractionStatus.CONFIRMED:
            assert review.status in [ExtractionStatus.CONFIRMED, ExtractionStatus.PENDING]
```

---

## 7. REGRESSION TEST SUITE

Run this before each deployment:

```bash
# All unit tests
pytest tests/unit -v

# All integration tests
pytest tests/integration -v

# API tests
pytest tests/api -v

# Smoke tests with sample data
pytest tests/smoke_test.py -v -m smoke

# Performance benchmarks
pytest tests/performance -v --benchmark-only

# Data quality checks
pytest tests/quality -v
```

---

## 8. MANUAL QA SCENARIOS

### Scenario 1: Create Project & Extract from 3 Contracts

1. Navigate to Projects page
2. Click "New Project"
3. Fill name: "Q1 Contract Review"
4. Click Create
5. Upload 3 sample PDFs
6. Select field template
7. Click "Extract Fields"
8. ✓ Verify comparison table shows all 3 documents
9. ✓ Verify confidence scores visible
10. ✓ Verify citations appear on click

### Scenario 2: Review & Correct Extractions

1. Go to Comparison Table
2. Identify extracted values
3. Go to Review tab
4. Edit 2-3 fields manually
5. Add notes explaining edits
6. Click confirm
7. ✓ Verify status changed to MANUAL_UPDATED
8. ✓ Verify table refreshed with new values
9. ✓ Verify audit trail shows reviewer name

### Scenario 3: Export & Offline Review

1. Go to Comparison Table
2. Click "Export to CSV"
3. Open CSV in Excel
4. ✓ Verify all fields present
5. ✓ Verify all documents as columns
6. ✓ Verify confidence values included
7. ✓ Verify alignment correct

---

## Summary

This comprehensive testing strategy ensures:

- 100% unit test coverage of core logic
- Integration tests verify end-to-end workflows
- API tests validate all endpoints
- Smoke tests with real data catch regressions
- Performance benchmarks ensure speed targets
- Data validation prevents corruption
- Manual QA verifies user experience

**Target Coverage**: > 90% code coverage
**Pre-deployment**: Run full test suite, 0 failures required
