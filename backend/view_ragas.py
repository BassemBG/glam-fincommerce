"""
RAGAS Evaluation Results Viewer

Usage:
    python view_ragas.py [options]

Options:
    --samples [date]     View samples for a specific date (default: today)
    --results [days]     View evaluation results for last N days (default: 7)
    --stats              Show overall statistics
    --pipeline <name>    Show metrics for specific pipeline
    --live               Enable live monitoring mode (refreshes every 30s)

Examples:
    python view_ragas.py --stats
    python view_ragas.py --samples 2026-01-29
    python view_ragas.py --results 3
    python view_ragas.py --pipeline search_closet
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

def get_ragas_dir() -> Path:
    """Get the RAGAS output directory"""
    base = Path(os.getcwd()) / "ragas_outputs"
    if not base.exists():
        print(f"❌ RAGAS output directory not found: {base}")
        print("   Make sure RAGAS_ENABLED=true in your .env file")
        sys.exit(1)
    return base

def read_jsonl(file_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records"""
    if not file_path.exists():
        return []
    
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                    if limit and len(records) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    return records

def show_stats():
    """Show overall RAGAS statistics"""
    ragas_dir = get_ragas_dir()
    
    print("\n" + "="*70)
    print("📊 RAGAS EVALUATION STATISTICS")
    print("="*70)
    
    # Count files
    sample_files = list(ragas_dir.glob("ragas_samples_*.jsonl"))
    result_files = list(ragas_dir.glob("ragas_results_*.jsonl"))
    
    print(f"\n📁 Output Directory: {ragas_dir}")
    print(f"   Sample Files: {len(sample_files)}")
    print(f"   Result Files: {len(result_files)}")
    
    # Count total samples and pipelines
    total_samples = 0
    pipelines = {}
    
    for file in sample_files:
        samples = read_jsonl(file)
        total_samples += len(samples)
        for s in samples:
            pipeline = s.get("pipeline", "unknown")
            pipelines[pipeline] = pipelines.get(pipeline, 0) + 1
    
    print(f"\n📈 Total Samples Recorded: {total_samples}")
    print(f"\n🔧 Pipelines Tracked:")
    for pipeline, count in sorted(pipelines.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {pipeline}: {count} samples")
    
    print("\n" + "="*70 + "\n")

def show_samples(date: Optional[str] = None, limit: int = 10):
    """Show recent samples"""
    ragas_dir = get_ragas_dir()
    date_str = date or datetime.utcnow().strftime("%Y-%m-%d")
    samples_file = ragas_dir / f"ragas_samples_{date_str}.jsonl"
    
    print("\n" + "="*70)
    print(f"📝 RAGAS SAMPLES - {date_str}")
    print("="*70)
    
    if not samples_file.exists():
        print(f"\n❌ No samples file found for {date_str}")
        print(f"   Looking for: {samples_file}")
        return
    
    samples = read_jsonl(samples_file, limit=limit)
    
    if not samples:
        print(f"\n⚠️  No samples recorded for {date_str}")
        return
    
    print(f"\n📊 Showing {len(samples)} most recent samples:\n")
    
    for i, sample in enumerate(samples, 1):
        pipeline = sample.get("pipeline", "unknown")
        question = sample.get("question", "")
        contexts_count = len(sample.get("contexts", []))
        answer_length = len(sample.get("answer", ""))
        timestamp = sample.get("timestamp", "")
        
        print(f"{i}. [{pipeline}]")
        print(f"   Time: {timestamp}")
        print(f"   Question: {question[:80]}{'...' if len(question) > 80 else ''}")
        print(f"   Retrieved: {contexts_count} contexts")
        print(f"   Answer: {answer_length} chars")
        print()
    
    print("="*70 + "\n")

def show_results(days: int = 7):
    """Show evaluation results"""
    ragas_dir = get_ragas_dir()
    
    print("\n" + "="*70)
    print(f"📊 RAGAS EVALUATION RESULTS - Last {days} days")
    print("="*70)
    
    results_all = []
    
    # Check last N days
    for i in range(days):
        check_date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        results_file = ragas_dir / f"ragas_results_{check_date}.jsonl"
        if results_file.exists():
            results_all.extend(read_jsonl(results_file))
    
    if not results_all:
        print(f"\n⚠️  No evaluation results found in last {days} days")
        print("   Make sure RAGAS_AUTO_EVAL=true in your .env file")
        return
    
    print(f"\n✅ Found {len(results_all)} evaluation runs\n")
    
    # Calculate averages
    all_metrics = []
    for result in results_all:
        if "results" in result:
            all_metrics.append(result["results"])
    
    if all_metrics:
        metric_keys = ["context_recall", "context_precision", "faithfulness", "answer_relevancy"]
        
        print("📈 Average Metrics Across All Evaluations:\n")
        for key in metric_keys:
            values = [m.get(key) for m in all_metrics if m.get(key) is not None]
            if values:
                avg = sum(values) / len(values)
                # Color code: green > 0.7, yellow > 0.5, red otherwise
                indicator = "🟢" if avg > 0.7 else "🟡" if avg > 0.5 else "🔴"
                print(f"   {indicator} {key.replace('_', ' ').title()}: {avg:.3f}")
        
        print("\n📊 Individual Evaluation Runs:\n")
        for i, result in enumerate(results_all[:5], 1):  # Show last 5
            timestamp = result.get("timestamp", "")
            count = result.get("count", 0)
            metrics = result.get("results", {})
            
            print(f"{i}. {timestamp} ({count} samples)")
            for key in metric_keys:
                if key in metrics:
                    print(f"   • {key}: {metrics[key]:.3f}")
            print()
    
    print("="*70 + "\n")

def show_pipeline(pipeline_name: str, days: int = 7):
    """Show metrics for specific pipeline"""
    ragas_dir = get_ragas_dir()
    
    print("\n" + "="*70)
    print(f"🔧 PIPELINE: {pipeline_name}")
    print("="*70)
    
    pipeline_samples = []
    
    # Collect samples for this pipeline
    for i in range(days):
        check_date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        samples_file = ragas_dir / f"ragas_samples_{check_date}.jsonl"
        if samples_file.exists():
            samples = read_jsonl(samples_file)
            pipeline_samples.extend([s for s in samples if s.get("pipeline") == pipeline_name])
    
    if not pipeline_samples:
        print(f"\n⚠️  No samples found for pipeline '{pipeline_name}' in last {days} days")
        return
    
    print(f"\n📊 Total Samples: {len(pipeline_samples)}")
    print(f"   Date Range: Last {days} days\n")
    
    # Show sample questions
    print("🔍 Sample Questions:\n")
    for i, sample in enumerate(pipeline_samples[:10], 1):
        question = sample.get("question", "")
        print(f"{i}. {question}")
    
    # Show unique users
    user_ids = set(s.get("metadata", {}).get("user_id") for s in pipeline_samples if s.get("metadata", {}).get("user_id"))
    if user_ids:
        print(f"\n👥 Unique Users: {len(user_ids)}")
    
    print("\n" + "="*70 + "\n")

def live_monitor():
    """Live monitoring mode - refreshes every 30s"""
    print("🔴 LIVE MONITORING MODE (Ctrl+C to exit)")
    print("   Refreshing every 30 seconds...\n")
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            show_stats()
            show_results(days=1)
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped\n")

def main():
    """Main CLI entry point"""
    args = sys.argv[1:]
    
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    if "--stats" in args:
        show_stats()
    
    elif "--samples" in args:
        idx = args.index("--samples")
        date = args[idx + 1] if len(args) > idx + 1 and not args[idx + 1].startswith("--") else None
        show_samples(date)
    
    elif "--results" in args:
        idx = args.index("--results")
        days = int(args[idx + 1]) if len(args) > idx + 1 and args[idx + 1].isdigit() else 7
        show_results(days)
    
    elif "--pipeline" in args:
        idx = args.index("--pipeline")
        if len(args) > idx + 1:
            pipeline_name = args[idx + 1]
            show_pipeline(pipeline_name)
        else:
            print("❌ Please specify a pipeline name")
    
    elif "--live" in args:
        live_monitor()
    
    else:
        print("❌ Unknown option. Use --help to see available commands")

if __name__ == "__main__":
    main()
