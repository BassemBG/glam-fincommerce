# RAGAS Evaluation Setup

RAGAS (RAG Assessment) automatically evaluates the quality of all RAG retrieval operations in the application.

## What Gets Evaluated

Every time the AI Stylist searches your closet, recommends brands, or retrieves user preferences, RAGAS captures:
- **Question**: What the user/agent asked
- **Contexts**: What was retrieved from vector databases
- **Answer**: The final response generated
- **Metrics**: Quality scores (context recall, precision, faithfulness, relevancy)

## Quick Setup

### 1. Install Dependencies

```bash
pip install ragas datasets
```

### 2. Configure Environment Variables

Add these lines to your `.env` file:

```bash
# RAGAS Evaluation Configuration
RAGAS_ENABLED=true
RAGAS_AUTO_EVAL=true
RAGAS_OUTPUT_DIR=ragas_outputs
RAGAS_MAX_SAMPLES=200
RAGAS_GROUND_TRUTH_FALLBACK=answer
```

**Settings explained:**
- `RAGAS_ENABLED`: Master switch to enable/disable RAGAS recording
- `RAGAS_AUTO_EVAL`: Evaluate each sample immediately (vs batch later)
- `RAGAS_OUTPUT_DIR`: Where to store results (default: `ragas_outputs/`)
- `RAGAS_MAX_SAMPLES`: Buffer size before flushing to disk
- `RAGAS_GROUND_TRUTH_FALLBACK`: What to use when ground truth is unavailable

### 3. Restart Backend

```bash
uvicorn app.main:app --reload
```

### 4. Use the App

Simply use the application normally:
- Chat with the AI Stylist
- Search your closet
- Browse brand recommendations
- Create outfits

RAGAS automatically records and evaluates every retrieval operation in the background.

## Viewing Results

### Option 1: CLI Tool

```bash
# Show overall statistics
python view_ragas.py --stats

# View today's samples
python view_ragas.py --samples

# View samples for specific date
python view_ragas.py --samples 2026-01-29

# View evaluation results (last 7 days)
python view_ragas.py --results

# View results for last 3 days
python view_ragas.py --results 3

# View metrics for specific pipeline
python view_ragas.py --pipeline search_closet
python view_ragas.py --pipeline search_brand_catalog

# Live monitoring (refreshes every 30s)
python view_ragas.py --live
```

### Option 2: REST API

Access these endpoints in your browser or via curl:

```bash
# Overall statistics
curl http://localhost:8000/api/v1/ragas/stats

# View recent samples (limit 10)
curl http://localhost:8000/api/v1/ragas/samples?limit=10

# Filter by pipeline
curl http://localhost:8000/api/v1/ragas/samples?pipeline=search_closet

# Filter by date
curl http://localhost:8000/api/v1/ragas/samples?date=2026-01-29

# View evaluation results (last 7 days)
curl http://localhost:8000/api/v1/ragas/results?days=7

# Pipeline-specific metrics
curl http://localhost:8000/api/v1/ragas/pipeline/search_closet
```

### Option 3: Direct File Access

Results are stored in `ragas_outputs/`:

```bash
# View samples
cat ragas_outputs/ragas_samples_2026-01-29.jsonl | jq .

# View evaluation results
cat ragas_outputs/ragas_results_2026-01-29.jsonl | jq .

# Count total samples
wc -l ragas_outputs/ragas_samples_*.jsonl
```

## Understanding Metrics

RAGAS calculates 4 key metrics for each retrieval:

| Metric | Description | Good Score |
|--------|-------------|------------|
| **context_recall** | How much relevant info was retrieved | > 0.7 |
| **context_precision** | How relevant the retrieved contexts are | > 0.7 |
| **faithfulness** | Is the answer grounded in retrieved context? | > 0.8 |
| **answer_relevancy** | Does the answer address the question? | > 0.7 |

**Example output:**
```json
{
  "context_recall": 0.89,
  "context_precision": 0.76,
  "faithfulness": 0.94,
  "answer_relevancy": 0.82
}
```

## Tracked RAG Pipelines

RAGAS monitors these retrieval operations:

### Advisor Tools
- `search_zep_graph` - User style preferences from memory
- `search_brand_catalog` - Brand product search
- `recommend_brand_items_dna` - Personalized recommendations

### Closet Tools
- `search_closet` - Visual/semantic clothing search
- `filter_closet_items` - Filtered closet search
- `list_all_outfits` - Outfit retrieval
- `search_saved_outfits` - Outfit text search
- `filter_saved_outfits` - Outfit filtering

## Testing RAGAS

### Automated Test

```bash
# 1. Get your auth token (login via frontend, check DevTools > Local Storage)

# 2. Edit test_ragas.py
AUTH_TOKEN = "your_jwt_token_here"

# 3. Run test
python test_ragas.py
```

### Manual Test

1. Start the backend
2. Login to the frontend
3. Chat with AI Stylist: "Show me my casual outfits"
4. Check results: `python view_ragas.py --stats`

## Troubleshooting

### No samples appearing?

```bash
# Check if RAGAS is enabled
grep RAGAS_ENABLED .env

# Check output directory exists
ls -la ragas_outputs/

# Check backend logs
# Look for "RAGAS recording" or "RAGAS evaluation" messages
```

### Import errors?

```bash
# Install dependencies
pip install ragas datasets

# Verify installation
pip show ragas
```

### API endpoints not working?

Make sure the backend is restarted after adding RAGAS settings to `.env`.

## Performance Notes

- RAGAS recording is **async and non-blocking**
- Failed evaluations are logged as warnings (won't break the app)
- Auto-evaluation adds ~1-2 seconds per retrieval
- Set `RAGAS_AUTO_EVAL=false` to record only (evaluate later in batch)
- JSONL format allows concurrent writes and efficient append operations

## Disabling RAGAS

To disable RAGAS (e.g., in production), simply set:

```bash
RAGAS_ENABLED=false
```

No code changes needed - the system gracefully skips recording when disabled.
