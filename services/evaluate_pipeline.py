"""
VOFC Document Processing Pipeline Evaluation Harness
Runs documents through the full pipeline and collects metrics.
"""

import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from services.preprocess import preprocess_document
from services.ollama_client import run_model_on_chunks
from services.postprocess import postprocess_results
from services.supabase_client import save_results

# Configuration - Use C:\Tools\Ollama\Data
BASE_DIR = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
EVAL_DIR = BASE_DIR / "eval_docs"
REPORTS_DIR = BASE_DIR / "eval_reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = REPORTS_DIR / 'evaluation.log'
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def evaluate_document(path, save=False, model="psa-engine:latest"):
    """
    Evaluate a single document through the full pipeline.
    
    Args:
        path: Path to document file
        save: Whether to save results to Supabase
        model: Ollama model to use
    
    Returns:
        Dictionary with metrics
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    
    logger.info(f"Evaluating document: {file_path.name}")
    metrics = {
        "file": file_path.name,
        "file_size_kb": round(file_path.stat().st_size / 1024, 2),
        "status": "success",
        "error": None
    }
    
    try:
        # Step 1: Preprocessing
        start = time.time()
        chunks = preprocess_document(str(file_path))
        t_extract = time.time() - start
        
        metrics.update({
            "chunks": len(chunks),
            "total_chars": sum(c.get('char_count', 0) for c in chunks),
            "avg_chunk_size": round(sum(c.get('char_count', 0) for c in chunks) / len(chunks) if chunks else 0, 0),
            "extraction_time": round(t_extract, 2)
        })
        
        if not chunks:
            metrics["status"] = "error"
            metrics["error"] = "No chunks created"
            return metrics
        
        # Step 2: Model inference
        start = time.time()
        model_out = run_model_on_chunks(chunks, model=model)
        t_model = time.time() - start
        
        # Count successful vs failed chunks
        successful_chunks = sum(1 for r in model_out if r.get('status') != 'failed' and 'error' not in r)
        failed_chunks = len(model_out) - successful_chunks
        
        metrics.update({
            "raw_records": len(model_out),
            "successful_chunks": successful_chunks,
            "failed_chunks": failed_chunks,
            "model_time": round(t_model, 2),
            "avg_time_per_chunk": round(t_model / len(chunks) if chunks else 0, 2)
        })
        
        # Step 3: Post-processing
        start = time.time()
        final = postprocess_results(model_out)
        t_post = time.time() - start
        
        # Count records with taxonomy resolved
        with_discipline = sum(1 for r in final if r.get('discipline_id'))
        with_sector = sum(1 for r in final if r.get('sector_id'))
        with_subsector = sum(1 for r in final if r.get('subsector_id'))
        
        metrics.update({
            "unique_records": len(final),
            "deduplication_rate": round((len(model_out) - len(final)) / len(model_out) * 100, 1) if model_out else 0,
            "with_discipline": with_discipline,
            "with_sector": with_sector,
            "with_subsector": with_subsector,
            "postprocess_time": round(t_post, 2)
        })
        
        # Step 4: Save to Supabase (optional)
        if save and final:
            start = time.time()
            try:
                save_stats = save_results(final, source_file=file_path.name)
                t_save = time.time() - start
                metrics.update({
                    "supabase_saved": save_stats.get('saved', 0),
                    "supabase_errors": save_stats.get('errors', 0),
                    "save_time": round(t_save, 2)
                })
            except Exception as e:
                logger.error(f"Failed to save to Supabase: {str(e)}")
                metrics["supabase_error"] = str(e)
                metrics["save_time"] = 0
        
        # Calculate total time
        total_time = t_extract + t_model + t_post
        if save:
            total_time += metrics.get('save_time', 0)
        
        metrics.update({
            "total_time": round(total_time, 2),
            "throughput_chunks_per_sec": round(len(chunks) / total_time if total_time > 0 else 0, 2)
        })
        
        logger.info(f"Evaluation complete for {file_path.name}: {metrics}")
        
    except Exception as e:
        logger.exception(f"Error evaluating {file_path.name}: {str(e)}")
        metrics.update({
            "status": "error",
            "error": str(e)
        })
    
    return metrics


def compare_with_reference(preds, refs):
    """
    Compare predictions with reference (gold-standard) data.
    
    Args:
        preds: List of predicted vulnerability/OFC strings
        refs: List of reference vulnerability/OFC strings
    
    Returns:
        Dictionary with precision, recall, F1 score
    """
    if not preds or not refs:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "tp": 0,
            "fp": 0,
            "fn": 0
        }
    
    # Normalize for comparison
    pred_set = set(pred.lower().strip() for pred in preds if pred)
    ref_set = set(ref.lower().strip() for ref in refs if ref)
    
    tp = len(pred_set & ref_set)  # True positives
    fp = len(pred_set - ref_set)   # False positives
    fn = len(ref_set - pred_set)   # False negatives
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "total_predicted": len(pred_set),
        "total_reference": len(ref_set)
    }


def load_reference_data(reference_file):
    """
    Load reference (gold-standard) data from JSON or CSV.
    
    Expected JSON format:
    {
        "document.pdf": {
            "vulnerabilities": ["vuln1", "vuln2"],
            "ofcs": ["ofc1", "ofc2"]
        }
    }
    
    Args:
        reference_file: Path to reference data file
    
    Returns:
        Dictionary mapping filename to reference data
    """
    ref_path = Path(reference_file)
    
    if not ref_path.exists():
        logger.warning(f"Reference file not found: {reference_file}")
        return {}
    
    try:
        if ref_path.suffix.lower() == '.json':
            with open(ref_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif ref_path.suffix.lower() == '.csv' and PANDAS_AVAILABLE:
            df = pd.read_csv(ref_path)
            # Assume CSV has columns: filename, vulnerability, ofc
            refs = {}
            for _, row in df.iterrows():
                filename = row.get('filename', '')
                if filename not in refs:
                    refs[filename] = {"vulnerabilities": [], "ofcs": []}
                if row.get('vulnerability'):
                    refs[filename]["vulnerabilities"].append(row['vulnerability'])
                if row.get('ofc'):
                    refs[filename]["ofcs"].append(row['ofc'])
            return refs
        else:
            logger.error(f"Unsupported reference file format: {ref_path.suffix}")
            return {}
    except Exception as e:
        logger.error(f"Failed to load reference data: {str(e)}")
        return {}


def run_batch(eval_dir=None, save=False, model="psa-engine:latest", reference_file=None):
    """
    Run batch evaluation on all documents in eval directory.
    
    Args:
        eval_dir: Directory containing documents to evaluate
        save: Whether to save results to Supabase
        model: Ollama model to use
        reference_file: Optional path to reference data for accuracy comparison
    
    Returns:
        DataFrame with all metrics
    """
    if eval_dir is None:
        eval_dir = EVAL_DIR
    
    eval_path = Path(eval_dir)
    if not eval_path.exists():
        logger.error(f"Evaluation directory not found: {eval_dir}")
        print(f"Error: Evaluation directory not found: {eval_dir}")
        return None
    
    # Load reference data if provided
    reference_data = {}
    if reference_file:
        reference_data = load_reference_data(reference_file)
        logger.info(f"Loaded reference data for {len(reference_data)} documents")
    
    # Find all supported documents
    supported_exts = ('.pdf', '.docx', '.txt')
    files = [f for f in eval_path.iterdir() 
             if f.is_file() and f.suffix.lower() in supported_exts]
    
    if not files:
        logger.warning(f"No documents found in {eval_dir}")
        print(f"No documents found in {eval_dir}")
        return None
    
    logger.info(f"Found {len(files)} documents to evaluate")
    print(f"\n{'='*80}")
    print(f"Evaluating {len(files)} documents")
    print(f"{'='*80}\n")
    
    all_metrics = []
    
    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file_path.name}")
        try:
            metrics = evaluate_document(str(file_path), save=save, model=model)
            
            # Add accuracy metrics if reference data available
            if reference_data and file_path.name in reference_data:
                ref = reference_data[file_path.name]
                
                # Get predictions from model output (would need to be stored)
                # For now, we'll extract from final results
                # This is a simplified version - you may need to adjust based on actual data structure
                pred_vulns = [r.get('vulnerability', '') for r in postprocess_results(
                    run_model_on_chunks(preprocess_document(str(file_path)), model=model)
                )]
                ref_vulns = ref.get('vulnerabilities', [])
                
                accuracy = compare_with_reference(pred_vulns, ref_vulns)
                metrics.update({
                    "accuracy_precision": accuracy['precision'],
                    "accuracy_recall": accuracy['recall'],
                    "accuracy_f1": accuracy['f1']
                })
            
            all_metrics.append(metrics)
            print(f"  ✓ Completed: {metrics.get('unique_records', 0)} records, {metrics.get('total_time', 0)}s")
            
        except Exception as e:
            logger.exception(f"Error evaluating {file_path.name}: {str(e)}")
            print(f"  ✗ Error: {str(e)}")
            all_metrics.append({
                "file": file_path.name,
                "status": "error",
                "error": str(e)
            })
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON report
    json_report = REPORTS_DIR / f"evaluation_report_{timestamp}.json"
    with open(json_report, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(files),
            "model": model,
            "save_to_supabase": save,
            "metrics": all_metrics
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved JSON report: {json_report}")
    
    # Generate CSV and console table if pandas available
    if PANDAS_AVAILABLE and all_metrics:
        df = pd.DataFrame(all_metrics)
        
        # Save CSV report
        csv_report = REPORTS_DIR / f"evaluation_report_{timestamp}.csv"
        df.to_csv(csv_report, index=False)
        logger.info(f"Saved CSV report: {csv_report}")
        
        # Print summary table
        print(f"\n{'='*80}")
        print("EVALUATION SUMMARY")
        print(f"{'='*80}\n")
        
        # Select key columns for display
        display_cols = ['file', 'chunks', 'unique_records', 'total_time', 'status']
        if 'accuracy_f1' in df.columns:
            display_cols.append('accuracy_f1')
        
        available_cols = [col for col in display_cols if col in df.columns]
        print(df[available_cols].to_string(index=False))
        
        # Print statistics
        print(f"\n{'='*80}")
        print("STATISTICS")
        print(f"{'='*80}\n")
        
        successful = df[df['status'] == 'success']
        if len(successful) > 0:
            print(f"Documents processed: {len(successful)}/{len(df)}")
            print(f"Average total time: {successful['total_time'].mean():.2f} sec/document")
            print(f"Average chunks: {successful['chunks'].mean():.1f}")
            print(f"Average records: {successful['unique_records'].mean():.1f}")
            print(f"Total records: {successful['unique_records'].sum()}")
            
            if 'accuracy_f1' in successful.columns:
                print(f"Average F1 score: {successful['accuracy_f1'].mean():.3f}")
        
        print(f"\nReports saved to: {REPORTS_DIR}")
        print(f"  - JSON: {json_report.name}")
        if PANDAS_AVAILABLE:
            print(f"  - CSV: {csv_report.name}")
        print(f"  - Log: evaluation.log")
        print(f"\n{'='*80}\n")
        
        return df
    else:
        # Print basic summary without pandas
        print(f"\n{'='*80}")
        print("EVALUATION SUMMARY")
        print(f"{'='*80}\n")
        
        successful = [m for m in all_metrics if m.get('status') == 'success']
        if successful:
            avg_time = sum(m.get('total_time', 0) for m in successful) / len(successful)
            total_records = sum(m.get('unique_records', 0) for m in successful)
            print(f"Documents processed: {len(successful)}/{len(all_metrics)}")
            print(f"Average total time: {avg_time:.2f} sec/document")
            print(f"Total records: {total_records}")
        
        print(f"\nReports saved to: {REPORTS_DIR}")
        print(f"  - JSON: {json_report.name}")
        print(f"  - Log: evaluation.log")
        print(f"\n{'='*80}\n")
        
        return all_metrics


if __name__ == "__main__":
    """
    CLI interface for pipeline evaluation.
    
    Usage:
        python evaluate_pipeline.py                    # Dry run (no Supabase save)
        python evaluate_pipeline.py --save             # Save to Supabase
        python evaluate_pipeline.py --model custom     # Use custom model
        python evaluate_pipeline.py --reference ref.json  # Compare with reference
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluate VOFC Document Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run evaluation
  python evaluate_pipeline.py
  
  # Save results to Supabase
  python evaluate_pipeline.py --save
  
  # Use custom model
  python evaluate_pipeline.py --model psa-engine:v2
  
  # Compare with reference data
  python evaluate_pipeline.py --reference gold_standard.json
        """
    )
    
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to Supabase (default: dry run)"
    )
    
    parser.add_argument(
        "--model",
        default="psa-engine:latest",
        help="Ollama model to use (default: psa-engine:latest)"
    )
    
    parser.add_argument(
        "--eval-dir",
        type=str,
        default=None,
        help=f"Directory containing documents to evaluate (default: {EVAL_DIR})"
    )
    
    parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help="Path to reference/gold-standard data file (JSON or CSV)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print("VOFC Pipeline Evaluation Harness")
    print(f"{'='*80}")
    print(f"Evaluation directory: {args.eval_dir or EVAL_DIR}")
    print(f"Model: {args.model}")
    print(f"Save to Supabase: {args.save}")
    if args.reference:
        print(f"Reference data: {args.reference}")
    print(f"{'='*80}\n")
    
    try:
        run_batch(
            eval_dir=args.eval_dir,
            save=args.save,
            model=args.model,
            reference_file=args.reference
        )
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        logger.info("Evaluation interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        logger.exception("Evaluation failed")
        exit(1)

