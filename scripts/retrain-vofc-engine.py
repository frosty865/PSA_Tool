#!/usr/bin/env python3
"""
Retrain/Fine-tune VOFC Engine Model

This script fine-tunes the VOFC engine model using training data from the
training_data/ directory. It creates a new model version with improved
narrative-risk comprehension.
"""

import os
import json
import yaml
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

# Configuration
CONFIG_PATH = Path("config/vofc_config.yaml")
TRAINING_DATA_DIR = Path("C:/Tools/Ollama/training_data")
OUTPUT_DIR = Path("D:/OllamaModels")
BASE_MODEL = "llama3:instruct"
NEW_MODEL_NAME = "vofc-engine:v2"


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def collect_training_files(data_dir: Path) -> List[Path]:
    """Collect all JSON training files from the data directory."""
    training_files = []
    for file_path in data_dir.glob("*.json"):
        if not file_path.name.endswith(".example"):
            training_files.append(file_path)
    return training_files


def validate_training_file(file_path: Path) -> bool:
    """Validate that a training file has the correct structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check for required top-level keys
        required_keys = ["vulnerabilities", "options_for_consideration"]
        if not all(key in data for key in required_keys):
            print(f"❌ {file_path.name} missing required keys: {required_keys}")
            return False
        
        # Validate vulnerabilities structure
        if not isinstance(data["vulnerabilities"], list):
            print(f"❌ {file_path.name}: vulnerabilities must be a list")
            return False
        
        # Validate OFCs structure
        if not isinstance(data["options_for_consideration"], list):
            print(f"❌ {file_path.name}: options_for_consideration must be a list")
            return False
        
        print(f"✅ {file_path.name} is valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ {file_path.name} is not valid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating {file_path.name}: {e}")
        return False


def create_training_config(training_files: List[Path], output_path: Path) -> Path:
    """Create Ollama training configuration file."""
    config = {
        "model": BASE_MODEL,
        "adapter": "qlora",
        "datasets": [
            {
                "path": str(file_path),
                "format": "json"
            }
            for file_path in training_files
        ],
        "train": {
            "epochs": 2,
            "lr": 1e-5,
            "batch": 2
        },
        "output": str(output_path / NEW_MODEL_NAME),
        "tags": [
            "vofc",
            "narrative_risk",
            "behavioral_analysis"
        ]
    }
    
    config_path = output_path / "vofc_engine_training.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Created training config: {config_path}")
    return config_path


def run_training(config_path: Path) -> bool:
    """
    Run Ollama model training.
    
    Note: This requires Ollama's training capabilities, which may not be
    available in all Ollama installations. You may need to use a different
    fine-tuning framework (e.g., Hugging Face Transformers, LoRA, etc.).
    """
    print("\n⚠️  Note: Ollama's native training API may not be available.")
    print("   You may need to use an external fine-tuning framework.")
    print("   This script provides the structure, but actual training")
    print("   may require additional setup.\n")
    
    # Check if Ollama is available
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("❌ Ollama command not available")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Ollama not found or not responding")
        return False
    
    print("✅ Ollama is available")
    print(f"📋 Training config: {config_path}")
    print("\nTo train the model, you would run:")
    print(f"  ollama create {NEW_MODEL_NAME} -f {config_path}")
    print("\nOr use a fine-tuning framework like:")
    print("  - Hugging Face Transformers with LoRA")
    print("  - Unsloth (optimized LoRA training)")
    print("  - Axolotl (training framework)")
    
    return True


def main():
    """Main training workflow."""
    print("=" * 60)
    print("VOFC Engine Retraining Script")
    print("=" * 60)
    print()
    
    # Load configuration
    config = load_config()
    training_config = config.get("training", {})
    
    # Override paths from config if available
    data_dir = Path(training_config.get("data_path", TRAINING_DATA_DIR))
    output_dir = Path(training_config.get("output_path", OUTPUT_DIR))
    
    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Training data directory: {data_dir}")
    print(f"📁 Output directory: {output_dir}")
    print()
    
    # Collect training files
    training_files = collect_training_files(data_dir)
    
    if not training_files:
        print(f"❌ No training files found in {data_dir}")
        print("   Add JSON files following the schema in training_data/README.md")
        return 1
    
    print(f"📄 Found {len(training_files)} training file(s):")
    for file_path in training_files:
        print(f"   - {file_path.name}")
    print()
    
    # Validate training files
    print("🔍 Validating training files...")
    valid_files = []
    for file_path in training_files:
        if validate_training_file(file_path):
            valid_files.append(file_path)
    
    if not valid_files:
        print("❌ No valid training files found")
        return 1
    
    print(f"\n✅ {len(valid_files)} valid training file(s)")
    print()
    
    # Create training configuration
    config_path = create_training_config(valid_files, output_dir)
    
    # Run training (or provide instructions)
    if run_training(config_path):
        print("\n✅ Training setup complete!")
        print(f"   Config saved to: {config_path}")
        print(f"   Next: Run the training command or use a fine-tuning framework")
        return 0
    else:
        print("\n❌ Training setup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

