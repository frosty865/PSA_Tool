"""
Benchmark Evaluator for VOFC Engine
Evaluates model extraction performance against predefined benchmarks.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)

# Default benchmark file path
DEFAULT_BENCHMARK_PATH = Path(r"C:\Tools\Ollama\Data\automation\vofc_benchmark_SiteSecurityDesignGuide.json")


def load_benchmark(benchmark_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load benchmark configuration from JSON file.
    
    Args:
        benchmark_path: Path to benchmark JSON file (default: Site Security Design Guide benchmark)
        
    Returns:
        Dictionary with benchmark configuration
    """
    if benchmark_path is None:
        benchmark_path = DEFAULT_BENCHMARK_PATH
    
    if not benchmark_path.exists():
        logger.warning(f"Benchmark file not found: {benchmark_path}")
        return {}
    
    try:
        with open(benchmark_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load benchmark: {e}")
        return {}


def extract_metrics_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metrics from a processing result.
    
    Args:
        result: Processing result dictionary (from phase1_parser, phase2_engine, etc.)
        
    Returns:
        Dictionary with extracted metrics
    """
    metrics = {
        "vulnerabilities": 0,
        "ofcs": 0,
        "unique_vulnerabilities": set(),
        "domains": set(),
        "json_errors": 0,
        "total_records": 0,
        "vulnerability_ofc_pairs": []
    }
    
    # Handle different result structures
    records = []
    if "records" in result:
        records = result["records"]
    elif "all_phase2_records" in result:
        records = result["all_phase2_records"]
    elif "vulnerabilities" in result:
        records = result["vulnerabilities"]
    
    metrics["total_records"] = len(records)
    
    # Process records
    for rec in records:
        # Handle nested structure (records with "vulnerabilities" array inside)
        if "vulnerabilities" in rec and isinstance(rec["vulnerabilities"], list):
            for vuln in rec["vulnerabilities"]:
                vuln_text = vuln.get("vulnerability") or vuln.get("vulnerability_name") or vuln.get("title", "")
                ofc_text = vuln.get("ofc") or ""
                ofcs_list = vuln.get("options_for_consideration", [])
                
                if vuln_text:
                    metrics["vulnerabilities"] += 1
                    metrics["unique_vulnerabilities"].add(vuln_text.lower().strip())
                    
                    # Count OFCs
                    if ofc_text:
                        metrics["ofcs"] += 1
                        metrics["vulnerability_ofc_pairs"].append((vuln_text, ofc_text))
                    if ofcs_list:
                        for ofc in ofcs_list:
                            if ofc:
                                metrics["ofcs"] += 1
                                metrics["vulnerability_ofc_pairs"].append((vuln_text, str(ofc)))
                    
                    # Extract domain/category
                    domain = vuln.get("category") or vuln.get("domain") or rec.get("category", "")
                    if domain:
                        metrics["domains"].add(domain)
        else:
            # Flat structure
            vuln_text = rec.get("vulnerability") or rec.get("vulnerability_name") or rec.get("title", "")
            ofc_text = rec.get("ofc") or ""
            ofcs_list = rec.get("options_for_consideration", [])
            
            if vuln_text:
                metrics["vulnerabilities"] += 1
                metrics["unique_vulnerabilities"].add(vuln_text.lower().strip())
                
                # Count OFCs
                if ofc_text:
                    metrics["ofcs"] += 1
                    metrics["vulnerability_ofc_pairs"].append((vuln_text, ofc_text))
                if ofcs_list:
                    for ofc in ofcs_list:
                        if ofc:
                            metrics["ofcs"] += 1
                            metrics["vulnerability_ofc_pairs"].append((vuln_text, str(ofc)))
                
                # Extract domain/category
                domain = rec.get("category") or rec.get("domain", "")
                if domain:
                    metrics["domains"].add(domain)
    
    # Convert sets to counts
    metrics["unique_vulnerabilities_count"] = len(metrics["unique_vulnerabilities"])
    metrics["domains_count"] = len(metrics["domains"])
    
    return metrics


def evaluate_against_benchmark(result: Dict[str, Any], benchmark_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Evaluate extraction results against benchmark.
    
    Args:
        result: Processing result dictionary
        benchmark_path: Path to benchmark JSON file
        
    Returns:
        Dictionary with evaluation scores and pass/fail status
    """
    benchmark = load_benchmark(benchmark_path)
    if not benchmark:
        logger.warning("No benchmark loaded, skipping evaluation")
        return {"error": "No benchmark loaded"}
    
    metrics = extract_metrics_from_result(result)
    evaluation = {
        "metrics": metrics,
        "scores": {},
        "passed": False,
        "overall_score": 0.0
    }
    
    # Extract benchmark targets
    expected = benchmark.get("expected_counts", {})
    benchmarks = benchmark.get("benchmarks", {})
    expected_domains = benchmark.get("expected_domains", [])
    
    # Score 1: Vulnerability count
    vuln_target = expected.get("vulnerabilities_target", 260)
    vuln_min = expected.get("vulnerabilities_min", 230)
    vuln_max = expected.get("vulnerabilities_max", 300)
    
    if metrics["vulnerabilities"] >= vuln_min and metrics["vulnerabilities"] <= vuln_max:
        # Within acceptable range
        if metrics["vulnerabilities"] >= vuln_target:
            vuln_score = 1.0
        else:
            # Linear interpolation between min and target
            vuln_score = 0.5 + 0.5 * (metrics["vulnerabilities"] - vuln_min) / (vuln_target - vuln_min)
    elif metrics["vulnerabilities"] < vuln_min:
        # Below minimum
        vuln_score = max(0.0, metrics["vulnerabilities"] / vuln_min)
    else:
        # Above maximum (over-extraction)
        vuln_score = max(0.0, 1.0 - (metrics["vulnerabilities"] - vuln_max) / vuln_max)
    
    evaluation["scores"]["vulnerability_count"] = vuln_score
    
    # Score 2: OFC count
    ofc_target = expected.get("ofcs_target", 700)
    ofc_min = expected.get("ofcs_min", 600)
    ofc_max = expected.get("ofcs_max", 750)
    
    if metrics["ofcs"] >= ofc_min and metrics["ofcs"] <= ofc_max:
        if metrics["ofcs"] >= ofc_target:
            ofc_score = 1.0
        else:
            ofc_score = 0.5 + 0.5 * (metrics["ofcs"] - ofc_min) / (ofc_target - ofc_min)
    elif metrics["ofcs"] < ofc_min:
        ofc_score = max(0.0, metrics["ofcs"] / ofc_min)
    else:
        ofc_score = max(0.0, 1.0 - (metrics["ofcs"] - ofc_max) / ofc_max)
    
    evaluation["scores"]["ofc_count"] = ofc_score
    
    # Score 3: Deduplication ratio
    if metrics["total_records"] > 0:
        dedup_ratio = metrics["unique_vulnerabilities_count"] / metrics["total_records"]
        dedup_target = benchmarks.get("deduplication_ratio", {}).get("target", 0.85)
        dedup_score = min(1.0, dedup_ratio / dedup_target)
    else:
        dedup_score = 0.0
    
    evaluation["scores"]["deduplication_ratio"] = dedup_score
    
    # Score 4: Category coverage
    if expected_domains:
        domain_coverage = len([d for d in metrics["domains"] if any(exp in str(d) for exp in expected_domains)]) / len(expected_domains)
        coverage_target = benchmarks.get("category_coverage", {}).get("target", 0.9)
        coverage_score = min(1.0, domain_coverage / coverage_target)
    else:
        coverage_score = 1.0
    
    evaluation["scores"]["category_coverage"] = coverage_score
    
    # Score 5: Average OFCs per vulnerability
    if metrics["vulnerabilities"] > 0:
        avg_ofc = metrics["ofcs"] / metrics["vulnerabilities"]
        avg_target = benchmarks.get("average_ofc_per_vulnerability", {}).get("target", 2.5)
        avg_score = min(1.0, avg_ofc / avg_target)
    else:
        avg_score = 0.0
    
    evaluation["scores"]["average_ofc_per_vulnerability"] = avg_score
    
    # Calculate overall score (mean of all scores)
    scores = list(evaluation["scores"].values())
    evaluation["overall_score"] = sum(scores) / len(scores) if scores else 0.0
    
    # Pass/fail (overall score >= 0.85)
    evaluation["passed"] = evaluation["overall_score"] >= 0.85
    
    # Add warnings
    warnings = []
    if metrics["vulnerabilities"] < 200:
        warnings.append("Under-extraction: vulnerabilities < 200")
    if metrics["ofcs"] < 500:
        warnings.append("Under-extraction: OFCs < 500")
    if dedup_score < 0.7:
        warnings.append("Over-repeating: deduplication ratio < 0.7")
    if coverage_score < 0.7:
        warnings.append(f"Domain gap: missing {len(expected_domains) - metrics['domains_count']} expected domains")
    
    evaluation["warnings"] = warnings
    
    return evaluation


def print_benchmark_report(evaluation: Dict[str, Any], benchmark_path: Optional[Path] = None):
    """
    Print a human-readable benchmark evaluation report.
    
    Args:
        evaluation: Evaluation dictionary from evaluate_against_benchmark
        benchmark_path: Path to benchmark file (for metadata)
    """
    if "error" in evaluation:
        print(f"ERROR: {evaluation['error']}")
        return
    
    benchmark = load_benchmark(benchmark_path)
    metadata = benchmark.get("metadata", {})
    
    print("=" * 70)
    print("VOFC ENGINE BENCHMARK EVALUATION")
    print("=" * 70)
    print(f"Document: {metadata.get('document', 'Unknown')}")
    print(f"Model: {metadata.get('expected_model', 'Unknown')}")
    print()
    
    metrics = evaluation.get("metrics", {})
    scores = evaluation.get("scores", {})
    
    print("EXTRACTION METRICS:")
    print(f"  Vulnerabilities: {metrics.get('vulnerabilities', 0)}")
    print(f"  Unique Vulnerabilities: {metrics.get('unique_vulnerabilities_count', 0)}")
    print(f"  OFCs: {metrics.get('ofcs', 0)}")
    print(f"  Domains Found: {metrics.get('domains_count', 0)}")
    print(f"  Total Records: {metrics.get('total_records', 0)}")
    print()
    
    print("BENCHMARK SCORES:")
    for score_name, score_value in scores.items():
        status = "PASS" if score_value >= 0.85 else "FAIL"
        print(f"  {score_name.replace('_', ' ').title()}: {score_value:.3f} [{status}]")
    print()
    
    overall = evaluation.get("overall_score", 0.0)
    passed = evaluation.get("passed", False)
    status = "PASSED" if passed else "FAILED"
    
    print(f"OVERALL SCORE: {overall:.3f} [{status}]")
    print()
    
    warnings = evaluation.get("warnings", [])
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    print("=" * 70)


if __name__ == "__main__":
    """
    CLI interface for benchmark evaluation.
    Usage: python services/benchmark_evaluator.py <result_json_file>
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python services/benchmark_evaluator.py <result_json_file>")
        print("Example: python services/benchmark_evaluator.py C:\\Tools\\Ollama\\Data\\review\\temp\\document_phase2_engine.json")
        sys.exit(1)
    
    result_file = Path(sys.argv[1])
    if not result_file.exists():
        print(f"ERROR: File not found: {result_file}")
        sys.exit(1)
    
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load result file: {e}")
        sys.exit(1)
    
    evaluation = evaluate_against_benchmark(result)
    print_benchmark_report(evaluation)

