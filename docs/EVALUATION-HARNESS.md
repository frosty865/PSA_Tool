# Evaluation Harness Documentation

## Overview

The `evaluate_pipeline.py` script provides a comprehensive evaluation harness for the VOFC document processing pipeline. It runs documents through the complete pipeline (preprocessing → model inference → post-processing → Supabase) and collects detailed metrics for performance analysis and quality assessment.

## Features

- **Full Pipeline Evaluation**: Tests the complete document processing workflow
- **Performance Metrics**: Tracks timing for each stage (extraction, model inference, post-processing)
- **Quality Metrics**: Measures chunk counts, deduplication rates, taxonomy resolution
- **Batch Processing**: Evaluates multiple documents in a single run
- **Reference Comparison**: Optional accuracy benchmarking against gold-standard data
- **Comprehensive Reporting**: Generates JSON, CSV, and console reports

## Installation

The evaluation harness uses the same dependencies as the main pipeline:

```bash
pip install pandas  # Optional but recommended for CSV reports and tables
```

All other dependencies (`preprocess`, `ollama_client`, `postprocess`, `supabase_client`) are already part of the VOFC-Processor service.

## Usage

### Basic Evaluation (Dry Run)

Run evaluation without saving to Supabase:

```bash
python evaluate_pipeline.py
```

### Save Results to Supabase

Include the `--save` flag to insert results into Supabase:

```bash
python evaluate_pipeline.py --save
```

### Use Custom Model

Specify a different Ollama model:

```bash
python evaluate_pipeline.py --model psa-engine:v2
```

### Compare with Reference Data

Evaluate accuracy against gold-standard annotations:

```bash
python evaluate_pipeline.py --reference gold_standard.json
```

### Custom Evaluation Directory

Specify a different directory containing test documents:

```bash
python evaluate_pipeline.py --eval-dir C:\Path\To\Test\Documents
```

## Directory Structure

The evaluation harness expects the following directory structure:

```
C:\Tools\VOFC-Processor\
├── eval_docs\          # Place test documents here (PDF, DOCX, TXT)
├── eval_reports\       # Generated reports saved here
│   ├── evaluation_report_YYYYMMDD_HHMMSS.json
│   ├── evaluation_report_YYYYMMDD_HHMMSS.csv
│   └── evaluation.log
└── evaluate_pipeline.py
```

If `C:\Tools\VOFC-Processor\` doesn't exist, the script will fall back to using `data/eval_docs` and `data/eval_reports` in the project root.

## Metrics Collected

### Per-Document Metrics

- **File Information**:
  - `file`: Filename
  - `file_size_kb`: File size in kilobytes
  - `status`: Processing status (`success` or `error`)

- **Preprocessing Metrics**:
  - `chunks`: Number of text chunks created
  - `total_chars`: Total characters extracted
  - `avg_chunk_size`: Average chunk size in characters
  - `extraction_time`: Time spent in preprocessing (seconds)

- **Model Inference Metrics**:
  - `raw_records`: Number of raw model outputs
  - `successful_chunks`: Chunks processed successfully
  - `failed_chunks`: Chunks that failed processing
  - `model_time`: Time spent in model inference (seconds)
  - `avg_time_per_chunk`: Average processing time per chunk

- **Post-Processing Metrics**:
  - `unique_records`: Number of unique records after deduplication
  - `deduplication_rate`: Percentage of records removed as duplicates
  - `with_discipline`: Records with resolved discipline ID
  - `with_sector`: Records with resolved sector ID
  - `with_subsector`: Records with resolved subsector ID
  - `postprocess_time`: Time spent in post-processing (seconds)

- **Supabase Metrics** (if `--save` used):
  - `supabase_saved`: Number of records saved
  - `supabase_errors`: Number of save errors
  - `save_time`: Time spent saving to Supabase (seconds)

- **Overall Metrics**:
  - `total_time`: Total pipeline time (seconds)
  - `throughput_chunks_per_sec`: Processing throughput

- **Accuracy Metrics** (if reference data provided):
  - `accuracy_precision`: Precision score
  - `accuracy_recall`: Recall score
  - `accuracy_f1`: F1 score

## Reference Data Format

To compare results against gold-standard annotations, provide a JSON file with the following structure:

```json
{
  "document1.pdf": {
    "vulnerabilities": [
      "Insecure Password Storage",
      "Weak Access Control"
    ],
    "ofcs": [
      "Implement hashing",
      "Use strong passwords",
      "Implement RBAC"
    ]
  },
  "document2.pdf": {
    "vulnerabilities": ["SQL Injection"],
    "ofcs": ["Use parameterized queries"]
  }
}
```

Alternatively, provide a CSV file with columns:
- `filename`: Document filename
- `vulnerability`: Vulnerability description
- `ofc`: Option for consideration

## Output Reports

### JSON Report

Comprehensive JSON report with all metrics and metadata:

```json
{
  "timestamp": "2025-01-15T10:30:00",
  "total_documents": 5,
  "model": "psa-engine:latest",
  "save_to_supabase": false,
  "metrics": [
    {
      "file": "sample.pdf",
      "chunks": 12,
      "unique_records": 8,
      "total_time": 45.23,
      ...
    }
  ]
}
```

### CSV Report

Tabular format suitable for spreadsheet analysis. Includes all metrics as columns.

### Console Output

Real-time progress updates and summary table:

```
================================================================================
Evaluating 5 documents
================================================================================

[1/5] Processing: sample1.pdf
  ✓ Completed: 8 records, 45.23s
[2/5] Processing: sample2.pdf
  ✓ Completed: 12 records, 52.10s
...

================================================================================
EVALUATION SUMMARY
================================================================================

file          chunks  unique_records  total_time  status
sample1.pdf    12      8               45.23       success
sample2.pdf    15      12              52.10       success
...

================================================================================
STATISTICS
================================================================================

Documents processed: 5/5
Average total time: 48.67 sec/document
Average chunks: 13.4
Average records: 10.0
Total records: 50

Reports saved to: C:\Tools\VOFC-Processor\eval_reports
  - JSON: evaluation_report_20250115_103000.json
  - CSV: evaluation_report_20250115_103000.csv
  - Log: evaluation.log
```

## Logging

All evaluation runs are logged to `eval_reports/evaluation.log` with timestamps, including:
- Document processing start/completion
- Errors and exceptions
- Metric values
- Summary statistics

## Integration with CI/CD

The evaluation harness can be integrated into automated testing pipelines:

```bash
# Run evaluation and check for errors
python evaluate_pipeline.py --eval-dir test_documents
if [ $? -ne 0 ]; then
    echo "Evaluation failed"
    exit 1
fi
```

## Best Practices

1. **Test Documents**: Use a diverse set of test documents covering different:
   - File formats (PDF, DOCX, TXT)
   - Document sizes (small, medium, large)
   - Content types (technical reports, assessments, guidelines)

2. **Baseline Metrics**: Establish baseline metrics for your documents to detect regressions

3. **Regular Evaluation**: Run evaluations after:
   - Model updates
   - Preprocessing changes
   - Post-processing improvements
   - Taxonomy updates

4. **Reference Data**: Maintain gold-standard annotations for critical documents to track accuracy over time

5. **Performance Monitoring**: Track timing metrics to identify performance bottlenecks

## Troubleshooting

### No Documents Found

**Error**: `No documents found in <directory>`

**Solution**: Ensure test documents are placed in `eval_docs/` directory with supported extensions (.pdf, .docx, .txt)

### Model Connection Errors

**Error**: `Ollama model execution failed`

**Solution**: 
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check model name is correct: `ollama list`
- Ensure model is available: `ollama pull psa-engine:latest`

### Supabase Save Errors

**Error**: `Failed to save to Supabase`

**Solution**:
- Verify Supabase credentials in environment variables
- Check network connectivity
- Review Supabase logs for detailed error messages

### Missing Dependencies

**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**: Install optional dependencies:
```bash
pip install pandas
```

Note: Pandas is optional - the script will work without it but won't generate CSV reports or formatted tables.

## Example Workflow

1. **Prepare Test Documents**:
   ```bash
   # Copy test documents to eval directory
   cp test_docs/*.pdf C:\Tools\VOFC-Processor\eval_docs\
   ```

2. **Run Evaluation**:
   ```bash
   cd C:\Tools\VOFC-Processor
   python evaluate_pipeline.py
   ```

3. **Review Results**:
   - Check console output for summary
   - Open CSV report in Excel for detailed analysis
   - Review JSON report for programmatic analysis

4. **Compare with Previous Run**:
   ```bash
   # Run with reference data
   python evaluate_pipeline.py --reference previous_results.json
   ```

5. **Save to Supabase** (if results look good):
   ```bash
   python evaluate_pipeline.py --save
   ```

## API Reference

### `evaluate_document(path, save=False, model="psa-engine:latest")`

Evaluate a single document through the pipeline.

**Parameters**:
- `path`: Path to document file
- `save`: Whether to save results to Supabase
- `model`: Ollama model name

**Returns**: Dictionary with metrics

### `run_batch(eval_dir=None, save=False, model="psa-engine:latest", reference_file=None)`

Run batch evaluation on all documents in a directory.

**Parameters**:
- `eval_dir`: Directory containing documents (default: `EVAL_DIR`)
- `save`: Whether to save results to Supabase
- `model`: Ollama model name
- `reference_file`: Path to reference data file

**Returns**: DataFrame (if pandas available) or list of metrics

### `compare_with_reference(preds, refs)`

Compare predictions with reference data.

**Parameters**:
- `preds`: List of predicted strings
- `refs`: List of reference strings

**Returns**: Dictionary with precision, recall, F1, and counts

### `load_reference_data(reference_file)`

Load reference data from JSON or CSV file.

**Parameters**:
- `reference_file`: Path to reference data file

**Returns**: Dictionary mapping filename to reference data

