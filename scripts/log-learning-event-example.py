#!/usr/bin/env python3
"""
Example script to log a post-audit enrichment learning event.

This demonstrates how to use the learning feedback system to log corrections
that will inform future model behavior.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.learning_feedback import log_post_audit_enrichment

# Example: Log enrichment event for USSS document
if __name__ == "__main__":
    result = log_post_audit_enrichment(
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
    
    if result:
        print("✅ Learning event logged successfully!")
        print(f"   Event ID: {result.get('id')}")
    else:
        print("❌ Failed to log learning event")
        sys.exit(1)

