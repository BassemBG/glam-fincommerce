# RAGAS Generation Evaluation Guide

## Overview

Generation evaluation focuses on measuring **LLM answer quality**, specifically:
- **Answer Relevancy**: Does the answer address the question?
- **Faithfulness**: Is the answer grounded in retrieved context (no hallucinations)?

This is different from retrieval evaluation which measures context quality.

## Key Concepts

### What RAGAS Generation Evaluates

| Metric | What It Measures | Good Score | Bad Score Means |
|--------|------------------|------------|-----------------|
| **answer_relevancy** | Does answer respond to the question? | > 0.7 | Vague, off-topic, or generic LLM fluff |
| **faithfulness** | Is answer supported by retrieved context? | > 0.8 | Hallucinations, external knowledge, unsafe claims |

### What You Need

For each evaluation, you must provide:

| Field | Required | Description |
|-------|----------|-------------|
| `question` | ✅ Yes | User's query |
| `contexts` | ✅ Yes | Retrieved information (list of strings) |
| `answer` | ✅ Yes | LLM's generated answer |
| `ground_truth` | ❌ No | Optional reference answer |

## Usage

### 1. Enable Generation Evaluation

Add to your `.env`:

```bash
RAGAS_ENABLED=true
RAGAS_AUTO_EVAL=true  # Auto-evaluate each answer
```

### 2. Evaluate a Single Answer

```python
from app.services.ragas_service import ragas_service

# After your LLM generates an answer
metrics = await ragas_service.evaluate_generation(
    question="What casual outfits can I make?",
    contexts=[
        "ID: 1 | Category: Top | Colors: blue, white | Brand: Zara",
        "ID: 5 | Category: Bottom | Colors: black | Brand: H&M",
    ],
    answer="You can create a casual outfit with your blue Zara top and black H&M pants.",
    pipeline="agent_chat",
    metadata={"user_id": 123}
)

# Returns: {'answer_relevancy': 0.89, 'faithfulness': 0.94}
```

### 3. Integrate into Agent Orchestrator

Add generation evaluation after your LLM responds:

```python
# In orchestrator.py after getting LLM response
from app.services.ragas_service import ragas_service

async def chat_stream(self, user_id: int, message: str, history: List, image_data: Optional[bytes]):
    # ... your existing code ...
    
    # After LLM generates final answer
    final_answer = "..."  # LLM's response
    retrieved_contexts = [...]  # From search_closet, search_brand_catalog, etc.
    
    # Evaluate generation quality
    metrics = await ragas_service.evaluate_generation(
        question=message,
        contexts=retrieved_contexts,
        answer=final_answer,
        pipeline="agent_orchestrator",
        metadata={"user_id": user_id}
    )
    
    if metrics:
        logger.info(f"Generation quality - Relevancy: {metrics['answer_relevancy']:.2f}, Faithfulness: {metrics['faithfulness']:.2f}")
        
        # Optional: Alert on low scores
        if metrics['faithfulness'] < 0.7:
            logger.warning(f"Potential hallucination detected for user {user_id}")
```

## Testing

### Run Test Suite

```bash
python test_ragas_generation.py
```

This runs 6 test cases covering:
1. ✅ Good answer (high relevancy + high faithfulness)
2. ❌ Hallucinated answer (low faithfulness)
3. ❌ Off-topic answer (low relevancy)
4. ❌ Vague answer (low relevancy)
5. ✅ Good brand recommendation
6. ❌ Style advice that contradicts user preferences

### Expected Output

```
🧪 RAGAS GENERATION EVALUATION TESTS
================================================================================

Test 1/6: Good Answer - Relevant & Faithful
Question: What casual tops do I own?

Retrieved Contexts (3 items):
  • ID: 1 | Category: Top | Sub-category: T-shirt | Colors: ['blue', 'white']...

Generated Answer:
  You own 3 casual tops: a blue and white Zara t-shirt, a cream H&M blouse...

⏳ Evaluating generation quality...

📈 RESULTS:
  🎯 Answer Relevancy: 0.921 🟢 Excellent
  ✓  Faithfulness:     0.967 🟢 Excellent
```

## Viewing Results

### CLI Tool

```bash
# View generation evaluations
python view_ragas.py --results

# The view_ragas.py tool automatically includes generation metrics
```

### API Endpoints

```bash
# Get all evaluation results (includes generation)
curl http://localhost:8000/api/v1/ragas/results

# Filter by pipeline
curl http://localhost:8000/api/v1/ragas/samples?pipeline=agent_orchestrator
```

### Direct File Access

Generation evaluations are stored separately:

```bash
# View generation-specific evaluations
cat ragas_outputs/ragas_generation_2026-01-29.jsonl | jq .

# Each line contains:
{
  "timestamp": "2026-01-29T10:30:45.123Z",
  "evaluation_type": "generation_only",
  "results": {
    "answer_relevancy": 0.89,
    "faithfulness": 0.94
  },
  "count": 1,
  "pipelines": ["agent_chat"],
  "question": "What casual outfits can I make?",
  "answer_preview": "You can create a casual outfit with..."
}
```

## Interpreting Scores

### Answer Relevancy

| Score | Interpretation | Action |
|-------|----------------|--------|
| > 0.8 | Excellent - directly answers question | ✅ No action needed |
| 0.7-0.8 | Good - addresses question adequately | ✅ Acceptable |
| 0.5-0.7 | Fair - somewhat relevant but vague | ⚠️ Review prompt engineering |
| < 0.5 | Poor - off-topic or generic | ❌ Fix LLM instructions |

### Faithfulness

| Score | Interpretation | Action |
|-------|----------------|--------|
| > 0.9 | Excellent - fully grounded | ✅ No action needed |
| 0.8-0.9 | Good - mostly grounded | ✅ Acceptable |
| 0.6-0.8 | Fair - some unsupported claims | ⚠️ Review retrieved contexts |
| < 0.6 | Poor - hallucinating | ❌ Critical issue - fix retrieval or prompt |

## Common Issues & Solutions

### Low Faithfulness Scores

**Problem**: LLM is adding information not in retrieved contexts

**Solutions**:
1. Strengthen system prompt: "Only use information from the provided contexts"
2. Improve retrieval to provide more complete context
3. Add explicit grounding instructions to LLM
4. Reduce temperature to make LLM more conservative

### Low Relevancy Scores

**Problem**: LLM gives vague or off-topic answers

**Solutions**:
1. Make questions more specific
2. Add examples to system prompt
3. Use few-shot prompting
4. Check if question is properly passed to LLM

### Evaluation Too Slow

**Problem**: Generation evaluation adds latency

**Solutions**:
1. Set `RAGAS_AUTO_EVAL=false` and evaluate in batch later
2. Sample only 10-20% of requests for evaluation
3. Run evaluation async (already done)
4. Use evaluation only in development/staging

## Best Practices

### 1. Always Evaluate Critical Flows

Focus generation evaluation on:
- Medical/health advice
- Financial recommendations
- Legal information
- User-facing chat responses

### 2. Set Up Alerts

```python
# Alert on low faithfulness (potential hallucination)
if metrics and metrics['faithfulness'] < 0.7:
    logger.error(f"HALLUCINATION ALERT: {metrics}")
    # Send to monitoring system
```

### 3. Track Trends Over Time

```python
# Monitor average scores daily
python view_ragas.py --results 30  # Last 30 days
```

### 4. A/B Test Prompts

Use generation metrics to compare different prompting strategies:

```python
# Test prompt A vs prompt B
metrics_a = await evaluate_generation(question, contexts, answer_a)
metrics_b = await evaluate_generation(question, contexts, answer_b)

# Choose prompt with better faithfulness
```

## Integration Checklist

- [ ] Add `RAGAS_ENABLED=true` to `.env`
- [ ] Run `python test_ragas_generation.py` to verify setup
- [ ] Integrate `evaluate_generation()` into agent orchestrator
- [ ] Set up monitoring for low faithfulness scores
- [ ] Create alerts for hallucination detection
- [ ] Review generation logs weekly
- [ ] Use metrics to improve prompts and retrieval

## Performance Impact

- **Latency**: ~1-2 seconds per evaluation (runs async)
- **Storage**: ~1KB per evaluation
- **CPU**: Moderate (RAGAS uses embeddings)

**Recommendation**: Enable in development/staging always. In production, sample 10-20% of requests or evaluate offline in batch.

## Comparison: Retrieval vs Generation Evaluation

| Aspect | Retrieval Eval | Generation Eval |
|--------|---------------|-----------------|
| **What** | Quality of retrieved contexts | Quality of LLM answers |
| **Metrics** | context_recall, context_precision | answer_relevancy, faithfulness |
| **When** | After vector search | After LLM generation |
| **Detects** | Poor search results | Hallucinations, vague answers |
| **File** | `ragas_results_*.jsonl` | `ragas_generation_*.jsonl` |

**Use both** for comprehensive RAG quality monitoring!
