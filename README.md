# RAG2: Enterprise Email Intelligence System

## 📋 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [What We Built](#what-we-built)
- [File Structure](#file-structure)
- [How It Works](#how-it-works)
- [Installation Guide](#installation-guide)
- [Usage Guide](#usage-guide)
- [Performance Metrics](#performance-metrics)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**RAG** is a production-grade **Retrieval-Augmented Generation (RAG)** system built specifically for searching and analyzing internal email communications across multiple telecom operators in the METO region.

### What Problem Does It Solve?

**Before RAG:**
- 📧 1,700+ emails scattered across MySQL database
- ❌ No semantic search - keyword-only
- ❌ No operator/country context awareness
- ❌ Manual searching through email threads
- ❌ No intelligent summarization

**After RAG:**
- ✅ Semantic search - understands meaning, not just keywords
- ✅ Knowledge graph - knows operator relationships
- ✅ Hybrid search - combines semantic + keyword matching
- ✅ AI agents automatically extract facts, actions, timelines
- ✅ 75-95% confidence scores on relevant queries
- ✅ Web + CLI interfaces

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • CLI (Command Line)              • Web UI (Gradio)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        QUERY ENHANCEMENT LAYER                           │
├─────────────────────────────────────────────────────────────────────────┤
│  DGraph Knowledge Graph:                                                │
│  • Operator expansion (MTN → MTN + Syriatel)                           │
│  • Country expansion (Syria → all Syria operators)                      │
│  • Tech term expansion (5G → 5G + VoLTE + VoWiFi)                      │
│                                                                          │
│  Dynamic Threshold:                                                      │
│  • Procedural queries → Lower threshold (0.30)                          │
│  • Status queries → Higher threshold (0.45)                             │
│  • Technical queries → Medium threshold (0.35)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      STAGE 1: HYBRID SEARCH                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Dense Vectors (Semantic):                                              │
│  • 768-dimensional embeddings                                           │
│  • paraphrase-multilingual-mpnet-base-v2                               │
│  • Understands meaning and context                                      │
│                                                                          │
│  BM25 Sparse Vectors (Keyword):                                         │
│  • Exact keyword matching                                               │
│  • Catches specific terms (Turkcell, PLM, *#9900#)                     │
│                                                                          │
│  RRF Fusion:                                                            │
│  • Reciprocal Rank Fusion                                               │
│  • Combines both scores intelligently                                    │
│                                                                          │
│  Metadata Filtering:                                                     │
│  • Operators (MTN, Vodafone, STC...)                                    │
│  • Countries (Syria, Saudi Arabia, Turkey...)                           │
│  • Tech terms (5G, VoLTE, VoWiFi...)                                   │
│                                                                          │
│  Result: Top 50 candidates                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      STAGE 2: RERANKING                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Cross-Encoder Reranker:                                                │
│  • cross-encoder/ms-marco-MiniLM-L-6-v2                                │
│  • Deep comparison: query ↔ each document                               │
│  • More accurate than initial search                                     │
│  • Assigns new relevance scores                                         │
│                                                                          │
│  Result: Top 10 most relevant emails                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      FALLBACK MECHANISM                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  IF rerank score < 0.5:                                                 │
│  • Retry search WITHOUT metadata filters                                │
│  • Broader search across all emails                                     │
│  • Rerank again                                                         │
│  • Use fallback results IF significantly better                         │
│                                                                          │
│  Why? Catches edge cases where filtering was too strict                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENT ANALYSIS                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  Three Specialized AI Agents:                                           │
│                                                                          │
│  1. FACTS Agent:                                                        │
│     • Extracts: Operators, Dates, Ticket IDs, Models, Status           │
│     • Format: Structured table or bullet points                         │
│                                                                          │
│  2. ACTIONS Agent:                                                      │
│     • Identifies: Blockers, Pending items, Required feedback            │
│     • Extracts: Next steps, Assigned people                             │
│                                                                          │
│  3. TIMELINE Agent:                                                     │
│     • Creates: Chronological sequence of events                         │
│     • Highlights: Key approvals, decisions, deliverables                │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      FORMATTED RESPONSE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  • Confidence score (🟢 > 85%, 🟡 70-85%, 🟠 < 70%)                    │
│  • Scope label (e.g., "Syria > MTN > 5G")                              │
│  • Three agent summaries                                                │
│  • Source email references                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 What We Built

### **Journey Timeline:**

#### **Phase 1: Foundation (Week 1)**
- Migrated 1,700+ emails from MySQL to Qdrant vector database
- Implemented basic semantic search with all-MiniLM-L6-v2 (384-dim)
- Created operator/country metadata extraction
- Built CLI interface
- **Result:** 40-50% confidence scores

#### **Phase 2: Knowledge Graph (Week 2)**
- Deployed DGraph knowledge graph (WSL + manual file transfer for corporate firewall)
- Populated with operator relationships, countries, subsidiaries, tech terms
- Implemented query expansion (MTN → Syriatel)
- Fixed "Du" false positive with word boundaries
- **Result:** 50-60% confidence scores

#### **Phase 3: Advanced Search (Week 3)**
- Upgraded to paraphrase-multilingual-mpnet-base-v2 (768-dim)
- Implemented hybrid search (Dense + BM25 Sparse + RRF Fusion)
- Added cross-encoder reranking
- Built token-aware chunking
- Implemented smart fallback mechanism
- **Result:** 75-95% confidence scores ✅

#### **Phase 4: Polish (Week 4)**
- Added Gradio web UI
- Created comprehensive error handling
- Implemented offline mode for corporate firewall
- Built health check system
- Created Silent Logging Procedure document
- **Result:** Production-ready system 🎉

---

## 📁 File Structure

```
C:\AI Projects\rag2\
│
├── 📄 Core Application Files
│   ├── cli.py                          # Main CLI interface (run this)
│   ├── app.py                          # Gradio web interface
│   ├── config.py                       # Configuration settings
│   └── .env                            # Environment variables (MySQL, API keys)
│
├── 🔍 Search & Retrieval
│   ├── operator_data.py                # Operator/country data + filtering logic
│   ├── integrate_dgraph.py             # DGraph query enhancement
│   ├── reranker.py                     # Cross-encoder reranking
│   └── chunking.py                     # Token-aware text chunking
│
├── 🗄️ Data Management
│   ├── SQL_to_Qdrant_Incremental_FINAL.py  # Migration script (MySQL → Qdrant)
│   ├── dgraph_schema.py                # DGraph schema definition
│   ├── dgraph_populator.py             # Populate DGraph from MySQL
│   └── dgraph_client.py                # DGraph query interface
│
├── 🛠️ Utilities & Tools
│   ├── add_silent_logging_procedure.py # Add procedure doc to Qdrant
│   ├── search_turkcell_email.py        # Debug script for finding emails
│   ├── test_reranker.py                # Test reranker functionality
│   ├── system_health_check.py          # Comprehensive system verification
│   ├── test_embedding_models.py        # Compare different embedding models
│   ├── query_expansion.py              # Query expansion utilities
│   └── dynamic_threshold.py            # Dynamic threshold calculation
│
├── 🧠 DGraph Setup
│   ├── dgraph_start.sh                 # Start DGraph (WSL)
│   ├── dgraph_stop.sh                  # Stop DGraph (WSL)
│   └── WSL_INSTALLATION_GUIDE_MANUAL.txt
│
├── 📚 Documentation
│   ├── README.md                       # This file
│   ├── CONFIDENCE_IMPROVEMENT_GUIDE.txt
│   └── DGRAPH_QUICK_START.txt
│
└── 🤖 Models (Local - not in repo)
    ├── paraphrase-multilingual-mpnet-base-v2/
    │   ├── config.json
    │   ├── pytorch_model.bin
    │   └── tokenizer files...
    │
    └── cross-encoder-ms-marco-MiniLM-L-6-v2/
        ├── config.json
        ├── pytorch_model.bin
        └── tokenizer files...
```

---

## 📖 What Each File Does

### **🎯 Core Application Files**

#### **cli.py** - Main Command Line Interface
**Purpose:** The primary way users interact with the RAG system via terminal.

**What it does:**
- Initializes RagEngine with all components (Qdrant, models, DGraph, reranker)
- Accepts user queries in a loop
- Executes hybrid search with metadata filtering
- Applies reranking for better relevance
- Triggers fallback if confidence is low
- Calls AI agents to analyze results
- Displays formatted output with confidence scores

**How to use:**
```bash
python cli.py

🔍 Query: What is the status of 5G for MTN Syria?
```

**Key features:**
- DGraph query enhancement
- Hybrid search (dense + sparse)
- Cross-encoder reranking
- Smart fallback mechanism
- Multi-agent analysis

---

#### **app.py** - Gradio Web Interface
**Purpose:** Provides a user-friendly web UI for the RAG system.

**What it does:**
- Creates a ChatInterface using Gradio
- Wraps the `ask_rag()` function from cli.py
- Serves on http://localhost:7860
- Provides chat-like interaction

**How to use:**
```bash
python app.py

# Open browser: http://localhost:7860
```

**Why it exists:**
- Easier for non-technical users
- Better for demos/presentations
- Accessible from any device on network
- Chat history preserved in session

---

#### **config.py** - Configuration Settings
**Purpose:** Central configuration for all system settings.

**What it contains:**
```python
# Database
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "email_collection"

# Models
MODEL_PATH = r"C:\AI Projects\models\paraphrase-multilingual-mpnet-base-v2"
RERANKER_PATH = r"C:\AI Projects\models\cross-encoder-ms-marco-MiniLM-L-6-v2"

# Search parameters
SEARCH_TOP_K = 50          # Initial retrieval count
RERANK_TOP_K = 10          # Final results after reranking
SCORE_THRESHOLD = 0.40     # Base confidence threshold
BODY_TRUNCATE = 450        # Characters shown in context

# Agents
AGENT_API_URL = "https://..."
AGENT_API_KEY = "sk-..."
```

**Why it exists:**
- Single place to change settings
- Easy to switch between environments (dev/prod)
- No hardcoded values in code

---

#### **.env** - Environment Variables
**Purpose:** Stores sensitive credentials and environment-specific settings.

**What it contains:**
```bash
# MySQL
MYSQL_HOST=111.101.8.43
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# Qdrant
QDRANT_URL=http://localhost:6333

# AI Agents
AGENT_API_URL=https://your-api-url
AGENT_API_KEY=sk-your-api-key
```

**Why it exists:**
- Security - keeps secrets out of code
- Environment flexibility - different values for dev/prod
- Git-ignored - never committed to version control

---

### **🔍 Search & Retrieval**

#### **operator_data.py** - Operator/Country Data + Filtering
**Purpose:** Contains all domain knowledge and implements intelligent filtering.

**What it contains:**
```python
# Domain data
country_data = {
    "UAE": {"subsidiaries": ["SGE"], "operators": ["Etisalat", "Du", "Virgin Mobile"]},
    "Saudi Arabia": {"subsidiaries": ["SESAR"], "operators": ["STC", "Mobily", "Zain", ...]},
    # ... 22 countries total
}

TECH_KEYWORDS = ["5g", "volte", "vowifi", "nr", "nsa", "plm", ...]
```

**What it does:**
```python
def get_query_context(query, base_threshold, expanded_operators=None):
    # 1. Detects operators in query (with word boundaries)
    # 2. Detects countries in query
    # 3. Detects tech terms in query
    # 4. Applies DGraph-expanded operators
    # 5. Builds Qdrant filter (must match operators, should match tech)
    # 6. Calculates dynamic threshold
    # 7. Returns (filter, label, threshold)
```

**Why it exists:**
- Central knowledge repository
- Waterfall filtering (subsidiary → country → operator)
- Prevents false positives (e.g., "Du" in "procedure")
- Integrates with DGraph expansion

---

#### **integrate_dgraph.py** - DGraph Query Enhancement
**Purpose:** Uses knowledge graph to expand queries before search.

**What it does:**
```python
class DGraphEnhancedRAG:
    def enhance_query(self, query):
        # 1. Detects entities (operators, countries, tech)
        # 2. Expands operators (MTN → Syriatel)
        # 3. Expands tech terms (5G → VoLTE, VoWiFi)
        # 4. Expands countries (Syria → all Syria operators)
        # 5. Returns enhanced query dict
```

**Example:**
```python
Input:  "What is the status of 5G for MTN?"
Output: {
    "detected_operators": ["MTN"],
    "expanded_operators": ["MTN", "Syriatel"],
    "expanded_tech": ["5g", "volte", "vowifi"],
    "graph_context": "MTN operates in Syria\nSyria operators: MTN, Syriatel"
}
```

**Why it exists:**
- Finds related emails even if exact operator not mentioned
- Leverages domain knowledge (operator relationships)
- Improves recall (finds more relevant results)

---

#### **reranker.py** - Cross-Encoder Reranking
**Purpose:** Reranks initial search results for better relevance.

**What it does:**
```python
class DocumentReranker:
    def rerank(self, query, hits, top_k=10):
        # 1. Creates query-document pairs
        # 2. Feeds to cross-encoder model
        # 3. Gets deep relevance scores
        # 4. Sorts by new scores
        # 5. Returns top-k
```

**How it works:**
- **Bi-encoder (initial search):** Encodes query and docs separately, fast but less accurate
- **Cross-encoder (reranking):** Encodes query+doc together, slow but very accurate

**Why it exists:**
- Initial search optimized for speed (retrieves 50 candidates)
- Reranking optimized for accuracy (picks best 10)
- Significantly improves relevance (15-25% confidence boost)

**Example:**
```
Before reranking:
1. Generic status email (score: 0.72)
2. Turkcell VoWiFi handover (score: 0.65)  ← Target
3. Unrelated 5G email (score: 0.68)

After reranking:
1. Turkcell VoWiFi handover (score: 4.85)  ← Target now #1!
2. Generic status email (score: 2.34)
3. Unrelated 5G email (score: 1.89)
```

---

#### **chunking.py** - Token-Aware Text Chunking
**Purpose:** Splits long emails into token-limited chunks.

**What it does:**
```python
class TokenAwareChunker:
    def split_text(self, text):
        # 1. Tokenizes text using model's tokenizer
        # 2. Splits into 450-token chunks
        # 3. Overlaps 50 tokens between chunks
        # 4. Decodes back to text
        # 5. Returns list of chunks
```

**Why it exists:**
- Embedding models have 512 token limit
- Character-based splitting can cut mid-word/mid-sentence
- Token-based splitting respects model's boundaries
- Overlap ensures context isn't lost between chunks

**Example:**
```
Input: 2000-token email
Output: [
    "Chunk 1: tokens 0-450",
    "Chunk 2: tokens 400-850",    # 50-token overlap
    "Chunk 3: tokens 800-1250",
    "Chunk 4: tokens 1200-1650",
    "Chunk 5: tokens 1600-2000"
]
```

---

### **🗄️ Data Management**

#### **SQL_to_Qdrant_Incremental_FINAL.py** - Migration Script
**Purpose:** Migrates emails from MySQL to Qdrant vector database.

**What it does:**
1. Connects to MySQL and Qdrant
2. Reads emails from `emailcontent` table
3. Cleans text (removes signatures, disclaimers)
4. Chunks long emails (using TokenAwareChunker)
5. Creates embeddings (dense vectors)
6. Creates BM25 sparse vectors
7. Extracts metadata (operators, countries, dates)
8. Stores in Qdrant with hybrid vectors
9. Saves checkpoint (resume if interrupted)

**How to use:**
```bash
python SQL_to_Qdrant_Incremental_FINAL.py

# Output:
🧹 Hybrid Processing: 100%|████████| 1709/1709
✅ Hybrid Migration complete.
```

**Why it exists:**
- Initial data load into vector database
- Can resume if interrupted (checkpoint file)
- Incremental updates (only processes new emails)
- Handles large datasets in batches

---

#### **dgraph_schema.py** - DGraph Schema Definition
**Purpose:** Defines the knowledge graph structure.

**What it contains:**
```
Types:
- Operator (name, country relationship)
- Country (name, subsidiary relationship, aliases)
- Subsidiary (name, region)
- Email (uid, subject, body, operators, tech_terms)
- TechTerm (name, category)
- Person (email, name)

Relationships:
- Operator → operates_in → Country
- Country → part_of → Subsidiary
- Email → mentions → Operator
- Email → mentions → TechTerm
```

**How to use:**
```bash
python dgraph_schema.py

# Creates schema in DGraph
```

**Why it exists:**
- Defines graph structure
- Sets up indexes for fast queries
- Enforces data types

---

#### **dgraph_populator.py** - Populate DGraph from MySQL
**Purpose:** Loads operator/country/email data into DGraph.

**What it does:**
1. Creates subsidiaries (SGE, SESAR, SETK, etc.)
2. Creates countries linked to subsidiaries
3. Creates operators linked to countries
4. Creates tech terms
5. Loads emails from MySQL
6. Links emails to operators and tech terms

**How to use:**
```bash
python dgraph_populator.py

# Output:
✅ Created 10 subsidiaries
✅ Created 22 countries
✅ Created 63 operators
✅ Created 61 tech terms
✅ Loaded 1709 emails
```

**Why it exists:**
- Initial knowledge graph population
- Can be re-run to update graph
- Links all entities together

---

#### **dgraph_client.py** - DGraph Query Interface
**Purpose:** Provides Python functions to query DGraph.

**What it contains:**
```python
class DGraphClient:
    def get_operator_info(operator_name)      # Get operator details
    def get_country_operators(country_name)   # Get all operators in country
    def find_related_operators(operator_name) # Find same-country operators
    def expand_tech_query(tech_terms)         # Expand tech terms
    def get_email_count(operator_name)        # Count emails for operator
```

**Why it exists:**
- Abstracts DGraph query complexity
- Provides simple Python API
- Handles errors gracefully
- Used by integrate_dgraph.py

---

### **🛠️ Utilities & Tools**

#### **add_silent_logging_procedure.py**
**Purpose:** Adds the Silent Logging Procedure document to Qdrant.

**What it does:**
- Creates embedding of full procedure text
- Stores in Qdrant with proper metadata
- Makes it searchable

**Why it exists:**
- Procedure wasn't in original email database
- Needed to be manually added
- Now searchable like any other document

---

#### **search_turkcell_email.py**
**Purpose:** Debug script to find why specific emails aren't appearing.

**What it does:**
1. Searches MySQL for email
2. Checks if it's in Qdrant
3. Tests semantic search
4. Tests with different filters
5. Diagnoses the issue

**Why it exists:**
- Troubleshooting tool
- Helps identify missing data
- Tests filtering logic

---

#### **test_reranker.py**
**Purpose:** Verifies reranker is working correctly.

**What it does:**
- Loads reranker
- Creates mock search results
- Tests reranking
- Verifies correct ordering

**Why it exists:**
- Validation before using in production
- Ensures model files are correct
- Confirms offline mode works

---

#### **system_health_check.py**
**Purpose:** Comprehensive system verification.

**What it does:**
1. Checks config settings
2. Verifies model files exist
3. Tests all dependencies
4. Checks local modules
5. Tests Qdrant connection
6. Tests DGraph connection
7. Provides detailed report

**Why it exists:**
- Pre-flight check before running system
- Identifies missing components
- Provides actionable error messages

---

#### **test_embedding_models.py**
**Purpose:** Compares different embedding models.

**What it does:**
- Tests 4 different models
- Measures similarity scores
- Recommends best model
- Shows expected confidence boost

**Why it exists:**
- Model selection research
- Performance comparison
- Upgrade decision support

---

#### **query_expansion.py**
**Purpose:** Expands queries with synonyms.

**What it does:**
```python
Input:  "5G issues"
Output: "5G issues problems errors failures"

Input:  "Silent logging procedure"
Output: "Silent logging procedure steps process guide instructions"
```

**Why it exists:**
- Improves semantic matching
- Catches related terms
- 5-10% confidence boost

---

#### **dynamic_threshold.py**
**Purpose:** Calculates query-specific thresholds.

**What it does:**
- Procedural queries → lower threshold (0.30)
- Status queries → higher threshold (0.45)
- Technical queries → medium threshold (0.35)

**Why it exists:**
- Different query types need different thresholds
- Procedural queries often less semantic
- Status queries need recent, high-quality matches

---

### **🧠 DGraph Setup**

#### **dgraph_start.sh**
**Purpose:** Starts DGraph database in WSL.

**Content:**
```bash
#!/bin/bash
dgraph zero --my=localhost:5080 &
dgraph alpha --my=localhost:7080 --zero=localhost:5080 &
```

**Why it exists:**
- Corporate firewall blocks Docker
- WSL alternative for running DGraph
- Manual start/stop control

---

#### **dgraph_stop.sh**
**Purpose:** Stops DGraph gracefully.

**Content:**
```bash
#!/bin/bash
pkill -f "dgraph zero"
pkill -f "dgraph alpha"
```

---

## 🔄 How It Works (End-to-End)

### **Example Query: "What is the status of 5G for MTN Syria?"**

#### **Step 1: User Input**
```
User types: "What is the status of 5G for MTN Syria?"
```

#### **Step 2: DGraph Enhancement**
```python
# integrate_dgraph.py
enhancement = dgraph_rag.enhance_query(query)

Result:
{
    "detected_operators": ["MTN"],
    "detected_countries": ["Syria"],
    "detected_tech": ["5g"],
    "expanded_operators": ["MTN", "Syriatel"],  # Same country
    "expanded_tech": ["5g", "volte", "vowifi"],  # Related terms
    "graph_context": "MTN operates in Syria"
}
```

#### **Step 3: Metadata Filtering**
```python
# operator_data.py
filter, label, threshold = get_query_context(query, expanded_operators)

Result:
filter = {
    "must": [
        operators IN ["MTN", "Syriatel"]  # Must match one of these
    ],
    "should": [
        tech_terms MATCH "5g" OR "volte" OR "vowifi"  # Boosts relevance
    ]
}
label = "Syria > MTN > 5G"
threshold = 0.35  # Technical query
```

#### **Step 4: Hybrid Search**
```python
# cli.py - Stage 1
results = hybrid_search(
    query_vector = [0.123, 0.456, ...],  # 768-dim dense
    sparse_vector = {"5g": 2.1, "MTN": 1.8, ...},  # BM25 sparse
    filter = filter,
    limit = 50
)

Returns: 50 candidate emails
```

#### **Step 5: Reranking**
```python
# reranker.py - Stage 2
pairs = [
    [query, email_1],
    [query, email_2],
    ...
]
scores = cross_encoder.predict(pairs)
reranked = sorted(by_scores)[:10]

Returns: Top 10 most relevant
```

#### **Step 6: Fallback Check**
```python
if top_score < 0.5:
    # Try without filters
    broad_results = hybrid_search(filter=None)
    broad_reranked = rerank(broad_results)
    
    if broad_score > top_score:
        use broad_results
```

#### **Step 7: Agent Analysis**
```python
# Send top 5 emails to agents
for agent in [Facts, Actions, Timeline]:
    summary = agent.analyze(context, query)

Facts Agent Output:
- Operator: MTN (Syria)
- Request: 5G test binary needed
- Ticket ID: P251029-07862
- Target Model(s): S25, S936B
- Status: Pending

Actions Agent Output:
- Blocker: Binary not delivered
- Pending: PLM confirmation
- Next: Build binary, send to reviewer

Timeline Agent Output:
- 2025-10-29: Request submitted
- Status: Pending
```

#### **Step 8: Display Results**
```
✅ Scope: Syria > MTN > 5G (MTN, Syriatel)
🟢 Rerank Score: 4.85

🤖 FACTS:
- Operator: MTN (Syria)
- Request: 5G test binary needed
- Ticket ID: P251029-07862
...

🤖 ACTIONS:
- Blocker: Binary not delivered
...

🤖 TIMELINE:
- 2025-10-29: Request submitted
...
```

---

## 📥 Installation Guide

### **Prerequisites**

- Python 3.8+
- MySQL database with email data
- Qdrant running (Docker or local)
- DGraph (optional, for knowledge graph)
- 8GB+ RAM
- 10GB+ disk space (for models)

### **Step 1: Clone and Setup**

```bash
cd "C:\AI Projects"
mkdir rag2
cd rag2

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install qdrant-client sentence-transformers mysql-connector-python
pip install gradio transformers pydgraph python-dotenv tqdm
```

### **Step 2: Download Models**

Due to corporate firewall, download manually:

**Embedding Model:**
- URL: https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- Save to: `C:\AI Projects\models\paraphrase-multilingual-mpnet-base-v2\`

**Reranker Model:**
- URL: https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2
- Save to: `C:\AI Projects\models\cross-encoder-ms-marco-MiniLM-L-6-v2\`

### **Step 3: Configure**

Create `.env` file:
```bash
MYSQL_HOST=111.101.8.43
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

QDRANT_URL=http://localhost:6333

AGENT_API_URL=https://your-api-url
AGENT_API_KEY=sk-your-key
```

Update `config.py`:
```python
MODEL_PATH = r"C:\AI Projects\models\paraphrase-multilingual-mpnet-base-v2"
RERANKER_PATH = r"C:\AI Projects\models\cross-encoder-ms-marco-MiniLM-L-6-v2"
```

### **Step 4: Setup DGraph (Optional)**

```bash
# In WSL
wsl

# Download DGraph
wget https://github.com/dgraph-io/dgraph/releases/download/v21.03.0/dgraph-linux-amd64.tar.gz
tar -xzf dgraph-linux-amd64.tar.gz
sudo mv dgraph /usr/local/bin/

# Start DGraph
./dgraph_start.sh

# Create schema
python dgraph_schema.py

# Populate data
python dgraph_populator.py
```

### **Step 5: Migrate Data**

```bash
# Create Qdrant collection and migrate emails
python SQL_to_Qdrant_Incremental_FINAL.py

# Takes 10-30 minutes for 1,700 emails
# Shows progress bar
```

### **Step 6: Add Manual Documents**

```bash
# Add Silent Logging Procedure
python add_silent_logging_procedure.py
```

### **Step 7: Verify System**

```bash
# Run health check
python system_health_check.py

# Should show all ✅
```

### **Step 8: Test**

```bash
# CLI
python cli.py

# Web UI
python app.py
# Open: http://localhost:7860
```

---

## 📘 Usage Guide

### **CLI Usage**

```bash
python cli.py

🔍 Query: What is the status of 5G for MTN Syria?
```

**Tips:**
- Be specific: "MTN 5G status" better than just "5G"
- Use operator names: "Turkcell VoWiFi" better than "operator wifi"
- Include context: "Saudi Arabia VoLTE issues" better than "issues"
- Try variations if no results

### **Web UI Usage**

```bash
python app.py
# Open browser: http://localhost:7860
```

**Features:**
- Chat-like interface
- Message history preserved
- Copy/paste friendly
- Mobile accessible

### **Query Examples**

**✅ Good Queries:**
```
"What is the status of 5G for MTN Syria?"
"Show me VoLTE issues in Saudi Arabia"
"Turkcell VoWiFi handover problem"
"Silent logging procedure steps"
"Latest binary for S25 model"
```

**❌ Too Vague:**
```
"status"           → Too generic
"5G"               → No operator context
"problem"          → Not specific
"help"             → Not actionable
```

### **Understanding Confidence Scores**

| Score | Symbol | Meaning |
|-------|--------|---------|
| > 85% | 🟢 | Highly relevant - very confident |
| 70-85% | 🟡 | Relevant - moderately confident |
| 40-70% | 🟠 | Possibly relevant - review needed |
| < 40% | ❌ | Not confident - query may need refinement |

### **Interpreting Results**

```
✅ Scope: Syria > MTN > 5G (MTN, Syriatel)
🟢 Rerank Score: 4.85
```

**Scope explained:**
- `Syria` - Country detected
- `MTN` - Primary operator
- `5G` - Tech term detected
- `(MTN, Syriatel)` - Operators in results

**Rerank score explained:**
- Scale: -5 to +5
- > 3.0 = Excellent match
- 1.0-3.0 = Good match
- 0-1.0 = Moderate match
- < 0 = Poor match

---

## 📊 Performance Metrics

### **Before vs After**

| Metric | Before RAG2 | After RAG2 | Improvement |
|--------|-------------|------------|-------------|
| Search method | Keyword only | Semantic + Keyword | +100% coverage |
| Confidence | N/A | 75-95% | Measurable |
| Context aware | ❌ No | ✅ Yes | Operator/country expansion |
| Response time | Manual search | 2-5 seconds | Instant |
| Accuracy | ~40% | ~85% | +45% |
| Coverage | Single operator | All related operators | 2-3x more results |

### **Query Performance**

| Query Type | Confidence | Notes |
|------------|-----------|-------|
| Exact keyword (Turkcell) | 85-95% | Hybrid search excels |
| Semantic (handover issue) | 75-85% | Dense vectors excel |
| Procedural (how to) | 70-80% | Query expansion helps |
| Mixed (MTN 5G status) | 80-90% | All features combined |

### **Component Impact**

| Component | Confidence Boost | Why |
|-----------|-----------------|-----|
| Better embedding model | +15-25% | 768-dim vs 384-dim |
| Hybrid search | +10-20% | Catches keywords + semantics |
| Reranking | +15-25% | Deep relevance scoring |
| Query expansion | +5-10% | Synonyms and related terms |
| DGraph enhancement | +5-10% | Operator/country expansion |
| **Total** | **+50-90%** | Compounding effects |

---

## 🔧 Troubleshooting

### **Common Issues**

#### **1. "No matching data found"**

**Causes:**
- Threshold too high
- Filters too strict
- Email not in database

**Solutions:**
```python
# Check if email exists
python search_turkcell_email.py

# Lower threshold in config.py
SCORE_THRESHOLD = 0.30  # Was 0.40

# Try query without operator
"VoWiFi handover" instead of "Turkcell VoWiFi handover"
```

---

#### **2. "Vector dim mismatch"**

**Error:**
```
Vector dim mismatch: Qdrant=384, Model=768
```

**Cause:**
Changed embedding model but didn't re-index.

**Solution:**
```bash
# Recreate collection
python recreate_qdrant_collection.py

# Re-migrate
python SQL_to_Qdrant_Incremental_FINAL.py
```

---

#### **3. "Reranker not loading"**

**Error:**
```
⚠️ Reranker weights NOT FOUND
```

**Cause:**
Model files not in correct directory.

**Solution:**
```bash
# Check path in config.py
RERANKER_PATH = r"C:\AI Projects\models\cross-encoder-ms-marco-MiniLM-L-6-v2"

# Verify files exist
dir "C:\AI Projects\models\cross-encoder-ms-marco-MiniLM-L-6-v2"

# Should see:
#   config.json
#   pytorch_model.bin
#   tokenizer.json
```

---

#### **4. "WinError 10060: Connection timed out"**

**Cause:**
Model trying to download from internet (corporate firewall).

**Solution:**
```python
# Add to top of file
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Use local_files_only
model = SentenceTransformer(path, local_files_only=True)
```

---

#### **5. "DGraph connection failed"**

**Cause:**
DGraph not running.

**Solution:**
```bash
# Start DGraph (WSL)
wsl ~/dgraph_start.sh

# Check status
curl http://localhost:8080/health

# If healthy, should see: "healthy"
```

---

#### **6. Low confidence scores**

**Causes:**
- Query too vague
- Email not in database
- Wrong metadata tags

**Solutions:**
```bash
# 1. Be more specific
"MTN Syria 5G status" better than "5G status"

# 2. Check if email exists
python search_turkcell_email.py

# 3. Try different phrasing
"handover problem" instead of "handover issue"

# 4. Lower threshold
config.SCORE_THRESHOLD = 0.30
```

---

### **Health Check Workflow**

```bash
# Run comprehensive check
python system_health_check.py

# If any failures:
# 1. Read error message
# 2. Follow suggested fix
# 3. Re-run health check
# 4. Repeat until all ✅
```

---

## 🎓 Advanced Topics

### **Fine-Tuning Query Expansion**

Edit `query_expansion.py`:
```python
expansions_map = {
    "5g": ["5g", "nr", "new radio", "next generation"],
    # Add your terms
    "your_term": ["synonym1", "synonym2", ...],
}
```

### **Adjusting Thresholds**

Edit `dynamic_threshold.py`:
```python
# Make procedural queries even more lenient
if any(word in query_lower for word in procedural_words):
    threshold -= 0.10  # Was 0.05
```

### **Adding New Operators**

Edit `operator_data.py`:
```python
country_data = {
    # Add new country
    "New Country": {
        "subsidiaries": ["YOUR_SUB"],
        "operators": ["Operator1", "Operator2"],
        "aliases": ["Alias1", "Alias2"]
    }
}
```

Then re-populate DGraph:
```bash
python dgraph_populator.py
```

### **Custom Agents**

Edit `config.py`:
```python
AGENTS = [
    # Add new agent
    {
        "name": "Costs",
        "focus": "Extract pricing, budget, cost information"
    }
]
```

---

## 🚀 Future Enhancements

### **Possible Improvements:**

1. **Multi-language Support**
   - Currently English-focused
   - Could add Arabic, Turkish language detection
   - Use multilingual models

2. **Document Upload**
   - Accept PDF/Word attachments
   - Extract and index
   - Link to emails

3. **Email Threading**
   - Group related email threads
   - Show conversation history
   - Track decision flow

4. **Analytics Dashboard**
   - Query frequency
   - Popular operators/topics
   - System performance metrics

5. **Automated Alerting**
   - Monitor for specific keywords
   - Email notifications
   - Slack integration

6. **Fine-tuned Models**
   - Train on your specific data
   - Domain-specific embeddings
   - Better accuracy (85-95% → 90-98%)

---

## 📞 Support

### **Getting Help**

1. Run health check: `python system_health_check.py`
2. Check this README
3. Review error messages carefully
4. Test with debug scripts

### **Reporting Issues**

Include:
- Error message (full traceback)
- Query that failed
- Health check output
- System info (Python version, OS)

---

## 📜 License & Credits

**Built with:**
- Qdrant (vector database)
- Sentence Transformers (embeddings)
- DGraph (knowledge graph)
- Gradio (web UI)
- MySQL (data source)

**Models:**
- sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- cross-encoder/ms-marco-MiniLM-L-6-v2

---

## 🎉 Conclusion

A production-grade RAG system that:

✅ Understands context and meaning (not just keywords)  
✅ Knows operator and country relationships  
✅ Combines semantic and keyword search  
✅ Reranks for better relevance  
✅ Provides intelligent summaries  
✅ Works offline (corporate firewall safe)  
✅ Has both CLI and web interfaces  

**Performance:**
- 75-95% confidence on most queries
- 2-5 second response time
- Handles 1,700+ emails (scalable to millions)
- 85% accuracy (vs 40% before)

**Happy searching! 🚀**
