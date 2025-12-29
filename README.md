# ESG Data Extraction System

**AI-Powered ESG Data Extraction from Bank Sustainability Reports**

Advanced system for extracting Environmental, Social, and Governance (ESG) indicators from 400+ page bank sustainability reports using vector search and AI.

## Key Features

- **Fast Vector Search Mode (Recommended)**: Semantic search + AI extraction
  - Uses sentence-transformers for local embeddings
  - Searches 400 pages in <1 second after initial indexing
  - ~6-10 seconds per indicator extraction
  - Caches embeddings for instant reuse
- **Agent Mode**: Autonomous AI with specialized tools
- **Simple Mode**: Basic extraction workflow
- **20 ESG Indicators**: Environmental + Social + Governance + ESRS2
- **Modern React UI**: Beautiful dark theme with real-time progress
- **FastAPI Backend**: RESTful API with auto-docs
- **SQLite Database**: Persistent storage with confidence scores
- **Auto CSV Export**: Timestamped + latest versions

## Target Banks & Reports

| Bank | Country | Report Type | Year |
|------|---------|-------------|------|
| Allied Irish Banks (AIB) | Ireland | 2024 Annual Financial Report | 2024 |
| BBVA | Spain | 2024 Consolidated Management Report | 2024 |
| Groupe BPCE | France | 2024 Universal Registration Document | 2024 |

## ESG Indicators (20 Total)

### Environmental (E1) - 7 indicators
- **E1-1**: GHG Emissions - Scope 1
- **E1-2**: GHG Emissions - Scope 2
- **E1-3**: GHG Emissions - Scope 3
- **E1-4**: Total GHG Emissions
- **E1-5**: GHG Intensity per Revenue
- **E1-6**: Energy Consumption
- **E1-7**: Renewable Energy Percentage

### Social (S1) - 6 indicators
- **S1-1**: Total Workforce
- **S1-2**: Employee Turnover Rate
- **S1-3**: Gender Diversity (% Women)
- **S1-4**: Training Hours per Employee
- **S1-5**: Work-Related Injuries
- **S1-6**: Fatality Rate

### Governance (G1) - 4 indicators
- **G1-1**: Board Size
- **G1-2**: Independent Directors (%)
- **G1-3**: Women on Board (%)
- **G1-4**: Board Meetings per Year

### ESRS 2 - 3 indicators
- **ESRS2-1**: Sustainability Governance Structure
- **ESRS2-2**: Materiality Assessment Process
- **ESRS2-3**: Stakeholder Engagement

## Quick Start

### 1. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_vector.txt

# Set API key
echo "OPENROUTER_API_KEY=your_key_here" > .env
```

Get your FREE OpenRouter API key from: https://openrouter.ai/keys

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. Start Servers

```bash
# Terminal 1: Start backend (port 8000)
source venv/bin/activate
uvicorn api:app --reload

# Terminal 2: Start frontend (port 3000)
cd frontend
npm start
```

Open http://localhost:3000 in your browser!

### 4. Add PDF Reports

Place your bank sustainability reports in `data/pdfs/` directory:
- `AIB_2024_Annual_Report.pdf`
- `BBVA_2024_Management_Report.pdf`
- etc.

## Using the Web UI

1. **Upload PDF**: Drag & drop or click to upload a bank report
2. **Select Mode**: Choose Fast (recommended), Agent, or Simple mode
3. **Select Indicators**: Pick which ESG metrics to extract
4. **Extract**: Click "Extract ESG Data" and watch real-time progress
5. **View Results**: See extracted values with confidence scores
6. **Download**: CSV files are automatically generated in outputs/ directory

### Extraction Modes

- **Fast Mode** (~30-60s for 20 indicators)
  - Vector search finds relevant sections instantly
  - One AI call per indicator
  - Best for production use
  
- **Agent Mode** (~3-5min for 20 indicators)
  - AI autonomously decides which tools to use
  - Multiple iterations to find data
  - Best for complex documents
  
- **Simple Mode** (~1-2min for 20 indicators)
  - Basic keyword search workflow
  - Good for standardized reports

```
┌─────────────────────────────────────────────┐
│        Agent Workflow (Autonomous)          │
├─────────────────────────────────────────────┤
│  1. Agent receives indicator to extract    │
│  2. Agent analyzes task and chooses tool   │
│  3. Tool executes (search, extract, etc.)  │
│  4. Agent sees result and decides:         │
│     - Use another tool?                     │
│     - Extract value?                        │
│     - Try different approach?               │
│  5. Agent extracts final value              │
└─────────────────────────────────────────────┘
```

**5 Agent Tools**:
1. **search_pdf**: Semantic search for relevant sections
2. **get_page_content**: Extract text from specific pages
3. **extract_table**: Parse tables for structured data
4. **get_page_range**: Get text from multiple consecutive pages
5. **search_by_keywords**: Keyword-based search with context

### Simple Mode (Fallback) 📋

Predefined workflow for basic extraction:

```
┌─────────────────────────────────────────────┐
│      Simple Workflow (Orchestrated)         │
├─────────────────────────────────────────────┤
│  1. Load PDF                                │
│  2. Search for indicator keywords           │
│  3. Extract relevant sections               │
│  4. Pass to LLM for value extraction        │
│  5. Return structured result                │
└─────────────────────────────────────────────┘
```

## 📁 Project Structure

```
doc_intel_2/
├── config.py                    # Configuration settings
├── models.py                    # Pydantic models & 20 ESG indicators
├── pdf_parser.py                # PDF processing (PyMuPDF + pdfplumber)
├── llm_client.py                # OpenRouter LLM client
├── agent_workflow.py            # Agent-based extraction workflow (5 tools)
├── extraction_workflow.py       # Simple extraction workflow
├── database.py                  # SQLite storage
├── api.py                       # FastAPI REST API
├── main.py                      # CLI entry point
├── download_reports.py          # Report download helper
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (API key)
├── setup.sh                     # Setup script
├── reports/                     # PDF reports directory
├── outputs/                     # CSV output files
├── data/                        # SQLite database
## Tech Stack

**Backend:**
- Python 3.12 with FastAPI
- sentence-transformers (all-MiniLM-L6-v2)
- PyTorch for ML
- LangChain/LangGraph for agent mode
- OpenRouter for FREE LLM access
- PyMuPDF for PDF parsing
- SQLite database

**Frontend:**
- React 18 with hooks
- Modern dark ocean theme
- Real-time extraction progress

## Performance

| Mode | Speed | Accuracy |
|------|-------|----------|
| **Fast** | ~30-60s | 90-100% |
| **Agent** | ~3-5min | 85-95% |
| **Simple** | ~1-2min | 70-85% |

## Project Structure

```
doc_intel_2/
├── api.py                    # FastAPI backend
├── fast_extractor.py         # Vector search extraction
├── vector_search.py          # Semantic search engine
├── models.py                 # 20 ESG indicators
├── database.py               # SQLite storage
├── frontend/                 # React UI
│   ├── src/App.js           # Main component
│   └── src/App.css          # Styles
├── data/
│   ├── pdfs/                # Upload PDFs here
│   ├── embeddings_cache/    # Vector embeddings (cached)
│   └── esg_data.db          # SQLite database
└── outputs/                 # CSV exports (auto-generated)
```

## Output Directory

The `outputs/` directory contains CSV exports of extracted ESG data:

**File Naming Convention:**
- **Timestamped**: `{Company}_{Year}_esg_data_{YYYYMMDD_HHMMSS}.csv`
  - Example: `AIB_2024_esg_data_20251229_143045.csv`
  - Historical record of each extraction run
  - Never overwritten
  
- **Latest**: `{Company}_{Year}_esg_data_latest.csv`
  - Example: `AIB_2024_esg_data_latest.csv`
  - Always contains most recent extraction
  - Overwrites previous "latest" file

**CSV Format:**
```csv
company,year,indicator,value,numeric_value,unit,source_page,confidence,notes
AIB,2024,E1-1,"2,875 tCO2e",,tCO2e,79.0,1.0,
AIB,2024,E1-2,"4,391 tCO2e",,tCO2e,79.0,0.9,
```

**Columns:**
- `company`: Company name
- `year`: Report year
- `indicator`: ESG indicator code (E1-1, S1-1, etc.)
- `value`: Extracted value as text
- `numeric_value`: Parsed numeric value (if applicable)
- `unit`: Unit of measurement (tCO2e, employees, %, etc.)
- `source_page`: Page number where value was found
- `confidence`: Extraction confidence score (0.0 - 1.0)
- `notes`: Additional context or reasoning

## Configuration

Create `.env` file:

```bash
OPENROUTER_API_KEY=your_key_here
```

Get FREE key: https://openrouter.ai/keys

## Troubleshooting

**Backend won't start:**
```bash
pip install -r requirements.txt requirements_vector.txt
```

**Frontend errors:**
```bash
cd frontend && npm install
```

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

---

**Built with Vector Search, React, and FastAPI**
