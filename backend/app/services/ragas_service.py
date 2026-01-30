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
    # Use the old metrics API (still works, will be deprecated in v1.0)
    from ragas.metrics import answer_relevancy, faithfulness
    try:
        from ragas.metrics import context_recall, context_precision
    except ImportError:
        context_recall = None
        context_precision = None
    from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace, HuggingFaceEmbeddings

except Exception as e:  # pragma: no cover - optional dependency
    logger.warning(f"[RAGAS] Failed to import required packages: {e}")
    Dataset = None
    evaluate = None
    answer_relevancy = None
    faithfulness = None
    context_recall = None
    context_precision = None
    HuggingFaceEndpoint = None
    ChatHuggingFace = None
    HuggingFaceEmbeddings = None


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

    def _get_eval_llm(self):
        if HuggingFaceEndpoint is None or ChatHuggingFace is None:
            return None

        # Primary: Try HuggingFace token first
        hf_token = getattr(settings, "HF_TOKEN", None) or getattr(settings, "RAGAS_LLM_API_KEY", None)
        if hf_token:
            try:
                model = getattr(settings, "RAGAS_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
                logger.info(f"[RAGAS] Using HuggingFace model: {model}")
                # Use ChatHuggingFace wrapper for conversational models
                llm = ChatHuggingFace(
                    llm=HuggingFaceEndpoint(
                        repo_id=model,
                        huggingfacehub_api_token=hf_token,
                        temperature=0.1,
                        max_new_tokens=512,
                        timeout=120,
                    )
                )
                return llm
            except Exception as e:
                logger.warning(f"[RAGAS] HuggingFace setup failed: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Fallback: Try OpenAI if available
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
                logger.info("[RAGAS] Using OpenAI model: gpt-4o-mini")
                return llm
            except Exception as e:
                logger.warning(f"[RAGAS] OpenAI setup failed: {e}")
        
        logger.info("[RAGAS] No LLM API key configured - set HF_TOKEN or OPENAI_API_KEY to enable evaluation")
        return None

    def _get_eval_embeddings(self):
        if HuggingFaceEmbeddings is None:
            return None

        model_name = getattr(settings, "RAGAS_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        try:
            embeddings = HuggingFaceEmbeddings(model_name=model_name)
            return embeddings
        except Exception as e:
            logger.warning(f"[RAGAS] Failed to load embeddings: {e}")
            return None

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

    def _sanitize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Convert NaN values to None for JSON serialization."""
        import math
        sanitized = {}
        for key, val in metrics.items():
            if isinstance(val, float):
                if math.isnan(val):
                    sanitized[key] = None
                else:
                    sanitized[key] = round(val, 4)
            else:
                sanitized[key] = val
        return sanitized

    def _extract_metadata_summary(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        user_ids = set()
        chat_ids = set()
        metadata_keys = set()

        for sample in samples:
            metadata = sample.get("metadata") or {}
            if isinstance(metadata, dict):
                metadata_keys.update(metadata.keys())
                user_id = metadata.get("user_id")
                if user_id:
                    user_ids.add(user_id)
                chat_id = metadata.get("chat_id") or metadata.get("thread_id")
                if chat_id:
                    chat_ids.add(chat_id)

        return {
            "user_ids": sorted(user_ids),
            "chat_ids": sorted(chat_ids),
            "metadata_keys": sorted(metadata_keys),
        }

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

        llm = self._get_eval_llm()
        embeddings = self._get_eval_embeddings()
        if llm is None:
            logger.warning("[RAGAS] No LLM configured; skipping evaluation")
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
            
            # Set llm and embeddings on metrics
            faithfulness.llm = llm
            faithfulness.embeddings = embeddings
            answer_relevancy.llm = llm
            answer_relevancy.embeddings = embeddings
            
            metrics_to_use = [faithfulness, answer_relevancy]
            
            # Add context metrics if available
            if context_recall is not None and context_precision is not None:
                context_recall.llm = llm
                context_recall.embeddings = embeddings
                context_precision.llm = llm
                context_precision.embeddings = embeddings
                metrics_to_use = [context_recall, context_precision, faithfulness, answer_relevancy]
            
            results = evaluate(
                dataset,
                metrics=metrics_to_use,
            )
            
            # Convert results - use to_pandas() and extract first row
            df = results.to_pandas()
            if len(df) > 0:
                # Extract the metric columns
                metric_cols = [col for col in df.columns if col in ['answer_relevancy', 'faithfulness', 'context_recall', 'context_precision']]
                results_dict = {col: df[col].iloc[0] for col in metric_cols}
            else:
                results_dict = {}
            
            sanitized_results = self._sanitize_metrics(results_dict)
            logger.info(f"[RAGAS] Evaluation completed: {sanitized_results}")
            
            output = {
                "timestamp": datetime.utcnow().isoformat(),
                "evaluation_type": "retrieval_and_generation",
                "results": sanitized_results,
                "count": len(samples),
                "pipelines": list({s["pipeline"] for s in samples}),
                "metadata_summary": self._extract_metadata_summary(samples),
            }
            path = self._output_path("results")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(output, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[RAGAS] Evaluation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _evaluate_generation_only(self, samples: List[Dict[str, Any]]) -> None:
        """
        Evaluate ONLY the generation quality (answer relevancy + faithfulness).
        This focuses on LLM output quality, not retrieval quality.
        """
        if evaluate is None or Dataset is None:
            logger.warning("[RAGAS] ragas/datasets not available; skipping generation evaluation")
            return

        llm = self._get_eval_llm()
        embeddings = self._get_eval_embeddings()
        if llm is None:
            logger.warning("[RAGAS] No LLM configured; skipping generation evaluation")
            return

        try:
            data = {
                "question": [s["question"] for s in samples],
                "contexts": [s["contexts"] for s in samples],
                "answer": [s["answer"] for s in samples],
            }
            dataset = Dataset.from_dict(data)
            
            # Set llm and embeddings on metrics
            answer_relevancy.llm = llm
            answer_relevancy.embeddings = embeddings
            faithfulness.llm = llm
            faithfulness.embeddings = embeddings
            
            # Only generation metrics: answer_relevancy + faithfulness
            results = evaluate(
                dataset,
                metrics=[
                    answer_relevancy,  # Does answer address the question?
                    faithfulness,      # Is answer grounded in context?
                ],
            )
            
            # Convert results - use to_pandas() and extract first row
            df = results.to_pandas()
            if len(df) > 0:
                # Extract the metric columns
                metric_cols = [col for col in df.columns if col in ['answer_relevancy', 'faithfulness']]
                results_dict = {col: df[col].iloc[0] for col in metric_cols}
            else:
                results_dict = {}
            
            sanitized_results = self._sanitize_metrics(results_dict)
            
            logger.info(f"[RAGAS] Generation evaluation: {sanitized_results}")
            
            output = {
                "timestamp": datetime.utcnow().isoformat(),
                "evaluation_type": "generation_only",
                "results": sanitized_results,
                "count": len(samples),
                "pipelines": list({s["pipeline"] for s in samples}),
                "metadata_summary": self._extract_metadata_summary(samples),
            }
            path = self._output_path("generation")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(output, ensure_ascii=False) + "\n")
                
            logger.info(f"[RAGAS] Generation evaluation completed: {len(samples)} samples")
        except Exception as e:
            logger.warning(f"[RAGAS] Generation evaluation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    async def evaluate_generation(
        self,
        *,
        question: str,
        contexts: List[str],
        answer: str,
        pipeline: str = "generation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Evaluate a single LLM-generated answer.
        Returns metrics: {answer_relevancy, faithfulness}
        """
        if not self.enabled:
            return None

        normalized_contexts = self._normalize_contexts(contexts)
        if not normalized_contexts:
            return None

        sample = {
            "pipeline": pipeline,
            "question": question,
            "contexts": normalized_contexts,
            "answer": answer,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Evaluate generation quality (stores both sample + evaluation)
        result = await asyncio.to_thread(self._evaluate_generation_sync, sample)
        return result

    def _evaluate_generation_sync(self, sample: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Synchronous generation evaluation for a single sample"""
        if evaluate is None or Dataset is None:
            logger.warning("[RAGAS] evaluate or Dataset is None")
            return None

        llm = self._get_eval_llm()
        embeddings = self._get_eval_embeddings()
        if llm is None:
            logger.info("[RAGAS] LLM not configured - skipping generation evaluation. Set OPENAI_API_KEY to enable.")
            return None
        if embeddings is None:
            logger.warning("[RAGAS] Embeddings is None")
            return None

        try:
            data = {
                "question": [sample["question"]],
                "contexts": [sample["contexts"]],
                "answer": [sample["answer"]],
            }
            dataset = Dataset.from_dict(data)
            
            # Set llm and embeddings on metrics
            answer_relevancy.llm = llm
            answer_relevancy.embeddings = embeddings
            faithfulness.llm = llm
            faithfulness.embeddings = embeddings
            
            results = evaluate(
                dataset,
                metrics=[
                    answer_relevancy,
                    faithfulness,
                ],
            )
            
            # Convert results - use to_pandas() and extract first row
            df = results.to_pandas()
            if len(df) > 0:
                # Extract the metric columns (not user_input, response, etc.)
                metric_cols = [col for col in df.columns if col in ['answer_relevancy', 'faithfulness', 'context_recall', 'context_precision']]
                results_dict = {col: df[col].iloc[0] for col in metric_cols}
            else:
                results_dict = {}
            
            sanitized_results = self._sanitize_metrics(results_dict)
            
            logger.info(f"[RAGAS] Single generation eval: {sanitized_results}")
            
            metrics = {
                "answer_relevancy": sanitized_results.get("answer_relevancy"),
                "faithfulness": sanitized_results.get("faithfulness"),
            }
            
            # Store sample + evaluation together
            sample_with_eval = {
                **sample,
                "evaluation": sanitized_results,
            }
            path_sample = self._output_path("samples")
            with open(path_sample, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample_with_eval, ensure_ascii=False) + "\n")
            
            # Also store in generation file
            output = {
                "timestamp": datetime.utcnow().isoformat(),
                "evaluation_type": "generation_only",
                "results": sanitized_results,
                "count": 1,
                "pipelines": [sample["pipeline"]],
                "question": sample["question"],
                "answer_preview": sample["answer"][:100],
                "metadata": sample.get("metadata") or {},
            }
            path = self._output_path("generation")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(output, ensure_ascii=False) + "\n")
            
            return metrics
        except Exception as e:
            logger.warning(f"[RAGAS] Generation evaluation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


ragas_service = RagasService()