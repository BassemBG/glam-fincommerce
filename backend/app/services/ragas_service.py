import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        context_recall,
        context_precision,
        faithfulness,
        answer_relevancy,
    )
except Exception:  # pragma: no cover - optional dependency
    Dataset = None
    evaluate = None
    context_recall = None
    context_precision = None
    faithfulness = None
    answer_relevancy = None


class RagasService:
    def __init__(self) -> None:
        self.enabled = getattr(settings, "RAGAS_ENABLED", False)
        self.auto_eval = getattr(settings, "RAGAS_AUTO_EVAL", False)
        self.output_dir = getattr(settings, "RAGAS_OUTPUT_DIR", "ragas_outputs")
        self.max_samples = getattr(settings, "RAGAS_MAX_SAMPLES", 200)
        self.ground_truth_fallback = getattr(settings, "RAGAS_GROUND_TRUTH_FALLBACK", "answer")
        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def _ensure_output_dir(self) -> str:
        base_dir = os.path.join(os.getcwd(), self.output_dir)
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _output_path(self, suffix: str) -> str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        base_dir = self._ensure_output_dir()
        return os.path.join(base_dir, f"ragas_{suffix}_{date_str}.jsonl")

    def _normalize_contexts(self, contexts: List[str]) -> List[str]:
        return [c for c in contexts if isinstance(c, str) and c.strip()]

    async def record_sample(
        self,
        *,
        pipeline: str,
        question: str,
        contexts: List[str],
        answer: str,
        ground_truth: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        normalized_contexts = self._normalize_contexts(contexts)
        if not normalized_contexts:
            return

        sample = {
            "pipeline": pipeline,
            "question": question,
            "contexts": normalized_contexts,
            "answer": answer,
            "ground_truth": ground_truth,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with self._lock:
            self._buffer.append(sample)
            if len(self._buffer) > self.max_samples:
                self._buffer = self._buffer[-self.max_samples :]

        await asyncio.to_thread(self._append_sample_to_file, sample)

        if self.auto_eval:
            await asyncio.to_thread(self._evaluate_and_store, [sample])

    def _append_sample_to_file(self, sample: Dict[str, Any]) -> None:
        try:
            path = self._output_path("samples")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[RAGAS] Failed to store sample: {e}")

    def _evaluate_and_store(self, samples: List[Dict[str, Any]]) -> None:
        if evaluate is None or Dataset is None:
            logger.warning("[RAGAS] ragas/datasets not available; skipping evaluation")
            return

        try:
            data = {
                "question": [s["question"] for s in samples],
                "contexts": [s["contexts"] for s in samples],
                "answer": [s["answer"] for s in samples],
                "ground_truth": [
                    (s.get("ground_truth") or (s["answer"] if self.ground_truth_fallback == "answer" else ""))
                    for s in samples
                ],
            }
            dataset = Dataset.from_dict(data)
            results = evaluate(
                dataset,
                metrics=[
                    context_recall,
                    context_precision,
                    faithfulness,
                    answer_relevancy,
                ],
            )
            output = {
                "timestamp": datetime.utcnow().isoformat(),
                "results": results,
                "count": len(samples),
                "pipelines": list({s["pipeline"] for s in samples}),
            }
            path = self._output_path("results")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(output, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.warning(f"[RAGAS] Evaluation failed: {e}")


ragas_service = RagasService()