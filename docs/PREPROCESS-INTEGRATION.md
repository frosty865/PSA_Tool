# Document Preprocessing Integration

## Overview

The document preprocessing module has been integrated into the Flask `/api/process` endpoint, enabling end-to-end document processing: upload → preprocess → model inference → Supabase storage.

## API Endpoint

### `POST /api/process`

Process uploaded documents with full preprocessing pipeline.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Field: `file` (PDF, DOCX, or TXT file)

**Example using curl:**
```bash
curl -X POST http://localhost:8080/api/process \
  -F "file=@document.pdf"
```

**Example using JavaScript (fetch):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8080/api/process', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "File processed successfully",
  "file": "document.pdf",
  "chunks": 15,
  "results": 15,
  "supabase": {
    "saved": 12,
    "errors": 0,
    "total": 15
  },
  "status": "ok",
  "service": "PSA Processing Server"
}
```

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Error message",
  "step": "preprocessing|model_inference|supabase_save",
  "service": "PSA Processing Server"
}
```

## Processing Pipeline

### Step 1: File Upload
- File is received via multipart/form-data
- Filename is sanitized to prevent path traversal
- File is saved to `C:\Tools\Ollama\Data\incoming\`

### Step 2: Preprocessing
- Text extraction from PDF/DOCX/TXT
- Text normalization (remove headers, fix hyphenation, clean whitespace)
- Sentence-aware chunking (~4000 chars per chunk, ~800-1200 tokens)
- Creates structured chunk data with metadata

### Step 3: Model Inference
- Each chunk is processed by Ollama model (`psa-engine:latest`)
- Model analyzes chunk for:
  - Security vulnerabilities
  - Options for Consideration (OFCs)
  - Relevant disciplines and sectors
  - Key recommendations
- Results are parsed and structured

### Step 4: Supabase Storage
- Results are saved to `submissions` table
- Each record includes:
  - Vulnerabilities array
  - OFCs array
  - Chunk metadata (chunk_id, source_file, page_range)
  - Model response
  - Processing timestamp
- Status set to `pending` for admin review

## New Functions

### `run_model_on_chunks(chunks, model="psa-engine:latest")`
**Location:** `services/ollama_client.py`

Processes a list of document chunks through the Ollama model.

**Parameters:**
- `chunks`: List of chunk dictionaries with `content` field
- `model`: Ollama model name (default: "psa-engine:latest")

**Returns:**
- List of result dictionaries, one per chunk

**Features:**
- Handles JSON parsing from model responses
- Includes chunk metadata in results
- Continues processing even if individual chunks fail
- Logs errors for failed chunks

### `save_results(results, source_file=None)`
**Location:** `services/supabase_client.py`

Saves processing results to Supabase submissions table.

**Parameters:**
- `results`: List of result dictionaries from model processing
- `source_file`: Original source filename (optional)

**Returns:**
- Dictionary with save statistics: `{"saved": N, "errors": M, "total": T}`

**Features:**
- Batch inserts to Supabase
- Filters out failed chunks
- Only saves records with vulnerabilities or OFCs
- Handles errors gracefully

## Logging

All processing steps are logged:

```
INFO - Received file upload: document.pdf
INFO - File saved to: C:\Tools\Ollama\Data\incoming\document.pdf
INFO - Starting preprocessing for document.pdf
INFO - Preprocessing complete: 15 chunks created
INFO - Running model inference on 15 chunks
INFO - Model inference complete: 15 results
INFO - Saving 15 results to Supabase
INFO - Supabase save complete: {'saved': 12, 'errors': 0, 'total': 15}
```

## Error Handling

The endpoint includes comprehensive error handling:

1. **File Upload Errors:**
   - No file provided → 400
   - Empty filename → 400

2. **Preprocessing Errors:**
   - Unsupported file type → 500 with step="preprocessing"
   - Empty document → 400
   - Extraction failure → 500 with step="preprocessing"

3. **Model Inference Errors:**
   - Ollama connection failure → 500 with step="model_inference"
   - Individual chunk failures → logged, processing continues

4. **Supabase Errors:**
   - Connection failure → logged, but doesn't fail request
   - Insert errors → logged, returns error count in response

## File Locations

- **Upload Directory:** `C:\Tools\Ollama\Data\incoming\`
- **Preprocessing Logs:** `logs/preprocess.log`
- **Flask Logs:** Console output (INFO level)

## Integration with Existing Endpoints

The new `/api/process` endpoint works alongside existing endpoints:

- `/api/process/start` - Process file by filename (existing)
- `/api/process/document` - Process document by path (existing)
- `/api/process/submit` - Queue file for processing (existing)
- `/api/process` - **NEW** - Upload and process file with preprocessing

## Testing

### Test with curl:
```bash
# Test PDF upload
curl -X POST http://localhost:8080/api/process \
  -F "file=@test.pdf"

# Test DOCX upload
curl -X POST http://localhost:8080/api/process \
  -F "file=@test.docx"

# Test TXT upload
curl -X POST http://localhost:8080/api/process \
  -F "file=@test.txt"
```

### Test with Python:
```python
import requests

url = "http://localhost:8080/api/process"
files = {'file': open('document.pdf', 'rb')}

response = requests.post(url, files=files)
print(response.json())
```

## Configuration

### Environment Variables

- `SUBMITTER_EMAIL` - Email address for submission records (optional)
- `OLLAMA_HOST` - Ollama server URL (default: http://127.0.0.1:11434)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key

### Model Configuration

Default model: `psa-engine:latest`

To use a different model, modify the `run_model_on_chunks` call in `routes/process.py`:

```python
results = run_model_on_chunks(chunks, model="your-model:latest")
```

## Performance Considerations

- **Chunking:** Large documents are split into manageable chunks (~4000 chars each)
- **Parallel Processing:** Currently sequential; can be parallelized for better performance
- **Timeout:** Model inference has 300s timeout per chunk
- **Batch Inserts:** Supabase saves are batched for efficiency

## Future Enhancements

- Parallel chunk processing for faster inference
- Progress tracking via WebSocket or polling
- Chunk result caching to avoid reprocessing
- Support for additional file formats
- Configurable chunk size via request parameter

---

*Last Updated: 2025-11-06*

