# AI Enhancement Quick Start Guide

## Overview

The VOFC Engine now supports AI-driven intelligent processing that replaces rule-based logic with semantic understanding. All AI features have automatic fallback to rules for reliability.

## Quick Enable

### 1. Add to `.env` file:

```bash
# Enable AI Enhancement
ENABLE_AI_ENHANCEMENT=true

# Optional: Use different model for enhancement (defaults to VOFC_MODEL)
AI_ENHANCEMENT_MODEL=vofc-engine:v3
```

### 2. Restart Services:

```powershell
# Restart as Administrator
nssm restart "VOFC-Ollama"
nssm restart "VOFC-Flask"
```

## What Gets Enhanced

### ✅ Domain Classification
**Before (Rules)**: "bollard" → "Perimeter" (keyword match)  
**After (AI)**: "vehicle barrier system" → "Perimeter Security" (semantic understanding)

### ✅ Implied Vulnerability Generation
**Before (Rules)**: Generic "(Implied: Missing or inadequate perimeter security)"  
**After (AI)**: Context-specific "(Implied: Inadequate vehicle access control at entry points)"

### ✅ Validation
**Before (Rules)**: Word overlap check (20-30% threshold)  
**After (AI)**: Semantic validation with evidence quotes

### ✅ Quality Assessment
**Before (Rules)**: Fixed confidence threshold (0.4)  
**After (AI)**: Dynamic quality scoring based on content analysis

### ✅ Deduplication
**Before (Rules)**: Text similarity (80% threshold)  
**After (AI)**: Semantic equivalence detection with merge suggestions

## How It Works

1. **AI First**: If `ENABLE_AI_ENHANCEMENT=true`, system tries AI functions
2. **Fallback**: If AI fails or unavailable, automatically uses rule-based logic
3. **Logging**: All AI decisions are logged with reasoning
4. **No Breaking Changes**: System works the same way, just smarter

## Monitoring

### Check AI Usage in Logs:

```powershell
# View AI decisions
Get-Content "C:\Tools\VOFC_Logs\vofc_engine.log" | Select-String "AI assigned" | Select-Object -Last 20

# View AI validation results
Get-Content "C:\Tools\VOFC_Logs\vofc_engine.log" | Select-String "AI validation" | Select-Object -Last 20

# View AI quality assessments
Get-Content "C:\Tools\VOFC_Logs\vofc_engine.log" | Select-String "AI quality" | Select-Object -Last 20
```

### Expected Log Messages:

```
[DEBUG] AI assigned domain 'Perimeter Security' (confidence: 0.85)
[DEBUG] AI generated implied vulnerability '...' (confidence: 0.72)
[DEBUG] AI validation passed - evidence: "..."
[DEBUG] AI quality score: 0.88, confidence: 0.82
[DEBUG] AI merge decision: should_merge=True, confidence: 0.91
```

## Performance Considerations

### Response Times
- **AI Classification**: ~1-2 seconds per record
- **AI Validation**: ~1-2 seconds per record
- **AI Quality Assessment**: ~1-2 seconds per record
- **Total Overhead**: ~3-6 seconds per record (when AI enabled)

### Optimization Tips

1. **Batch Processing**: AI functions are called per-record, but can be optimized
2. **Caching**: Consider caching AI results for identical inputs (future enhancement)
3. **Selective Enable**: Enable only specific AI features if needed:
   - `AI_VALIDATION_ENABLED=true` (validation only)
   - `AI_CLASSIFICATION_ENABLED=true` (classification only)

## Troubleshooting

### AI Not Working?

1. **Check Environment Variable**:
   ```powershell
   $env:ENABLE_AI_ENHANCEMENT
   # Should output: true
   ```

2. **Check Model Availability**:
   ```powershell
   ollama list
   # Should show: vofc-engine:v3
   ```

3. **Check Logs for Errors**:
   ```powershell
   Get-Content "C:\Tools\VOFC_Logs\vofc_engine.log" | Select-String "AI.*failed" | Select-Object -Last 10
   ```

4. **Verify Fallback Working**:
   - If AI fails, system should automatically use rules
   - Check logs for "falling back to" messages

### Common Issues

**Issue**: "AI enhancement failed, using keywords"  
**Solution**: AI unavailable or model not responding. System will use rules automatically.

**Issue**: Slow processing  
**Solution**: AI adds ~3-6 seconds per record. Consider disabling for high-volume processing.

**Issue**: AI returning invalid responses  
**Solution**: Check model version. Try updating to latest `vofc-engine:v3`.

## Disabling AI Enhancement

To disable and return to rule-based only:

```bash
# In .env file
ENABLE_AI_ENHANCEMENT=false
```

Then restart services.

## Expected Improvements

| Metric | Before (Rules) | After (AI) | Improvement |
|--------|----------------|------------|-------------|
| Domain Accuracy | 70% | 90%+ | +20% |
| False Positives | 15% | 5% | -10% |
| Validation Accuracy | 80% | 95%+ | +15% |
| Implied Vuln Quality | Low (generic) | High (specific) | Significant |
| Deduplication Precision | 75% | 90%+ | +15% |

## Next Steps

1. **Enable AI Enhancement**: Add `ENABLE_AI_ENHANCEMENT=true` to `.env`
2. **Restart Services**: Apply changes
3. **Test with Sample Document**: Process a document and check logs
4. **Monitor Performance**: Watch for AI decisions and fallbacks
5. **Compare Results**: Review extracted data quality improvements

## Advanced Configuration

See `docs/AI_ENHANCEMENT_STRATEGY.md` for:
- Detailed implementation guide
- Performance optimization
- Caching strategies
- Batch processing
- Multi-model ensemble

