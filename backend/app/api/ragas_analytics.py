from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

router = APIRouter()

def _get_ragas_dir() -> Path:
    """Get the RAGAS output directory"""
    base = Path(os.getcwd()) / "ragas_outputs"
    base.mkdir(exist_ok=True)
    return base

def _read_jsonl(file_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records"""
    if not file_path.exists():
        return []
    
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
    return records

@router.get("/ragas/samples")
async def get_ragas_samples(
    date: Optional[str] = None,
    pipeline: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Retrieve RAGAS evaluation samples
    
    Args:
        date: Date string (YYYY-MM-DD), defaults to today
        pipeline: Filter by pipeline name (e.g., 'search_closet', 'search_zep_graph')
        limit: Maximum number of samples to return
    """
    try:
        ragas_dir = _get_ragas_dir()
        date_str = date or datetime.utcnow().strftime("%Y-%m-%d")
        samples_file = ragas_dir / f"ragas_samples_{date_str}.jsonl"
        
        samples = _read_jsonl(samples_file, limit=limit)
        
        # Filter by pipeline if specified
        if pipeline:
            samples = [s for s in samples if s.get("pipeline") == pipeline]
        
        return {
            "date": date_str,
            "total_samples": len(samples),
            "samples": samples
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ragas/results")
async def get_ragas_results(
    date: Optional[str] = None,
    days: int = 7
) -> Dict[str, Any]:
    """
    Retrieve RAGAS evaluation results
    
    Args:
        date: Date string (YYYY-MM-DD), defaults to today
        days: Number of days to look back
    """
    try:
        ragas_dir = _get_ragas_dir()
        results_all = []
        
        # Check last N days
        for i in range(days):
            check_date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            results_file = ragas_dir / f"ragas_results_{check_date}.jsonl"
            if results_file.exists():
                results_all.extend(_read_jsonl(results_file))
        
        if not results_all:
            return {
                "message": "No evaluation results found",
                "results": []
            }
        
        # Calculate averages across all evaluations
        all_metrics = []
        for result in results_all:
            if "results" in result:
                all_metrics.append(result["results"])
        
        if all_metrics:
            # Average metrics
            avg_metrics = {}
            metric_keys = ["context_recall", "context_precision", "faithfulness", "answer_relevancy"]
            for key in metric_keys:
                values = [m.get(key) for m in all_metrics if m.get(key) is not None]
                if values:
                    avg_metrics[key] = sum(values) / len(values)
        else:
            avg_metrics = {}
        
        return {
            "days_analyzed": days,
            "total_evaluations": len(results_all),
            "average_metrics": avg_metrics,
            "detailed_results": results_all
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ragas/stats")
async def get_ragas_stats() -> Dict[str, Any]:
    """Get overall RAGAS statistics"""
    try:
        ragas_dir = _get_ragas_dir()
        
        # Count files
        sample_files = list(ragas_dir.glob("ragas_samples_*.jsonl"))
        result_files = list(ragas_dir.glob("ragas_results_*.jsonl"))
        
        # Count total samples
        total_samples = 0
        pipelines = set()
        for file in sample_files:
            samples = _read_jsonl(file)
            total_samples += len(samples)
            for s in samples:
                pipelines.add(s.get("pipeline"))
        
        return {
            "total_sample_files": len(sample_files),
            "total_result_files": len(result_files),
            "total_samples_recorded": total_samples,
            "pipelines_tracked": list(pipelines),
            "output_directory": str(ragas_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ragas/pipeline/{pipeline_name}")
async def get_pipeline_metrics(
    pipeline_name: str,
    days: int = 7
) -> Dict[str, Any]:
    """
    Get metrics for a specific RAG pipeline
    
    Args:
        pipeline_name: Name of the pipeline (e.g., 'search_closet', 'search_brand_catalog')
        days: Number of days to analyze
    """
    try:
        ragas_dir = _get_ragas_dir()
        pipeline_samples = []
        
        # Collect samples for this pipeline
        for i in range(days):
            check_date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            samples_file = ragas_dir / f"ragas_samples_{check_date}.jsonl"
            if samples_file.exists():
                samples = _read_jsonl(samples_file)
                pipeline_samples.extend([s for s in samples if s.get("pipeline") == pipeline_name])
        
        if not pipeline_samples:
            return {
                "pipeline": pipeline_name,
                "message": "No samples found for this pipeline",
                "total_samples": 0
            }
        
        return {
            "pipeline": pipeline_name,
            "total_samples": len(pipeline_samples),
            "date_range": f"Last {days} days",
            "sample_questions": [s.get("question") for s in pipeline_samples[:10]],
            "metadata_summary": {
                "user_ids": list(set(s.get("metadata", {}).get("user_id") for s in pipeline_samples if s.get("metadata", {}).get("user_id")))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
