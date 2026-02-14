# Quick Start Guide

Get the Legal Tabular Review system running in 10 minutes.

---

## 1. LOCAL SETUP (10 minutes)

### Prerequisites Check

```bash
# Check Python version
python --version       # Need: 3.10+
pip --version

# Check Node.js
node --version        # Need: 18+
npm --version
```

### Backend Setup (3 minutes)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn app:app --reload --port 8000
```

**Success indicator**: Terminal shows `Uvicorn running on http://127.0.0.1:8000`

### Frontend Setup (3 minutes)

In a **new terminal**:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start frontend
npm run dev
```

**Success indicator**: Terminal shows `Local: http://localhost:5173`

### Access the System (Immediately)

1. **Open browser**: `http://localhost:5173`
2. **You should see**: Empty project list with "New Project" button
3. **API Status**: `http://localhost:8000/docs` (Interactive API docs)

---

## 2. FIRST WORKFLOW (5 minutes)

### Step 1: Create a Project

1. Click **"New Project"** button
2. Fill in:
   - **Name**: "Test Contracts"
   - **Description**: "Testing the system"
3. Click **"Create"**
4. ✓ Project appears in list

### Step 2: Upload Documents

1. Click on the project
2. Go to **Documents** tab
3. **Drag & drop** or click to select files from `data/` folder:
   - `EX-10.2.html`
   - `Tesla_Form.html`
4. Wait for "INDEXED" status
5. ✓ Both documents appear in list

### Step 3: Extract Fields

1. Go to **"Comparison Table"** tab
2. Click **"Extract Fields"** button
3. Wait 30-60 seconds
4. ✓ Pre-configured field template automatically extracts:
   - Effective Date
   - Parties
   - Salary/Compensation
   - Job Title

### Step 4: Review Extractions

1. Go to **"Review"** tab
2. See pending extractions with AI values
3. Click **"Approve"** on each (or edit)
4. ✓ Status changes to CONFIRMED

### Step 5: View Comparison Table

1. Go back to **"Comparison Table"** tab
2. ✓ See side-by-side values from both documents
3. Click **"Export CSV"** to download spreadsheet

---

## 3. KEY FEATURES TO EXPLORE

### Field Templates

```
Create custom templates instead of using defaults:
1. Projects → Select project
2. Find template selector (Settings tab - coming soon)
3. Or use API: POST /templates
```

### Advanced Review

```
Edit extracted values manually:
1. Review tab → Click "Edit" button
2. Change value and add notes
3. Click "Save" → Status becomes MANUAL_UPDATED
```

### Quality Report

```
Get accuracy metrics:
1. Projects → Select project
2. Evaluation tab
3. See metrics dashboard:
   - Average confidence
   - Field accuracy
   - Coverage percentage
```

---

## 4. SAMPLE WORKFLOW COMMANDS

### Quick API Test

```bash
# Create project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "description": "Quick test"}'

# Expected: Returns project with ID like "proj-001"
```

### Using Python SDK

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Create project
project = requests.post(f"{BASE_URL}/projects", json={
    "name": "My Contracts",
    "description": "Review contracts"
}).json()

project_id = project['id']
print(f"Created: {project_id}")

# List documents
docs = requests.get(f"{BASE_URL}/projects/{project_id}/documents").json()
print(f"Documents: {docs['total']}")

# View comparison table
table = requests.get(f"{BASE_URL}/projects/{project_id}/table").json()
print(f"Comparison: {table['row_count']} fields × {table['document_count']} docs")
```

---

## 5. COMMON TASKS

### Task: Add More Documents

```
1. Project → Documents tab
2. Click "+" or drag-drop new file
3. Supported formats: PDF, DOCX, HTML, TXT
4. Max size: 100MB
5. Click Extract after uploading
```

### Task: Export Results

```
1. Project → Comparison Table tab
2. Click "Export CSV"
3. Opens in Excel/Google Sheets
4. Includes confidence scores and page references
```

### Task: Review with Team

```
1. Project → Review tab
2. Each extraction shows AI value + confidence
3. Team members can approve/edit/reject
4. All changes tracked with timestamp
```

### Task: Generate Quality Report

```
1. Project → Evaluation tab
2. Shows accuracy metrics automatically
3. Field-level breakdown showing:
   - Extraction accuracy
   - Confidence scores
   - Comparison consistency
```

---

## 6. TROUBLESHOOTING

| Problem                            | Solution                                                                |
| ---------------------------------- | ----------------------------------------------------------------------- |
| "Blank page in browser"            | Restart: `npm run dev` in frontend folder                               |
| "Connection refused on API"        | Check backend running: `lsof -i :8000` (macOS)                          |
| "No documents appear after upload" | Wait 10 seconds, refresh page, or check backend logs                    |
| "Extraction gives low confidence"  | Verify document text is readable (not scanned PDF)                      |
| "Port 8000/5173 already in use"    | Use different: `--port 8001` for backend, `-- --port 5174` for frontend |

---

## 7. FILE LOCATIONS

```
Foundation Files:
├── backend/
│   ├── app.py                 ← Main API server
│   ├── requirements.txt        ← Python dependencies
│   └── src/
│       ├── models/            ← Database schemas
│       ├── services/          ← Business logic
│       └── storage/           ← Database access
│
├── frontend/
│   ├── package.json           ← NPM dependencies
│   ├── vite.config.ts         ← Build config
│   ├── src/
│   │   ├── App.tsx            ← Main React component
│   │   ├── pages/             ← Page components
│   │   ├── components/        ← Reusable components
│   │   └── services/          ← API client
│   └── .env.local             ← Frontend config
│
├── data/
│   ├── EX-10.2.html          ← Sample documents
│   └── Tesla_Form.html
│
└── docs/
    ├── ARCHITECTURE.md        ← System design
    ├── FUNCTIONAL_DESIGN.md   ← Feature specs
    ├── API_REFERENCE.md       ← API documentation
    ├── DEPLOYMENT.md          ← Production setup
    ├── TESTING_QA.md          ← Test strategy
    ├── TROUBLESHOOTING.md     ← FAQ & fixes
    └── README.md              ← Overview
```

---

## 8. NEXT STEPS

### For Testing

```bash
# Run backend tests
cd backend
pytest tests/ -v

# Run frontend tests
cd frontend
npm test
```

### For Production

```bash
Read: docs/DEPLOYMENT.md
- Docker Compose setup
- Cloud deployment (AWS, Heroku)
- Database migration
- SSL/HTTPS setup
```

### For Advanced Usage

```bash
Read: docs/API_REFERENCE.md
- All 20+ API endpoints
- Python SDK examples
- Request/response samples
- Error handling
```

---

## 9. KEYBOARD SHORTCUTS

| Shortcut                                   | Action                                 |
| ------------------------------------------ | -------------------------------------- |
| `Ctrl+K`                                   | Clear console / focus search           |
| `F12`                                      | Developer tools (see network requests) |
| `Cmd+Shift+K` (Mac) / `Ctrl+Shift+K` (Win) | Clear terminal                         |

---

## 10. WHAT TO TRY NEXT

**✓ Already Tried:**

- Create project
- Upload documents
- Extract fields
- Review extractions
- Export CSV

**Try Next:**

1. **Edit extraction values** in Review tab and see status change
2. **Export to CSV** and open in Excel
3. **Check API docs** at http://localhost:8000/docs
4. **Read ARCHITECTURE.md** to understand data flow
5. **Run backend tests** to verify setup: `pytest tests/unit -v`

---

## SUPPORT

**Documentation:**

- `docs/ARCHITECTURE.md` - How the system works
- `docs/API_REFERENCE.md` - All API endpoints
- `docs/TROUBLESHOOTING.md` - Common issues
- `docs/DEPLOYMENT.md` - Production setup

**Logs:**

- Backend: Check terminal where you ran `uvicorn app:app`
- Frontend: Open browser DevTools (F12) → Console tab
- Database: Check SQLite file at `backend/legal_review.db`

---

## ESTIMATED TIME FOR FULL SETUP

| Task                    | Time            |
| ----------------------- | --------------- |
| Python environment      | 2 min           |
| Backend dependencies    | 1 min           |
| Frontend dependencies   | 2 min           |
| Start both servers      | 1 min           |
| Create first project    | 1 min           |
| Upload sample documents | 2 min           |
| Extract fields          | 1 min           |
| **TOTAL**               | **~10 minutes** |

---

You now have a working system! 🎉

Next, explore the documentation or jump to production deployment in `docs/DEPLOYMENT.md`.
