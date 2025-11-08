# Learning Event (VOFC Feedback Loop) - Implementation Summary

## Overview

This implementation adds a complete Learning Event feedback loop system that enables continuous improvement of the VOFC extraction engine through logged corrections and runtime configuration.

## What Was Implemented

### 1. Learning Feedback Service (`services/learning_feedback.py`)

**New Functions:**
- `log_post_audit_enrichment()` - Logs correction/enrichment events to `learning_events` table
- `get_enrichment_themes()` - Retrieves themes from past corrections for a document
- `get_enrichment_examples()` - Retrieves example patterns from past corrections

**Usage:**
```python
from services.learning_feedback import log_post_audit_enrichment

log_post_audit_enrichment(
    model_id="vofc-engine:latest",
    source_file="USSS Averting Targeted School Violence.2021.03.pdf",
    detected_vulnerabilities=1,
    expected_vulnerabilities=10,
    expected_ofcs=30,
    correction_payload={
        "themes": ["threat assessment", "leakage", ...],
        "examples": [...]
    }
)
```

### 2. Enhanced Ollama Client (`services/ollama_client.py`)

**New Features:**
- Configuration loading from YAML file (`config/vofc_config.yaml`)
- Document-specific prompt biases
- Enrichment context from learning events
- Enhanced prompt building with all enhancements

**New Functions:**
- `load_engine_config()` - Loads configuration from YAML
- `get_document_bias()` - Gets document-specific prompts
- `get_enrichment_context()` - Gets enrichment context from learning events
- `build_enhanced_prompt()` - Builds enhanced prompt

**Updated Functions:**
- `run_model()` - Now accepts `file_path` parameter for prompt enhancement
- `run_model_on_chunks()` - Now accepts `file_path` parameter

### 3. Configuration File (`config/vofc_config.yaml`)

**Configuration Options:**
- `VOFC_ENGINE_TOPICS` - Target extraction counts, narrative risk, thematic expansion
- `document_biases` - Document-specific prompt enhancements
- `themes` - Global themes to emphasize
- `training` - Training parameters

### 4. Training Data Structure

**Created:**
- `training_data/` directory
- `training_data/README.md` - Schema documentation
- `training_data/usss_averting_2021.json.example` - Example training file

### 5. Retraining Script (`scripts/retrain-vofc-engine.py`)

**Features:**
- Validates training files
- Creates Ollama training configuration
- Provides instructions for model fine-tuning

### 6. Example Scripts

**Created:**
- `scripts/log-learning-event-example.py` - Example of logging a learning event

### 7. Documentation

**Created:**
- `docs/LEARNING-FEEDBACK-LOOP.md` - Complete usage guide
- `docs/LEARNING-FEEDBACK-IMPLEMENTATION.md` - This file

### 8. Integration Updates

**Updated:**
- `ollama_auto_processor.py` - All `run_model()` calls now pass `file_path` parameter
  - `phase1_parser()` - Updated
  - `phase2_engine()` - Updated
  - `phase3_auditor()` - Updated
  - Fallback prompt call - Updated

## How It Works

1. **Analyst Corrects Output**: When an analyst identifies missing vulnerabilities or OFCs, they log a learning event.

2. **Learning Event Logged**: The correction is stored in `learning_events` table with:
   - Themes that should be emphasized
   - Example vulnerability-OFC pairs
   - Detection ratios (detected vs expected)

3. **Configuration Applied**: Next time a similar document is processed:
   - Document-specific biases are applied (from config file)
   - Enrichment themes are retrieved from past corrections
   - Example patterns are included in the prompt
   - Global configuration settings are applied

4. **Enhanced Prompts**: The model receives enhanced prompts that guide it to:
   - Focus on previously missed themes
   - Look for patterns similar to past corrections
   - Extract target number of vulnerabilities and OFCs

5. **Improved Extraction**: The model extracts more accurately based on the feedback.

## Configuration File Location

**Default:** `C:/Tools/Ollama/vofc_config.yaml`

**Override:** Set `VOFC_ENGINE_CONFIG` environment variable

## Next Steps

1. **Log Learning Events**: Use `scripts/log-learning-event-example.py` or call `log_post_audit_enrichment()` directly

2. **Configure Document Biases**: Edit `config/vofc_config.yaml` to add document-specific prompts

3. **Collect Training Data**: Add JSON files to `training_data/` directory following the schema

4. **Retrain Model** (Optional): Use `scripts/retrain-vofc-engine.py` to fine-tune the model

## Files Modified

- `services/ollama_client.py` - Added configuration and prompt enhancement
- `ollama_auto_processor.py` - Updated to pass `file_path` to `run_model()`

## Files Created

- `services/learning_feedback.py` - Learning feedback service
- `config/vofc_config.yaml` - Configuration file
- `training_data/README.md` - Training data documentation
- `training_data/usss_averting_2021.json.example` - Example training file
- `scripts/log-learning-event-example.py` - Example script
- `scripts/retrain-vofc-engine.py` - Retraining script
- `docs/LEARNING-FEEDBACK-LOOP.md` - Usage guide
- `docs/LEARNING-FEEDBACK-IMPLEMENTATION.md` - This file

## Testing

1. **Test Learning Event Logging:**
   ```bash
   python scripts/log-learning-event-example.py
   ```

2. **Test Configuration Loading:**
   - Ensure `config/vofc_config.yaml` exists
   - Process a document and check logs for "Loaded engine config"

3. **Test Prompt Enhancement:**
   - Process a document matching a pattern in `document_biases`
   - Check logs for enhanced prompts

## Dependencies

- `pyyaml` - For YAML configuration loading
- `supabase-py` - For learning events database access (already installed)

## Notes

- The system gracefully falls back to defaults if configuration file is missing
- Enrichment context is optional and won't break processing if unavailable
- Document biases are matched case-insensitively against filenames
- All enhancements are additive - they don't replace the base prompt

