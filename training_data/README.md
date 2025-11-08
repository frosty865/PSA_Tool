# Training Data Directory

This directory contains training data for fine-tuning the VOFC engine model.

## Quick Start

### Option 1: Create Model with Enhanced System Prompts (Immediate)

Ollama's `create` command uses Modelfiles to add system prompts. This doesn't fine-tune the model but adds specialized instructions:

```bash
ollama create vofc-engine:v2 -f training_data/Modelfile
```

This creates a model based on `llama3:instruct` with enhanced system prompts focused on narrative risk patterns.

### Option 2: Fine-Tune with External Frameworks (Advanced)

For actual model fine-tuning (training on your data), use external frameworks:

- **Hugging Face Transformers with LoRA** - Most flexible
- **Unsloth** - Optimized for speed and memory efficiency
- **Axolotl** - Comprehensive training framework

The `vofc_engine_training.yaml` file contains configuration for these frameworks.

## Structure

Each training file should follow this JSON schema:

```json
{
  "vulnerabilities": [
    {
      "vulnerability": "Vulnerability description text",
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
      "option_text": "OFC description text",
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

## Example Files

- `usss_averting_2021.json` - USSS Averting Targeted School Violence (2021)
- `ntac_protective_investigations_2019.json` - NTAC Protective Investigations (2019)
- `fbi_school_attacks_2021.json` - FBI School Attacks Report (2021)

## Files

- `usss_averting_2021.json` - Training data with 10 vulnerabilities and OFCs
- `Modelfile` - Ollama Modelfile for creating model with enhanced prompts
- `vofc_engine_training.yaml` - Configuration for external fine-tuning frameworks

## Usage

### Using the Modelfile (Ollama Native)

```bash
# Create model with enhanced system prompts
ollama create vofc-engine:v2 -f training_data/Modelfile

# Test the model
ollama run vofc-engine:v2 "Extract vulnerabilities from this text: ..."
```

### Using External Fine-Tuning Frameworks

The training JSON files can be used with frameworks like:
- Hugging Face Transformers
- Unsloth
- Axolotl

See `scripts/retrain-vofc-engine.py` for validation and setup guidance.

## Note on Fine-Tuning

**Important:** Ollama's native `create` command does NOT perform actual fine-tuning. It only:
- Sets the base model (FROM)
- Adds system prompts (SYSTEM)
- Configures parameters (PARAMETER)

For actual fine-tuning (training the model weights on your data), you must use external frameworks that support LoRA, QLoRA, or full fine-tuning.

