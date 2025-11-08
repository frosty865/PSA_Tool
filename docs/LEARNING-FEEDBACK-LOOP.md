# Learning Event (VOFC Feedback Loop)

## Overview

The Learning Event system enables continuous improvement of the VOFC (Vulnerability and Options for Consideration) extraction engine by logging corrections and enrichment events. These events inform future model behavior through runtime configuration and can be used for model fine-tuning.

## Architecture

```
Analyst Correction → Learning Event Logged → Configuration Updated → Model Behavior Improved
                                                      ↓
                                            Runtime Prompt Enhancement
```

## Components

### 1. Learning Feedback Service (`services/learning_feedback.py`)

Logs post-audit enrichment events to the `learning_events` table.

**Key Functions:**
- `log_post_audit_enrichment()` - Logs a correction/enrichment event
- `get_enrichment_themes()` - Retrieves themes from past corrections
- `get_enrichment_examples()` - Retrieves example patterns from past corrections

### 2. Enhanced Ollama Client (`services/ollama_client.py`)

Supports runtime configuration and prompt enhancement based on:
- Document-specific biases (from config file)
- Past enrichment events (from learning_events table)
- Global configuration settings

**Key Functions:**
- `load_engine_config()` - Loads configuration from YAML file
- `get_document_bias()` - Gets document-specific prompt enhancements
- `get_enrichment_context()` - Gets enrichment context from learning events
- `build_enhanced_prompt()` - Builds enhanced prompt with all enhancements

### 3. Configuration File (`config/vofc_config.yaml`)

YAML configuration file that controls:
- Target extraction counts (vulnerabilities per doc, OFCs per vulnerability)
- Document-specific prompt biases
- Global themes to emphasize
- Training parameters

## Usage

### Step 1: Log a Learning Event

When an analyst corrects or enriches model output, log it as a learning event:

```python
from services.learning_feedback import log_post_audit_enrichment

log_post_audit_enrichment(
    model_id="vofc-engine:latest",
    source_file="USSS Averting Targeted School Violence.2021.03.pdf",
    detected_vulnerabilities=1,
    expected_vulnerabilities=10,
    expected_ofcs=30,
    correction_payload={
        "themes": [
            "threat assessment",
            "leakage",
            "discipline follow-up",
            "information sharing",
            "mental health",
            "social media",
            "weapon access",
            "school climate"
        ],
        "examples": [
            {
                "vulnerability": "No formal threat-assessment program",
                "ofcs": [
                    "Establish and train multidisciplinary behavioral threat assessment teams",
                    "Adopt and implement standard operating procedures following REMS/USSS guidelines"
                ]
            }
        ]
    }
)
```

**Or use the example script:**
```bash
python scripts/log-learning-event-example.py
```

### Step 2: Configuration is Automatically Applied

The next time a document with similar content is processed:

1. **Document Bias Detection**: If the filename matches patterns in `vofc_config.yaml`, document-specific prompts are added.

2. **Enrichment Context**: Themes and examples from past corrections for the same document are retrieved and added to the prompt.

3. **Global Configuration**: Settings from `VOFC_ENGINE_TOPICS` are applied (target counts, narrative risk focus, etc.).

### Step 3: Model Behavior Improves

The enhanced prompts guide the model to:
- Focus on themes that were previously missed
- Look for patterns similar to past corrections
- Extract the target number of vulnerabilities and OFCs

## Configuration

### Configuration File Location

Default: `C:/Tools/Ollama/vofc_config.yaml`

Override with environment variable:
```bash
set VOFC_ENGINE_CONFIG=C:/Custom/Path/vofc_config.yaml
```

### Configuration Structure

```yaml
VOFC_ENGINE_TOPICS:
  narrative_risk: true              # Enable narrative risk detection
  thematic_expansion: true          # Enable thematic expansion
  target_vulnerabilities_per_doc: 10 # Target vulnerabilities per document
  target_ofcs_per_vulnerability: 3   # Target OFCs per vulnerability

document_biases:
  "USSS":
    prompts:
      - "Focus on systemic and behavioral vulnerabilities, not IT or cyber."
      - "Look for narrative findings and recommended actions."

themes: []  # Global themes to emphasize
```

### Adding Document-Specific Biases

Add entries to `document_biases` in the config file:

```yaml
document_biases:
  "Pattern to Match":
    prompts:
      - "First prompt instruction"
      - "Second prompt instruction"
```

The pattern is matched against the document filename (case-insensitive).

## Training Data

### Training Data Structure

Training files should be placed in `C:/Tools/Ollama/training_data/` and follow this schema:

```json
{
  "vulnerabilities": [
    {
      "vulnerability": "Vulnerability description",
      "discipline_id": "uuid-here",
      "category": "Physical",
      "sector_id": "uuid-here",
      "subsector_id": "uuid-here",
      "page_ref": "1-2",
      "chunk_id": "doc_001_chunk_01"
    }
  ],
  "options_for_consideration": [
    {
      "option_text": "OFC description",
      "vulnerability": "Vulnerability text (reference)",
      "discipline_id": "uuid-here",
      "sector_id": "uuid-here",
      "subsector_id": "uuid-here"
    }
  ],
  "references": [
    {
      "title": "Document title",
      "url": "https://example.com/doc.pdf",
      "author": "Author name",
      "publication_date": "2021-03-01"
    }
  ]
}
```

### Retraining the Model

Use the retraining script to fine-tune the model:

```bash
python scripts/retrain-vofc-engine.py
```

This script:
1. Validates training files
2. Creates Ollama training configuration
3. Provides instructions for running training

**Note:** Actual model training may require additional setup with fine-tuning frameworks (Hugging Face Transformers, LoRA, etc.) as Ollama's native training capabilities may be limited.

## Database Schema

Learning events are stored in the `learning_events` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Link to submission (nullable) |
| `event_type` | `text` | `'post_audit_enrichment'` |
| `approved` | `boolean` | `true` (enrichment events are positive examples) |
| `model_version` | `text` | Model version (e.g., `'vofc-engine:latest'`) |
| `confidence_score` | `decimal` | `NULL` (not applicable for enrichment) |
| `metadata` | `jsonb` | Contains correction payload, themes, examples |
| `created_at` | `timestamptz` | Event timestamp |

## Example Workflow

1. **Document Processed**: Model extracts 1 vulnerability from USSS document
2. **Analyst Reviews**: Identifies 10 vulnerabilities that should have been found
3. **Learning Event Logged**: Correction logged with themes and examples
4. **Next Similar Document**: Model receives enhanced prompt with:
   - Document bias: "Focus on systemic and behavioral vulnerabilities..."
   - Enrichment themes: "threat assessment, leakage, discipline follow-up..."
   - Example patterns: Past corrections for similar documents
5. **Improved Extraction**: Model extracts 8 vulnerabilities (closer to target)

## Integration Points

### In Processing Pipeline

The enhanced prompts are automatically applied when:
- `run_model()` is called with `file_path` parameter
- `run_model_on_chunks()` is called with `file_path` parameter

### In Review Interface

Analysts can trigger learning event logging through:
- Manual correction workflows
- Bulk correction tools
- API endpoints (to be implemented)

## Future Enhancements

- **Automatic Learning Event Creation**: Detect when analysts make corrections and automatically log events
- **Embedding-Based Similarity**: Use document embeddings to find similar documents and apply their enrichment context
- **Confidence Threshold Adjustment**: Automatically adjust confidence thresholds based on learning events
- **A/B Testing**: Compare model versions with and without enrichment context

## Related Documentation

- `docs/LEARNING-SYSTEM.md` - General learning system overview
- `docs/LEARNING-LOGGER.md` - Automatic learning event logging
- `config/vofc_config.yaml` - Configuration file
- `scripts/log-learning-event-example.py` - Example usage script
- `scripts/retrain-vofc-engine.py` - Retraining script

