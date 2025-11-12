# Zero Results Fix

## Problem

Documents processed but produced zero or minimal results (hallucinations like "Apache Log4j", "CVE-2022-1234").

## Root Causes

1. **Prompt Mismatch**: The prompt didn't match the model's training format
2. **Hallucination Prevention**: Model was inventing cyber vulnerabilities instead of extracting physical security issues
3. **JSON Parsing**: Response parsing wasn't handling the model's output format correctly

## Fixes Applied

### 1. Updated Prompt (`vofc_processor.py`)

**Before:**
```
Extract vulnerabilities and options for consideration from the document above.
Use the reference library to align with existing canonical records where applicable.
Return valid JSON array format with vulnerability and OFC records.
```

**After:**
```
You are VOFC-ENGINE, a physical security extraction analyst.
Only produce findings related to PHYSICAL security for facilities...

NEVER produce cyber/CVE/patch/exploit content. NEVER invent vulnerabilities that don't exist in the document.

Rules:
- If text describes a problem/gap/deficiency → output type="vulnerability" with "vulnerability" field
- If text describes a mitigation/action/recommendation → output type="ofc" with "ofc" field
- Extract diverse, specific vulnerabilities (design process, site-specific issues, operational gaps)
- Do NOT repeat the same vulnerability multiple times
- Do NOT invent cyber issues, CVEs, patches, exploits, software libraries
```

### 2. Improved JSON Parsing

- Handles both array and single object responses
- Normalizes format: `{"type":"vulnerability","vulnerability":"..."}` → standard format
- Filters out hallucinations (Apache, CVE-, Log4j, placeholder, dummy, test, example)
- Validates records have actual content

### 3. Record Validation

```python
# Filter out empty or placeholder records (including cyber hallucinations)
data = [r for r in data if (r.get("vulnerability") or r.get("ofc")) and 
        not r.get("vulnerability", "").lower().startswith(("apache", "cve-", "log4j", "placeholder", "dummy", "test", "example"))]
```

## Testing

1. **Restart VOFC-Processor service:**
   ```powershell
   nssm restart VOFC-Processor
   ```

2. **Process a test document:**
   - Place PDF in `C:\Tools\Ollama\Data\incoming\`
   - Wait for processing
   - Check `C:\Tools\Ollama\Data\processed\` for results

3. **Verify results:**
   - Should have multiple physical security vulnerabilities/OFCs
   - No cyber/CVE content
   - No hallucinations
   - Records should be specific to the document content

## Expected Output Format

```json
[
  {
    "type": "vulnerability",
    "vulnerability": "Lack of perimeter fencing",
    "ofc": ""
  },
  {
    "type": "ofc",
    "vulnerability": "",
    "ofc": "Install access control system at main entrance"
  }
]
```

## Troubleshooting

### Still Getting Zero Results

1. **Check model is running:**
   ```powershell
   curl http://localhost:11434/api/tags
   ```

2. **Check processor logs:**
   ```powershell
   Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -Tail 50
   ```

3. **Verify document has physical security content:**
   - Model only extracts physical security issues
   - Cyber/IT documents will return empty results

4. **Check for JSON parsing errors:**
   - Look for `*_error.txt` files in `processed/` directory
   - These show the raw model response if JSON parsing failed

### Getting Hallucinations

1. **Verify model version:**
   ```powershell
   ollama list
   ```
   Should show `vofc-engine:latest`

2. **Check prompt is being used:**
   - Review logs for prompt being sent
   - Verify model Modelfile matches expected format

3. **Filter is working:**
   - Hallucinations should be filtered out automatically
   - If still appearing, check filter patterns in `save_output()`

## Next Steps

- Monitor processing results
- Adjust prompt if needed based on document types
- Add more filter patterns if new hallucinations appear
- Consider retraining model if extraction quality is poor

