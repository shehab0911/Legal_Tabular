# Legal Tabular Review System - Architecture & Design

## System Overview

The Legal Tabular Review is a production-grade system for extracting key fields from multiple legal documents and presenting them in a structured table for side-by-side comparison and review. The system emphasizes consistent field extraction, normalization to a unified schema, and review workflows with field templates.

### Core Vision

- **Input**: Multiple legal documents (PDF, DOCX, HTML, TXT)
- **Output**: Structured comparison tables with field-aligned data, citations, confidence scores
- **Purpose**: Enable legal teams to quickly compare key terms across multiple contracts, regulations, and related documents

---

## 1. PRODUCT & DATA MODEL ALIGNMENT

### 1.1 End-to-End Data Flow

```
User Creates Project
    ↓
User uploads field template (defines fields to extract)
    ↓
User uploads documents (PDF/DOCX/HTML/TXT)
    ↓
Document Parsing & Indexing (chunks created)
    ↓
Field Extraction (with citations + confidence + normalization)
    ↓
Extraction Results Stored (in DB with review states)
    ↓
User Reviews Extractions (approve/reject/manual edit)
    ↓
Comparison Table Generated (all documents side-by-side)
    ↓
Quality Evaluation (AI vs human comparison)
    ↓
Reports & Analytics Generated
```

### 1.2 Data Model

#### Projects (Core Container)

- **id**: UUID primary key
- **name**: Project identifier
- **description**: Optional project details
- **status**: CREATED, INGESTING, INDEXING, READY, EXTRACTING, REVIEW_PENDING, COMPLETED, ERROR
- **field_template_id**: Reference to field template
- **created_at, updated_at**: Timestamps
- **Relationships**: HasMany Documents, HasMany Extractions, HasMany ReviewStates

#### Documents (Input Source)

- **id**: UUID
- **project_id**: FK to Project
- **filename, file_type, file_path, file_size**: File metadata
- **content_text**: Full parsed text content
- **parsed_metadata**: Extraction metadata (author, title, pages, etc.)
- **status**: UPLOADED, PARSING, INDEXED, EXTRACTED, ERROR
- **Relationships**: HasMany Chunks, HasMany Citations

#### DocumentChunks (Indexing Layer)

- **id**: UUID
- **document_id**: FK
- **chunk_index**: Position in document
- **text**: Chunk content (1000-word chunks with 100-word overlap)
- **page_number, section_title**: Location metadata
- **embedding**: Optional vector embedding for similarity search
- **Relationships**: BelongsTo Document

#### FieldTemplates (Schema Definition)

- **id**: UUID
- **name**: Template name
- **description**: Template documentation
- **version**: Versioning for template updates (triggers re-extraction)
- **fields**: JSON array of FieldDefinition objects
- **is_active**: Boolean for template status
- **created_at, updated_at**: Timestamps

#### FieldDefinition (Schema Item)

```json
{
  "name": "effective_date",
  "display_name": "Effective Date",
  "field_type": "DATE",
  "description": "The date the contract becomes effective",
  "required": true,
  "normalization_rules": {
    "format": "YYYY-MM-DD",
    "timezone": "UTC"
  },
  "validation_rules": {
    "not_future": true,
    "not_before": "2000-01-01"
  },
  "examples": ["2024-01-15", "January 15, 2024"]
}
```

#### ExtractionResult (Extraction Output)

- **id**: UUID
- **project_id, document_id**: FK references
- **field_name**: Which field was extracted
- **field_type**: Date, Currency, Entity, Text, etc.
- **extracted_value**: Raw extracted text
- **raw_text**: Source text from document
- **normalized_value**: Cleaned/standardized value
- **confidence_score**: 0.0-1.0 confidence level
- **status**: PENDING, EXTRACTED, CONFIRMED, REJECTED, MANUAL_UPDATED, MISSING_DATA
- **metadata**: Additional extraction context
- **Relationships**: HasMany Citations, HasOne ReviewState

#### Citations (Audit Trail)

- **id**: UUID
- **extraction_id**: FK to ExtractionResult
- **document_id, chunk_id**: Location references
- **citation_text**: Evidence supporting extraction (first 500 chars)
- **page_number, section_title**: Location metadata
- **relevance_score**: 0.0-1.0 relevance to extracted field
- **created_at**: Creation timestamp

#### ReviewState (Auditability)

- **id**: UUID
- **project_id, extraction_id**: FK references (extraction_id is unique)
- **status**: PENDING, CONFIRMED, REJECTED, MANUAL_UPDATED
- **ai_value**: AI-generated extraction
- **manual_value**: User-provided correction
- **reviewer_notes**: Notes from reviewer
- **confidence_score**: Combined confidence metric
- **reviewed_at, reviewed_by**: Audit metadata

#### Annotations (Collaboration)

- **id**: UUID
- **extraction_id**: FK
- **comment_text**: Annotation content
- **annotated_by, created_at, updated_at**: Audit trail

#### Tasks (Async Processing)

- **id**: UUID
- **task_type**: "ingest", "extract", "evaluate"
- **project_id**: Optional FK
- **status**: QUEUED, PROCESSING, COMPLETED, FAILED
- **result**: JSON result payload
- **error_message**: Error details if failed
- **created_at, started_at, completed_at**: Timeline

#### EvaluationResults (Quality Metrics)

- **id**: UUID
- **project_id, document_id**: FK references
- **field_name, ai_value, human_value**: Comparison data
- **match_score**: 0.0-1.0 similarity score
- **normalized_match**: Boolean (> 0.8 threshold)
- **notes**: Qualitative assessment

### 1.3 Status Transitions

**Project Status Flow**:

```
CREATED → INGESTING → INDEXING → READY → EXTRACTING → REVIEW_PENDING → COMPLETED
                                                    ↓
                                                  ERROR
```

**Extraction Status Flow**:

```
PENDING → EXTRACTED → [CONFIRMED | REJECTED | MANUAL_UPDATED | MISSING_DATA]
                    ↓
                  REVIEW_PENDING
```

**Document Status Flow**:

```
UPLOADED → PARSING → INDEXED → EXTRACTED
                ↓         ↓
              ERROR    ERROR
```

---

## 2. DOCUMENT INGESTION & PARSING

### 2.1 Supported Formats

| Format   | Parser         | Features                                                    |
| -------- | -------------- | ----------------------------------------------------------- |
| **PDF**  | PyPDF2         | Page extraction, metadata extraction, page numbers          |
| **DOCX** | python-docx    | Paragraph extraction, table extraction, document properties |
| **HTML** | BeautifulSoup4 | DOM parsing, metadata tags, text cleaning                   |
| **TXT**  | Native         | Encoding detection, simple text extraction                  |

### 2.2 Parsing Pipeline

```python
1. File Upload Validation
   - Check file extension against whitelist
   - Validate file size (max 50MB)
   - Verify MIME type

2. Document Parsing
   - Extract text content using format-specific parser
   - Preserve structure (pages, sections, tables)
   - Extract metadata (title, author, creation date)

3. Content Preservation
   - Store full text in `content_text` field
   - Record page numbers for citations
   - Extract section headings for context

4. Metadata Recording
   - parsed_metadata JSON:
     {
       "format": "pdf",
       "pages": 42,
       "title": "Contract",
       "author": "ABC Corp",
       "word_count": 15230
     }
```

### 2.3 Chunking Strategy

All documents are automatically chunked for indexing:

```python
class DocumentChunker:
    def __init__(self, chunk_size=1000, overlap=100):
        # chunk_size: words per chunk (configurable)
        # overlap: words repeated between consecutive chunks

    def chunk(self, text, metadata):
        # Algorithm:
        # 1. Split text into sentences
        # 2. Group sentences into chunks (~1000 words)
        # 3. Add 100-word overlap between chunks
        # 4. Record page and section metadata
        # Returns: List of chunk dicts with text, page_number, section_title
```

**Example Chunk Structure**:

```json
{
  "chunk_index": 5,
  "text": "Lorem ipsum dolor sit amet... [1000 words] ...consectetur adipiscing elit.",
  "page_number": 3,
  "section_title": "PAYMENT TERMS",
  "word_count": 1002,
  "metadata": {
    "sentence_count": 18,
    "line_count": 45
  }
}
```

### 2.4 New Document Handling

When a new document is added to an existing project:

1. **New Extraction**: Extract fields using current field template
2. **Preserve Existing**: Keep previous extractions intact
3. **Update Comparison**: Regenerate comparison table with new data
4. **Track Changes**: Record document ingestion timestamp
5. **Rollback Capability**: Old extractions remain for audit trail

---

## 3. FIELD TEMPLATE & SCHEMA MANAGEMENT

### 3.1 Field Template Structure

Field templates define what to extract and how to validate/normalize results.

```python
class FieldTemplate:
    id: str
    name: str = "Contract Review Template v1"
    description: str = "Extract key contract terms"
    version: int = 1  # Increment on updates
    fields: List[FieldDefinition]
    is_active: bool = True
```

### 3.2 Field Definition Structure

```python
@dataclass
class FieldDefinition:
    name: str = "effective_date"  # Unique identifier
    display_name: str = "Effective Date"  # User-friendly
    field_type: FieldType = FieldType.DATE  # Data type
    description: str = "When contract becomes effective"
    required: bool = True

    # Field validation rules
    validation_rules: Dict[str, Any] = {
        "not_future": True,
        "not_before": "2000-01-01",
        "format": "YYYY-MM-DD"
    }

    # Normalization configuration
    normalization_rules: Dict[str, Any] = {
        "target_format": "YYYY-MM-DD",
        "timezone": "UTC",
        "strip_whitespace": True
    }

    # Field examples for prompt engineering
    examples: List[str] = [
        "January 15, 2024",
        "2024-01-15",
        "15/01/2024"
    ]
```

### 3.3 Supported Field Types

| Type             | Description         | Normalization         | Validation        |
| ---------------- | ------------------- | --------------------- | ----------------- |
| **DATE**         | Calendar dates      | YYYY-MM-DD format     | Date range checks |
| **CURRENCY**     | Money values        | USD XXX.XX            | Positive checks   |
| **PERCENTAGE**   | Percentages         | 0-100                 | Range 0-100       |
| **ENTITY**       | Names/organizations | Proper capitalization | Format checks     |
| **BOOLEAN**      | Yes/No values       | true/false            | Binary validation |
| **MULTI_SELECT** | Multiple options    | Normalize to list     | Option whitelist  |
| **TEXT**         | Freeform text       | Trim whitespace       | Length limits     |
| **FREEFORM**     | Any text            | No normalization      | No validation     |

### 3.4 Template Versioning & Re-extraction

When template is updated:

1. **Create New Version**: Increment version number
2. **Mark Old Version**: Keep for audit trail
3. **Trigger Re-extraction**: Background job re-extracts all documents
4. **Update Extractions**: New field values replace old ones
5. **Preserve History**: Old review states remain for comparison

```python
# Workflow:
template = get_template("template_id")
template.version = template.version + 1
template.fields = new_field_list
save(template)

# Background job:
for each project with this template:
    for each document:
        run_extraction(document, template.fields)
        update_extraction_results()
        reset_review_states()
```

---

## 4. FIELD EXTRACTION WORKFLOW

### 4.1 Extraction Methods

The system supports two extraction approaches:

#### Method 1: LLM-Based (Recommended)

```python
def extract_with_llm(document_text: str, field_def: FieldDefinition) -> ExtractionResult:
    prompt = f"""
    Extract the following field from legal document:

    Field: {field_def.display_name}
    Type: {field_def.field_type}
    Description: {field_def.description}
    Examples: {field_def.examples}

    Document text:
    {document_text[:5000]}

    Return JSON:
    {{
      "value": "extracted value",
      "raw_text": "source text from document",
      "confidence": 0.0-1.0,
      "reasoning": "why this value"
    }}
    """

    response = llm_client.complete(prompt)
    result = parse_json(response)
    return ExtractionResult(
        extracted_value=result['value'],
        raw_text=result['raw_text'],
        confidence_score=result['confidence'],
        metadata={'method': 'llm', 'reasoning': result['reasoning']}
    )
```

#### Method 2: Heuristic/Regex-Based (Fallback)

```python
def extract_with_heuristics(document_text: str, field_name: str) -> ExtractionResult:
    patterns = {
        'effective_date': [
            r'effective\s+(?:date)?[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})'
        ],
        'parties': [
            r'between\s+([A-Z][A-Za-z\s&.,]+?)\s+and'
        ],
        'currency': [
            r'\$[\d,]+\.?\d*'
        ]
    }

    for pattern in patterns.get(field_name, []):
        matches = re.finditer(pattern, document_text, re.IGNORECASE)
        for match in matches:
            value = match.group(1) if match.groups() else match.group(0)
            # Score based on pattern confidence
            confidence = 0.5 + pattern_confidence_boost
            return ExtractionResult(
                extracted_value=value.strip(),
                confidence_score=confidence,
                metadata={'method': 'heuristic', 'pattern': pattern}
            )
```

### 4.2 Citation Finding

For each extracted field, the system finds supporting citations:

```python
def find_citations(extracted_value: str, document_chunks: List[Chunk]) -> List[Citation]:
    citations = []

    # Score chunks by relevance using:
    # 1. Direct text match (highest confidence)
    # 2. Jaccard similarity on tokens
    # 3. Semantic similarity (if embeddings available)

    for chunk in document_chunks:
        if extracted_value in chunk.text:
            similarity = 1.0  # Direct match
        else:
            # Jaccard similarity
            query_tokens = set(extracted_value.lower().split())
            chunk_tokens = set(chunk.text.lower().split())
            intersection = len(query_tokens & chunk_tokens)
            union = len(query_tokens | chunk_tokens)
            similarity = intersection / max(1, union)

        if similarity > 0:
            citations.append(Citation(
                citation_text=chunk.text[:500],
                relevance_score=similarity,
                page_number=chunk.page_number,
                section_title=chunk.section_title
            ))

    # Return top-3 by relevance
    return sorted(citations, key=lambda c: c.relevance_score, reverse=True)[:3]
```

### 4.3 Normalization & Validation

Each extracted value is normalized and validated:

```python
def normalize_and_validate(
    extracted_value: str,
    field_def: FieldDefinition
) -> Tuple[str, float]:  # (normalized_value, confidence_adjustment)

    # Step 1: Normalization
    if field_def.field_type == FieldType.DATE:
        normalized = normalize_date(extracted_value)  # → YYYY-MM-DD
        confidence_adj = 1.0 if normalized else 0.5

    elif field_def.field_type == FieldType.CURRENCY:
        normalized = normalize_currency(extracted_value)  # → USD X,XXX.XX
        confidence_adj = 1.0 if normalized else 0.5

    elif field_def.field_type == FieldType.BOOLEAN:
        normalized = normalize_boolean(extracted_value)  # → true/false
        confidence_adj = 1.0 if normalized else 0.3

    else:
        normalized = extracted_value.strip()
        confidence_adj = 0.8

    # Step 2: Validation
    if not validate(normalized, field_def.validation_rules):
        confidence_adj *= 0.7  # Penalty for failed validation

    return normalized, confidence_adj
```

### 4.4 Confidence Scoring

Confidence score combines multiple factors:

```python
def calculate_confidence(extraction: ExtractionResult) -> float:
    # Base confidence from extraction method
    if extraction.method == 'llm':
        base_confidence = extraction.llm_confidence   # 0.0-1.0
    else:
        base_confidence = 0.5  # Heuristic baseline

    # Adjustments
    citation_boost = 0.1 if len(extraction.citations) >= 2 else 0
    normalization_score = 1.0 if extraction.normalized_value else 0.6
    validation_score = 1.0 if validation_passed else 0.7

    # Combined
    final_confidence = base_confidence * (
        (normalization_score + validation_score) / 2
    ) + citation_boost

    return min(1.0, final_confidence)
```

---

## 5. TABULAR COMPARISON & REVIEW

### 5.1 Comparison Table Structure

The comparison table aligns fields across documents:

```
Field Name    | Field Type | Document A            | Document B            | Document C
              |            | Value | Conf | Status | Value | Conf | Status | Value | Conf | Status
────────────────────────────────────────────────────────────────────────────────────────────────────
Effective     | DATE       | 2024-01-15 | 95% ✓  | 2024-01-15 | 85% ✓  | 2024-02-01 | 70% ?
Date          |            |            |        |            |        |             |
Parties       | ENTITY     | ABC Corp & | 92% ✓  | ABC Corp & | 88% ✓  | ABC Corp   | 65% !
              |            | XYZ Inc    |        | XYZ Inc    |        | (incomplete)|
Payment       | CURRENCY   | USD 50,000 | 98% ✓  | USD 45,000 | 90% ✓  | USD 50,000 | 75% ✓
Terms         |            |            |        |            |        |             |
...
```

### 5.2 Table Generation Algorithm

```python
def generate_comparison_table(project_id: str) -> ComparisonTable:
    documents = get_project_documents(project_id)
    extractions = get_project_extractions(project_id)

    # Group by field
    field_groups = {}
    for extraction in extractions:
        if extraction.field_name not in field_groups:
            field_groups[extraction.field_name] = {
                'field_type': extraction.field_type,
                'results': {}
            }
        field_groups[extraction.field_name]['results'][
            extraction.document_id
        ] = extraction

    # Create rows
    rows = []
    for field_name, group in field_groups.items():
        row = TableRow(
            field_name=field_name,
            field_type=group['field_type'],
            document_results={
                doc.id: group['results'].get(doc.id)
                for doc in documents
            }
        )
        rows.append(row)

    return ComparisonTable(
        project_id=project_id,
        rows=rows,
        generation_timestamp=datetime.now()
    )
```

### 5.3 Review States & Transitions

Each extraction has a associated review state:

```
PENDING → Review Action
          ├─ CONFIRMED: AI value approved, no changes
          ├─ REJECTED: AI value incorrect, value marked missing
          ├─ MANUAL_UPDATED: Manual correction provided
          └─ MISSING_DATA: Field not present in document
```

Review State Lifecycle:

```python
class ReviewState:
    # Initial
    status = ExtractionStatus.PENDING
    ai_value = extraction.extracted_value
    manual_value = None

    # After Review
    async def confirm():
        self.status = ExtractionStatus.CONFIRMED
        self.reviewed_at = now()
        self.reviewed_by = current_user

    async def reject():
        self.status = ExtractionStatus.REJECTED
        self.reviewed_at = now()
        self.reviewed_by = current_user

    async def manual_update(new_value: str, notes: str):
        self.status = ExtractionStatus.MANUAL_UPDATED
        self.manual_value = new_value
        self.reviewer_notes = notes
        self.reviewed_at = now()
        self.reviewed_by = current_user
```

### 5.4 Audit Trail

Auditability is maintained through:

1. **Before/After Values**: Both AI and manual values stored
2. **Timestamps**: Creation, review, modification times recorded
3. **User Attribution**: Reviewer identification
4. **Decision Rationale**: Optional notes explaining decisions
5. **Citation Preservation**: Original citations linked to each extraction

---

## 6. QUALITY EVALUATION

### 6.1 Evaluation Workflow

Evaluation compares AI-extracted values against human-labeled ground truth:

```python
def evaluate_project(
    project_id: str,
    evaluation_data: List[{
        document_id: str,
        field_name: str,
        human_value: str
    }]
):
    for item in evaluation_data:
        # Get AI extraction
        extraction = get_extraction(
            project_id, item['document_id'], item['field_name']
        )
        ai_value = extraction.normalized_value or extraction.extracted_value
        human_value = item['human_value']

        # Calculate match score
        match_score = calculate_similarity(ai_value, human_value)
        normalized_match = match_score > 0.8

        # Store evaluation
        store_evaluation(
            project_id=project_id,
            field_name=item['field_name'],
            ai_value=ai_value,
            human_value=human_value,
            match_score=match_score,
            normalized_match=normalized_match
        )
```

### 6.2 Evaluation Metrics

#### Field-Level Accuracy

```
accuracy = (matched_fields / total_fields) * 100
Where matched_fields have match_score > 0.8
```

#### Coverage

```
coverage = (fields_with_extractions / total_fields) * 100
```

#### Normalization Validity

```
valid_normalizations = count(successful_normalizations)
normalization_rate = valid_normalizations / total_extractions
```

#### Confidence Calibration

```
For each confidence bucket:
  actual_accuracy = matched / total_in_bucket
  calibration_error = |confidence - actual_accuracy|

avg_calibration_error = mean(all_calibration_errors)
```

### 6.3 Evaluation Report

```python
@dataclass
class EvaluationReport:
    project_id: str
    metrics: EvaluationMetrics = {
        'total_fields': 150,
        'matched_fields': 138,
        'field_accuracy': 0.92,
        'coverage': 0.95,
        'average_confidence': 0.87,
        'normalization_success': 0.98
    }
    field_results: List[FieldEvaluation] = [
        {
            'field_name': 'effective_date',
            'total': 10,
            'matched': 10,
            'accuracy': 1.0,
            'avg_confidence': 0.94
        },
        ...
    ]
    timestamp: datetime
```

### 6.4 Similarity Scoring

```python
def calculate_similarity(ai_value: str, human_value: str) -> float:
    if not ai_value or not human_value:
        return 1.0 if ai_value == human_value else 0.0

    # Normalize both values
    ai_norm = str(ai_value).lower().strip()
    human_norm = str(human_value).lower().strip()

    # Exact match
    if ai_norm == human_norm:
        return 1.0

    # Levenshtein distance
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, ai_norm, human_norm).ratio()

    return ratio
```

---

## 7. OPTIONAL DIFF & ANNOTATION LAYER

### 7.1 Diff Highlighting

For each field, highlight differences across documents:

```python
def compute_diff(field_values: Dict[str, str]) -> Dict[str, Any]:
    """
    Returns: {
        'field_name': 'effective_date',
        'values': {
            'doc_1': '2024-01-15',
            'doc_2': '2024-01-20',
            'doc_3': '2024-01-15'
        },
        'differences': [
            {'doc_ids': ['doc_1', 'doc_3'], 'value': '2024-01-15'},
            {'doc_ids': ['doc_2'], 'value': '2024-01-20', 'highlighted': True}
        ]
    }
    """
```

### 7.2 Annotations & Comments

Annotations are stored separately from extractions:

```python
class Annotation:
    id: str
    extraction_id: str
    comment_text: str
    annotated_by: str
    created_at: datetime
    updated_at: datetime

    # Annotations never modify underlying extraction
    # They are advisory/collaborative only
```

**Workflow**:

1. User views extraction result
2. User adds comment/annotation
3. Comment displayed alongside extraction
4. Other users see comment
5. Extraction value unchanged

---

## 8. FRONTEND EXPERIENCE

### 8.1 User Screens

#### 1. Project List Page

- View all projects in grid/list format
- Status indicators (CREATED, READY, COMPLETED, ERROR)
- Quick stats (documents, extractions)
- Create new project button
- Edit/delete project actions

#### 2. Project Detail Page (Main Hub)

5 tabs:

**A. Documents Tab**

- Upload document form (drag-drop support)
- List of uploaded documents with status
- File size and type info
- Actions: Delete, Re-extract
- Extract all button

**B. Comparison Table Tab**

- Horizontal table with field rows
- Document columns side-by-side
- Extract values with confidence bars
- Color-coded status (confirmed=green, rejected=red)
- Export to CSV/Excel button
- Sort/filter options

**C. Review Tab**

- Pending reviews list
- Review form with:
  - Field name and AI value
  - Action buttons: Approve/Reject/Edit
  - Manual value textarea
  - Notes textarea
  - Confident score display

**D. Evaluation Tab**

- Accuracy metrics dashboard
- Field-by-field performance table
- Visualization: accuracy vs confidence curve
- Table of evaluation results

**E. Settings Tab**

- Project name/description edit
- Field template selection/binding
- Project template management
- Re-extraction triggers

### 8.2 Key User Interactions

#### Workflow 1: Create Project & Extract

```
1. Click "New Project"
2. Fill name, description, select template
3. Upload documents
4. System auto-indexes, shows "Indexed" status
5. Click "Extract Fields"
6. System extracts, shows results in table
7. Go to Review tab to approve/modify
```

#### Workflow 2: Review & Compare

```
1. Go to Comparison Table tab
2. See all extracted fields side-by-side
3. Identify differences between documents
4. Click on field to expand details + citations
5. Click "Edit" to make manual corrections
6. System re-calculates confidence
7. Export table to CSV for offline review
```

#### Workflow 3: Evaluate Quality

```
1. Go to Evaluation tab
2. See accuracy metrics
3. View field-level performance
4. Upload reference data (human extractions)
5. System compares and generates report
6. Identify low-accuracy fields
7. Retrain or adjust template
```

---

## 9. BACKEND SERVICE ARCHITECTURE

### 9.1 Layered Architecture

```
┌─────────────────────────────────────┐
│     HTTP REST API Layer (FastAPI)   │
├─────────────────────────────────────┤
│  Service Layer                      │
│  • ProjectService                   │
│  • DocumentService                  │
│  • ExtractionService                │
│  • ReviewService                    │
│  • ComparisonService                │
│  • EvaluationService                │
│  • TaskService                      │
├─────────────────────────────────────┤
│  Business Logic Layer               │
│  • DocumentParser                   │
│  • DocumentChunker                  │
│  • FieldExtractor                   │
│  • ValueNormalizer                  │
│  • SimilarityCalculator             │
├─────────────────────────────────────┤
│  Repository Layer (Data Access)     │
│  • DatabaseRepository               │
│  • Query builders & persistence     │
├─────────────────────────────────────┤
│  Database Layer                     │
│  • SQLAlchemy ORM                   │
│  • SQLite/PostgreSQL                │
└─────────────────────────────────────┘
```

### 9.2 Key Services

**ProjectService**: Project CRUD operations
**DocumentService**: Document ingestion and parsing
**ExtractionService**: Field extraction orchestration
**ReviewService**: Review workflow management
**ComparisonService**: Table generation
**EvaluationService**: Quality evaluation
**TaskService**: Async task tracking

### 9.3 Async Processing

Long-running operations use background tasks:

```python
# Endpoint triggers task
@app.post("/projects/{project_id}/extract")
async def extract_fields(project_id: str, background_tasks: BackgroundTasks):
    task = Task.create(type="extract", project_id=project_id)
    background_tasks.add_task(
        run_extraction_background,
        project_id,
        task.id
    )
    return {"task_id": task.id, "status": "started"}

# Background function
def run_extraction_background(project_id: str, task_id: str):
    task.update(status="PROCESSING")
    try:
        result = extraction_service.extract_all(project_id)
        task.update(status="COMPLETED", result=result)
    except Exception as e:
        task.update(status="FAILED", error=str(e))
```

---

## 10. API ENDPOINTS

### Projects

- `POST /projects` - Create project
- `GET /projects` - List all projects
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project

### Documents

- `POST /projects/{id}/documents/upload` - Upload document
- `GET /projects/{id}/documents` - List project documents

### Field Templates

- `POST /field-templates` - Create template
- `GET /field-templates` - List templates
- `PUT /field-templates/{id}` - Update template

### Extraction

- `POST /projects/{id}/extract` - Start extraction
- `GET /extractions/{id}` - Get extraction details
- `PUT /extractions/{id}/review` - Review extraction

### Comparison

- `GET /projects/{id}/table` - Get comparison table
- `POST /projects/{id}/table/export-csv` - Export to CSV

### Evaluation

- `POST /projects/{id}/evaluate` - Start evaluation
- `GET /projects/{id}/evaluation-report` - Get report

### Tasks

- `GET /tasks/{id}` - Get task status

---

## 11. DEPLOYMENT & OPERATIONS

### Production Checklist

- [ ] Database: Use PostgreSQL (not SQLite)
- [ ] Cache: Implement Redis for session/task state
- [ ] LLM: Configure API keys (OpenAI, Anthropic, etc.)
- [ ] Storage: Use S3 for document files
- [ ] Monitoring: Implement logging and alerting
- [ ] Security: CORS, rate limiting, auth
- [ ] Testing: Unit + integration tests
- [ ] Documentation: API docs, deployment guide

### Environment Configuration

```
DATABASE_URL=postgresql://user:pass@host:5432/legal_db
LLM_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
S3_BUCKET=legal-documents-prod
DEBUG=false
```

---

## 12. PERFORMANCE & SCALABILITY

### Optimization Strategies

1. **Chunking**: Pre-chunked documents enable faster retrieval
2. **Indexing**: Database indices on project_id, document_id, field_name
3. **Caching**: Redis cache for field templates, frequently used extractions
4. **Parallelization**: Extract multiple documents concurrently
5. **Batch Processing**: Process multiple fields per LLM call

### Scaling Considerations

- **Horizontal Scaling**: Multiple API servers behind load balancer
- **Async Workers**: Celery/RQ for background tasks
- **Database Replication**: Primary-replica PostgreSQL setup
- **CDN**: Static assets (frontend)
- **Vector Store**: Optional Pinecone/Weaviate for semantic search

---

## End-to-End Example

**User Journey: Extract Contract Terms**

```
1. User creates project "Q1 2024 Contracts"
2. User selects template with fields:
   - Effective Date
   - Liability Cap
   - Payment Terms

3. User uploads 5 PDF contracts
4. System automatically:
   - Parses each PDF (content + metadata)
   - Creates 50 chunks per document
   - Stores in database

5. User clicks "Extract Fields"
6. System:
   - Sends "extract effective_date" to LLM for each doc
   - Gets back values: "2024-01-15", "2024-01-10", etc.
   - Finds citations from chunks
   - Calculates confidence scores
   - Stores ExtractionResults

7. Comparison table shows:
   ┌────────────────┬──────┬──────┬──────┬──────┬──────┐
   │ Effective Date │ Doc1 │ Doc2 │ Doc3 │ Doc4 │ Doc5 │
   ├────────────────┼──────┼──────┼──────┼──────┼──────┤
   │                │ 2024-│ 2024-│ 2024-│ 2024-│ 2024-│
   │                │ 01-15│ 01-10│ 01-15│ 02-01│ 01-15│
   │                │ 95%  │ 88%  │ 92%  │ 70%  │ 94% │
   └────────────────┴──────┴──────┴──────┴──────┴──────┘

8. User reviews:
   - Approves Doc1-5 (all have dates)
   - Notes Doc4 date might be wrong (only 70% confidence)
   - Manually corrects Doc4 to "2024-01-15"

9. User compares with liability caps:
   - Sees significant difference in Doc3 ($1M vs $5M in others)
   - Flags for legal review

10. System exports CSV with all fields, values, confidence, status

Done! ✓
```

This comprehensive architecture provides a production-ready system for legal document analysis with full auditability, flexibility, and scalability.
