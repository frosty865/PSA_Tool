"""
Builds USSS Averting Targeted School Violence (2021) training sample,
writes Ollama training config, and registers a learning_event in Supabase.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services.supabase_client import get_supabase_client
except ImportError:
    print("[!] Warning: Could not import supabase_client. Learning event registration will be skipped.")
    get_supabase_client = None

TRAIN_DIR = os.path.join(os.getcwd(), "training_data")
os.makedirs(TRAIN_DIR, exist_ok=True)

# === 1️⃣ Create the USSS training JSON ===
usss_training = {
    "source_file": "USSS Averting Targeted School Violence.2021.03.pdf",
    "processed_at": datetime.utcnow().isoformat(),
    "vulnerabilities": [
        {
            "vulnerability": "Absence of formal threat-assessment programs or inconsistent team operation.",
            "category": "Procedural",
            "discipline": "Behavioral Threat Assessment",
            "ofcs": [
                "Establish multidisciplinary behavioral threat assessment teams.",
                "Adopt standardized operating procedures aligned with REMS and USSS NTAC guidance."
            ],
        },
        {
            "vulnerability": "Leakage of intent or threats not acted upon by peers or staff.",
            "category": "Awareness",
            "discipline": "Reporting Systems",
            "ofcs": [
                "Implement anonymous reporting systems (Safe2Tell, Stop It).",
                "Train staff and students to identify and report warning behaviors."
            ],
        },
        {
            "vulnerability": "Information silos between schools, law enforcement, and mental health providers.",
            "category": "Coordination",
            "discipline": "Information Sharing",
            "ofcs": [
                "Develop MOUs for information sharing within FERPA/HIPAA bounds.",
                "Assign liaison officers to connect school, police, and behavioral health resources."
            ],
        },
        {
            "vulnerability": "Disciplinary removals without follow-up support or reintegration.",
            "category": "Policy",
            "discipline": "Discipline & Reintegration",
            "ofcs": [
                "Pair disciplinary actions with re-entry plans and monitoring.",
                "Coordinate with counselors to maintain engagement post-incident."
            ],
        },
        {
            "vulnerability": "Concerning behaviors observed by multiple staff not linked together.",
            "category": "Procedural",
            "discipline": "Incident Reporting",
            "ofcs": [
                "Centralize behavior reports in a single digital system.",
                "Ensure threat teams can review cross-staff observations in real time."
            ],
        },
        {
            "vulnerability": "Lack of accessible mental-health resources for at-risk students.",
            "category": "Resilience",
            "discipline": "Mental Health Integration",
            "ofcs": [
                "Expand partnerships with community mental-health providers.",
                "Embed counselors and social workers in threat-assessment teams."
            ],
        },
        {
            "vulnerability": "No proactive monitoring of social-media indicators.",
            "category": "Technology",
            "discipline": "Social Media Awareness",
            "ofcs": [
                "Develop policies for monitoring public social-media threats.",
                "Train staff on recognizing online indicators of targeted violence."
            ],
        },
        {
            "vulnerability": "Unsecured access to firearms in homes of subjects.",
            "category": "Physical",
            "discipline": "Firearm Access Control",
            "ofcs": [
                "Conduct firearm-safety and secure-storage awareness campaigns.",
                "Work with law enforcement for temporary removal under risk-protection laws."
            ],
        },
        {
            "vulnerability": "Lack of structured after-action reviews following averted attacks.",
            "category": "Programmatic",
            "discipline": "Continuous Improvement",
            "ofcs": [
                "Create post-incident review processes to capture lessons learned.",
                "Update threat-assessment protocols after every averted incident."
            ],
        },
        {
            "vulnerability": "Negative or exclusionary school climate fostering alienation.",
            "category": "Cultural",
            "discipline": "School Climate & Inclusion",
            "ofcs": [
                "Implement social-emotional learning and anti-bullying programs.",
                "Promote inclusive activities and mentorship opportunities."
            ],
        },
    ],
}

json_path = os.path.join(TRAIN_DIR, "usss_averting_2021.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(usss_training, f, indent=2)
print(f"[+] Wrote training sample: {json_path}")

# === 2️⃣ Create Ollama Modelfile ===
system_prompt = """You are a specialized security assessment extraction engine focused on narrative risk patterns and behavioral indicators. Your task is to extract vulnerabilities and options for consideration (OFCs) from security documents, with particular emphasis on:

- Behavioral threat assessment and leakage indicators
- Information sharing and coordination gaps
- Discipline and reintegration processes
- Mental health integration and support systems
- Social media awareness and monitoring
- School climate and inclusion factors
- Firearm access control
- Continuous improvement and after-action reviews

Focus on systemic and behavioral vulnerabilities, not IT or cyber. Look for narrative findings and recommended actions. Aim to extract approximately 10 vulnerabilities per document, with 3 options for consideration per vulnerability.

Always respond in valid JSON format with structured vulnerability-OFC pairs."""

modelfile_text = f"""FROM llama3:instruct

SYSTEM \"\"\"{system_prompt}\"\"\"
"""

modelfile_path = os.path.join(TRAIN_DIR, "Modelfile")
with open(modelfile_path, "w", encoding="utf-8") as f:
    f.write(modelfile_text)
print(f"[+] Wrote Modelfile: {modelfile_path}")

# === 3️⃣ Ollama training config (for external frameworks) ===
yaml_text = """# Training configuration for external fine-tuning frameworks
# (Hugging Face Transformers, Unsloth, Axolotl, etc.)
# Ollama's native 'create' command does not support this format

model: llama3:instruct
adapter: qlora
datasets:
  - path: training_data/
    format: json
train:
  epochs: 2
  lr: 1e-5
  batch: 2
output: D:\\OllamaModels\\vofc-engine-v2
tags:
  - vofc
  - narrative_risk
  - behavioral_analysis
"""

yaml_path = os.path.join(TRAIN_DIR, "vofc_engine_training.yaml")
with open(yaml_path, "w", encoding="utf-8") as f:
    f.write(yaml_text)
print(f"[+] Wrote config (for external frameworks): {yaml_path}")

# === 4️⃣ Register a learning event in Supabase ===
# Note: This is optional and may fail due to schema constraints or cache issues.
# The training data files are the important output - learning event is just metadata.
if get_supabase_client:
    try:
        supabase = get_supabase_client()
        
        # Build metadata with training information
        metadata = {
            "source_file": "USSS Averting Targeted School Violence.2021.03.pdf",
            "themes": [
                "threat assessment",
                "reporting systems",
                "information sharing",
                "mental health",
                "social media",
                "firearm access",
                "school climate"
            ],
            "vulns_expected": 10,
            "ofcs_expected": 30,
            "delta_score": 900,  # Improvement score
            "training_type": "manual_curation",
            "training_data_file": "usss_averting_2021.json"
        }
        
        # Create learning event record - use minimal fields to avoid schema cache issues
        # PostgREST schema cache may be stale, so we use only essential fields
        # Note: event_type must be one of: 'approval', 'rejection', 'correction', 'edited', 'auto_parse'
        learning_event = {
            "event_type": "approval",  # Training data is an approved example
            "model_version": "vofc-engine:v2",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Try to add optional fields, but don't fail if they're not in schema cache
        try:
            result = supabase.table("learning_events").insert(learning_event).execute()
            if result.data:
                print(f"[+] Learning event registered in Supabase (ID: {result.data[0].get('id', 'unknown')})")
            else:
                print("[!] Warning: Learning event insert returned no data")
        except Exception as insert_error:
            # If any error, just log and continue - not critical
            error_msg = str(insert_error)
            print("[!] Note: Learning event registration skipped (schema constraint or cache issue).")
            print("   This is not critical - training data files were created successfully.")
            print("   You can manually log the learning event later if needed.")
                
    except Exception as e:
        print(f"[!] Note: Learning event registration skipped: {e}")
        print("   This is not critical - training data files were created successfully.")
else:
    print("[!] Skipping learning event registration (supabase_client not available)")

print("\n" + "="*60)
print("Ready to create model with Ollama:")
print("="*60)
print(f"  ollama create vofc-engine:v2 -f {modelfile_path}")
print("\nThis creates a model with enhanced system prompts.")
print("For actual fine-tuning, use external frameworks:")
print("  - Hugging Face Transformers with LoRA")
print("  - Unsloth (optimized LoRA training)")
print("  - Axolotl (training framework)")
