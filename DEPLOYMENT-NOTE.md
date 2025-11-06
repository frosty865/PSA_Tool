# Preprocessing Module Deployment

## File Location

The `preprocess.py` module has been created in the project at:
- **Project Location:** `services/preprocess.py`

## Deployment to VOFC-Processor Service

To deploy to the VOFC-Processor service directory:

1. **Copy the file:**
   ```powershell
   Copy-Item "services\preprocess.py" "C:\Tools\VOFC-Processor\preprocess.py"
   ```

2. **Install dependencies:**
   ```powershell
   pip install PyMuPDF nltk python-docx
   ```
   
   Or install from requirements.txt:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Create logs directory:**
   ```powershell
   New-Item -ItemType Directory -Path "C:\Tools\VOFC-Processor\logs" -Force
   ```

4. **Test the module:**
   ```powershell
   python C:\Tools\VOFC-Processor\preprocess.py "C:\Tools\VOFC-Processor\incoming\sample.pdf"
   ```

## Integration with process_worker.py

If you have a `process_worker.py` in `C:\Tools\VOFC-Processor\`, update it to use the preprocessing module:

```python
from preprocess import preprocess_document

def process_file(file_path):
    """Process a file using preprocessing and model pipeline"""
    try:
        # Preprocess document into chunks
        chunks = preprocess_document(file_path)
        
        # Process each chunk with model
        results = []
        for chunk in chunks:
            result = run_model_on_chunk(chunk)
            results.append({
                'chunk_id': chunk['chunk_id'],
                'result': result
            })
        
        # Save results
        save_results(file_path, results)
        
        return results
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
```

## Verification

After deployment, verify the module works:

```powershell
# Test CLI
python C:\Tools\VOFC-Processor\preprocess.py "C:\Tools\VOFC-Processor\incoming\test.pdf"

# Check logs
Get-Content C:\Tools\VOFC-Processor\logs\preprocess.log -Tail 20
```

---

*Note: The module is designed to work standalone or as part of the processing pipeline.*

