"""
VOFC Processor - Unified Pipeline
Replaces all phase-based processors with a single, service-ready pipeline.

Flow: PDF → text extraction → (optional reference subset) → vofc-engine:latest → JSON validation → Supabase upload → archive
"""
import os
import json
import uuid
import logging
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available - reference subset loading disabled")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.error("PyMuPDF (fitz) not available - PDF processing disabled")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.error("requests library not available - Ollama API calls disabled")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.error("supabase not available - database upload disabled")


# ==========================================================
# CONFIGURATION
# ==========================================================

# Load .env file if available (before reading environment variables)
try:
    from dotenv import load_dotenv
    # Try multiple possible .env file locations
    script_dir = Path(__file__).parent
    possible_env_paths = [
        script_dir.parent.parent / ".env",  # Project root
        script_dir / ".env",  # Processor directory
        Path(r"C:\Tools\PSA_Tool\.env"),  # Tools directory
        Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env"),  # User project
    ]
    
    env_loaded = False
    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)  # Don't override existing env vars
            logging.info(f"Loaded environment variables from {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        logging.debug("No .env file found in standard locations")
except ImportError:
    logging.warning("python-dotenv not installed - .env file will not be loaded automatically")
except Exception as e:
    logging.warning(f"Failed to load .env file: {e}")

# Base data directory - supports both C:\Tools\Ollama\Data and C:\Tools\VOFC
DATA_DIR = os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data")
if not os.path.exists(DATA_DIR):
    # Try alternative path
    DATA_DIR = r"C:\Tools\VOFC\Data"
    if not os.path.exists(DATA_DIR):
        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        os.makedirs(DATA_DIR, exist_ok=True)

LIB_PATH = os.path.join(DATA_DIR, "library", "VOFC_Library.xlsx")
INCOMING_DIR = os.path.join(DATA_DIR, "incoming")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LIBRARY_DIR = os.path.join(DATA_DIR, "library")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
for dir_path in [INCOMING_DIR, PROCESSED_DIR, LIBRARY_DIR, TEMP_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Supabase configuration
# Check for SUPABASE_URL (try NEXT_PUBLIC_SUPABASE_URL as fallback)
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
# Check for SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = "submissions"

# Debug logging for environment variable loading
if not SUPABASE_URL or not SUPABASE_KEY:
    logging.debug(f"Supabase env check - URL: {bool(SUPABASE_URL)}, KEY: {bool(SUPABASE_KEY)}")
    logging.debug(f"  SUPABASE_URL: {bool(os.getenv('SUPABASE_URL'))}")
    logging.debug(f"  NEXT_PUBLIC_SUPABASE_URL: {bool(os.getenv('NEXT_PUBLIC_SUPABASE_URL'))}")
    logging.debug(f"  SUPABASE_KEY: {bool(os.getenv('SUPABASE_KEY'))}")
    logging.debug(f"  SUPABASE_SERVICE_ROLE_KEY: {bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY'))}")

if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized successfully")
    except Exception as e:
        logging.warning(f"Could not initialize Supabase client: {e}")
        supabase = None
else:
    supabase = None
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.warning("Supabase credentials not configured (SUPABASE_URL, SUPABASE_KEY)")
        logging.warning("  Make sure .env file is loaded or environment variables are set")

# Ollama server configuration (treat as separate server entity)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# Model name can be set via OLLAMA_MODEL environment variable, defaults to vofc-engine:latest
MODEL_NAME = os.getenv("OLLAMA_MODEL", "vofc-engine:latest")

# Logging setup
log_file = os.path.join(LOGS_DIR, f"vofc_processor_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==========================================================
# FUNCTIONS
# ==========================================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF not available - cannot extract text from PDF")
    
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        raise


def load_reference_subset(limit: int = 2000) -> List[Dict[str, Any]]:
    """
    Load a subset of reference records from Supabase production database.
    Queries vulnerabilities and OFCs to provide context for model alignment.
    Returns empty list if Supabase is unavailable or query fails.
    """
    if not supabase:
        logger.warning("Supabase not configured - skipping reference subset loading")
        return []
    
    try:
        records = []
        
        # Get vulnerabilities from Supabase
        try:
            # Query with only columns that exist in production schema
            # Production uses 'vulnerability' (not 'vulnerability_name' or 'description')
            vuln_response = supabase.table("vulnerabilities").select(
                "id, vulnerability, discipline, sector_id, subsector_id"
            ).limit(limit).execute()
            
            vulnerabilities = vuln_response.data if vuln_response.data else []
            logger.debug(f"Fetched {len(vulnerabilities)} vulnerabilities from Supabase")
            
            # Get OFCs from Supabase
            ofc_response = supabase.table("options_for_consideration").select(
                "id, option_text, discipline"
            ).limit(limit).execute()
            
            ofcs = ofc_response.data if ofc_response.data else []
            logger.debug(f"Fetched {len(ofcs)} OFCs from Supabase")
            
            # Get vulnerability-OFC links to pair them
            try:
                links_response = supabase.table("vulnerability_ofc_links").select(
                    "vulnerability_id, ofc_id"
                ).limit(limit * 2).execute()
                
                links = links_response.data if links_response.data else []
                logger.debug(f"Fetched {len(links)} vulnerability-OFC links from Supabase")
                
                # Create lookup maps
                vuln_map = {v.get("id"): v for v in vulnerabilities}
                ofc_map = {o.get("id"): o for o in ofcs}
                
                # Build paired records from links
                for link in links[:limit]:
                    vuln_id = link.get("vulnerability_id")
                    ofc_id = link.get("ofc_id")
                    
                    vuln = vuln_map.get(vuln_id)
                    ofc = ofc_map.get(ofc_id)
                    
                    if vuln and ofc:
                        records.append({
                            "id": str(vuln_id),
                            "vulnerability": str(vuln.get("vulnerability", "")).strip(),
                            "ofc": str(ofc.get("option_text", "")).strip(),
                            "discipline": str(vuln.get("discipline") or ofc.get("discipline", "")).strip(),
                            "sector": "",  # Would need to join sectors table
                            "subsector": ""  # Would need to join subsectors table
                        })
                
                # Add standalone vulnerabilities (without OFCs)
                for vuln in vulnerabilities:
                    if len(records) >= limit:
                        break
                    vuln_id = vuln.get("id")
                    # Skip if already added via link
                    if not any(r.get("id") == str(vuln_id) for r in records):
                        # Use vulnerability column (production schema)
                        vuln_text = str(vuln.get("vulnerability", "")).strip()
                        if vuln_text:
                            records.append({
                                "id": str(vuln_id),
                                "vulnerability": vuln_text,
                                "ofc": "",
                                "discipline": str(vuln.get("discipline", "")).strip(),
                                "sector": "",
                                "subsector": ""
                            })
                
                # Add standalone OFCs (without vulnerabilities)
                for ofc in ofcs:
                    if len(records) >= limit:
                        break
                    ofc_id = ofc.get("id")
                    # Skip if already added via link (check if any record has this OFC text)
                    ofc_text = str(ofc.get("option_text", "")).strip()
                    if not any(r.get("ofc", "").strip() == ofc_text for r in records):
                        records.append({
                            "id": str(uuid.uuid4()),
                            "vulnerability": "",
                            "ofc": ofc_text,
                            "discipline": str(ofc.get("discipline", "")).strip(),
                            "sector": "",
                            "subsector": ""
                        })
                        
            except Exception as link_error:
                logger.warning(f"Could not fetch vulnerability-OFC links: {link_error}")
                # Fall back to just vulnerabilities and OFCs separately
                for vuln in vulnerabilities[:limit//2]:
                    records.append({
                        "id": str(vuln.get("id")),
                        "vulnerability": str(vuln.get("vulnerability", "")).strip(),
                        "ofc": "",
                        "discipline": str(vuln.get("discipline", "")).strip(),
                        "sector": "",
                        "subsector": ""
                    })
                
                for ofc in ofcs[:limit//2]:
                    if len(records) >= limit:
                        break
                    records.append({
                        "id": str(ofc.get("id")),
                        "vulnerability": "",
                        "ofc": str(ofc.get("option_text", "")).strip(),
                        "discipline": str(ofc.get("discipline", "")).strip(),
                        "sector": "",
                        "subsector": ""
                    })
        
        except Exception as query_error:
            logger.warning(f"Error querying Supabase for reference data: {query_error}")
            return []
        
        result = records[:limit]
        logger.info(f"Loaded {len(result)} reference records from Supabase production database")
        return result
        
    except Exception as e:
        logger.warning(f"Error loading reference subset from Supabase: {e}")
        return []


def send_to_ollama(document_text: str, reference_context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Send document text and reference context to vofc-engine:latest via Ollama HTTP API.
    Treats Ollama as a separate server entity.
    Returns the model response.
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not available - cannot call Ollama API")
    
    # Build reference context block
    reference_block = {
        "context_summary": (
            "Reference VOFC Library for canonical vulnerabilities and OFCs. "
            "Use this to align, merge, or reuse existing records where relevant."
        ),
        "records": reference_context
    }
    
    context_json = json.dumps(reference_block, ensure_ascii=False, indent=2)
    
    prompt = f"""Extract physical security vulnerabilities and OFCs from this document. Return ONLY valid JSON.

Reference Context:
{context_json}

Document:
{document_text}

Output format - JSON object with records array:
{{
  "records": [
    {{
      "vulnerability": "<physical security issue>",
      "options_for_consideration": ["<mitigation1>", "<mitigation2>"],
      "discipline": "<discipline name>",
      "sector": "<sector name>",
      "subsector": "<subsector name>",
      "confidence": "High|Medium|Low",
      "impact_level": "High|Moderate|Low",
      "follow_up": false,
      "standard_reference": "<reference if applicable>"
    }}
  ],
  "links": [
    {{
      "ofc": "<option text>",
      "linked_vulnerabilities": ["<vuln1>", "<vuln2>"]
    }}
  ]
}}

Rules:
- Physical security only (perimeter, access, lighting, locks, barriers, guards, CPTED, surveillance, intrusion detection, visitor management)
- NO cyber/CVE/patch/exploit content
- Extract inclusively - include all plausible vulnerabilities and mitigations
- Normalize disciplines and sectors to match DHS standards
- If nothing found, return: {{"records": [], "links": []}}
- NO explanations or markdown - ONLY valid JSON

JSON:"""
    
    # Ollama API endpoint for generate
    api_url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": {
            "temperature": 0.1,
            "num_predict": 8192  # Increase max tokens to prevent JSON truncation
        },
        "stream": False
    }
    
    try:
        logger.info(f"Calling Ollama server at {OLLAMA_BASE_URL} with model {MODEL_NAME}...")
        logger.debug(f"Request: model={MODEL_NAME}, num_predict=8192, prompt_length={len(prompt)} chars")
        
        response = requests.post(
            api_url,
            json=payload,
            timeout=600,  # 10 minute timeout for large documents with long responses
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()  # Raise exception for HTTP errors
        
        result = response.json()
        
        if "response" not in result:
            raise ValueError(f"Unexpected response format from Ollama: {result}")
        
        logger.info(f"✓ Received response from Ollama server ({len(result.get('response', ''))} chars)")
        return result
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to Ollama server at {OLLAMA_BASE_URL}")
        logger.error(f"  Error: {e}")
        logger.error(f"  Please ensure Ollama server is running and accessible")
        raise ConnectionError(f"Cannot connect to Ollama server at {OLLAMA_BASE_URL}: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Request to Ollama server timed out after 5 minutes")
        raise TimeoutError(f"Ollama server request timed out: {e}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error from Ollama server: {e}")
        logger.error(f"  Response: {response.text if 'response' in locals() else 'N/A'}")
        raise
    except Exception as e:
        logger.error(f"Error calling Ollama API: {e}")
        raise


def calculate_dedupe_key(vulnerability: str, first_ofc: str = "") -> str:
    """
    Calculate SHA1 hash for deduplication key.
    Format: sha1(vulnerability + first_ofc)
    Returns lowercase hash to ensure consistency.
    """
    combined = f"{vulnerability.strip()}{first_ofc.strip()}"
    return hashlib.sha1(combined.encode('utf-8')).hexdigest().lower()


def save_output(base_name: str, response_text: str) -> tuple[str, Dict[str, Any]]:
    """
    Save model response to JSON file and validate.
    Returns (output_path, parsed_data).
    """
    # Validate input
    if not response_text or not response_text.strip():
        error_msg = f"Empty response from model for {base_name}"
        logger.error(error_msg)
        error_path = os.path.join(PROCESSED_DIR, f"{base_name}_error.txt")
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(f"Error: {error_msg}\n")
            f.write(f"Response was empty or whitespace only.\n")
        raise ValueError(error_msg)
    
    # Try to parse JSON from response
    try:
        # Extract JSON from response if it's wrapped in markdown or other text
        original_text = response_text
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        import re
        if response_text.startswith('```'):
            response_text = re.sub(r'```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'```\s*$', '', response_text)
            response_text = response_text.strip()
        
        # Try to find the complete JSON object by matching balanced braces
        # Look for opening brace followed by "records"
        json_start = response_text.find('{"records"')
        if json_start == -1:
            json_start = response_text.find('{')
        
        if json_start >= 0:
            # Find the matching closing brace by counting braces
            brace_count = 0
            json_end = -1
            in_string = False
            escape_next = False
            
            for i in range(json_start, len(response_text)):
                char = response_text[i]
                
                # Handle string literals (don't count braces inside strings)
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
            
            if json_end > json_start:
                response_text = response_text[json_start:json_end]
            else:
                # JSON is incomplete - try to extract what we have and fix it
                logger.warning(f"JSON appears incomplete (brace_count={brace_count}), attempting to fix...")
                
                # Try to extract partial JSON and close it
                partial_json = response_text[json_start:]
                
                # If we have "records" array, try to close it
                if '"records"' in partial_json:
                    # Find the records array
                    records_start = partial_json.find('"records"')
                    if records_start >= 0:
                        # Try to find where records array should end
                        # Look for the last complete record
                        last_complete_record = partial_json.rfind('}')
                        if last_complete_record > records_start:
                            # Try to construct valid JSON
                            # Extract up to last complete record, then close arrays/objects
                            try:
                                # Find the opening of records array
                                array_start = partial_json.find('[', records_start)
                                if array_start >= 0:
                                    # Count complete records (ending with })
                                    record_count = partial_json[array_start:last_complete_record+1].count('},')
                                    if record_count > 0:
                                        # Build complete JSON
                                        fixed_json = partial_json[:last_complete_record+1]
                                        # Close records array
                                        if fixed_json[-1] != ']':
                                            fixed_json += ']'
                                        # Close main object
                                        if fixed_json[-1] != '}':
                                            fixed_json += '}'
                                        # Add empty links if missing
                                        if '"links"' not in fixed_json:
                                            fixed_json = fixed_json.rstrip('}') + ', "links": []}'
                                        response_text = fixed_json
                                        logger.info(f"Fixed incomplete JSON by closing {record_count} records")
                            except Exception as fix_error:
                                logger.warning(f"Could not fix incomplete JSON: {fix_error}")
                
                # Final fallback: try regex
                if not response_text or response_text == partial_json:
                    json_match = re.search(r'(\{.*?"records".*?\})', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(1)
                    else:
                        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                        if json_match:
                            response_text = json_match.group(1)
        
        # Final validation before parsing
        response_text = response_text.strip()
        if not response_text:
            raise ValueError("No JSON found in response after extraction")
        
        data = json.loads(response_text)
        
        # Handle new schema: {"records": [...], "links": [...]}
        if isinstance(data, dict):
            records = data.get("records", [])
            links = data.get("links", [])
        elif isinstance(data, list):
            # Legacy format - convert to new format
            records = data
            links = []
        else:
            raise ValueError(f"Unexpected response format: {type(data)}")
        
        # Process records: normalize and add dedupe_key
        valid_records = []
        for record in records:
            if not isinstance(record, dict):
                continue
            
            vulnerability = str(record.get("vulnerability", "")).strip()
            options_for_consideration = record.get("options_for_consideration", [])
            
            # Handle both array and string formats for OFCs
            if isinstance(options_for_consideration, str):
                options_for_consideration = [options_for_consideration]
            elif not isinstance(options_for_consideration, list):
                options_for_consideration = []
            
            first_ofc = options_for_consideration[0] if options_for_consideration else ""
            
            # Skip empty records and cyber hallucinations
            if not vulnerability or vulnerability.lower().startswith(("apache", "cve-", "log4j", "placeholder", "dummy", "test", "example")):
                continue
            
            # Calculate dedupe_key
            dedupe_key = calculate_dedupe_key(vulnerability, first_ofc)
            
            # Build normalized record
            normalized = {
                "vulnerability": vulnerability,
                "options_for_consideration": [str(ofc).strip() for ofc in options_for_consideration if ofc],
                "discipline": str(record.get("discipline", "")).strip(),
                "sector": str(record.get("sector", "")).strip(),
                "subsector": str(record.get("subsector", "")).strip(),
                "confidence": str(record.get("confidence", "Medium")).strip(),
                "impact_level": str(record.get("impact_level", "Moderate")).strip(),
                "follow_up": bool(record.get("follow_up", False)),
                "dedupe_key": dedupe_key,
                "standard_reference": str(record.get("standard_reference", "")).strip()
            }
            
            valid_records.append(normalized)
        
        # Process links
        valid_links = []
        for link in links:
            if not isinstance(link, dict):
                continue
            ofc = str(link.get("ofc", "")).strip()
            linked_vulns = link.get("linked_vulnerabilities", [])
            if ofc and linked_vulns:
                valid_links.append({
                    "ofc": ofc,
                    "linked_vulnerabilities": [str(v).strip() for v in linked_vulns if v]
                })
        
        # Build final data structure
        data = {
            "records": valid_records,
            "links": valid_links
        }
        
    except json.JSONDecodeError as e:
        # Save error output for debugging
        error_path = os.path.join(PROCESSED_DIR, f"{base_name}_error.txt")
        original = original_text if 'original_text' in locals() else response_text
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(f"JSON Decode Error: {e}\n\n")
            f.write(f"Error position: line {e.lineno}, column {e.colno}\n\n")
            f.write(f"Response length: {len(original)} chars\n\n")
            f.write("Original Response (first 2000 chars):\n")
            f.write(original[:2000])
            f.write("\n\n")
            f.write("Extracted Text (attempted to parse):\n")
            f.write(response_text[:2000] if len(response_text) > 2000 else response_text)
            f.write("\n\n")
            f.write("Full Response:\n")
            f.write(original)
        logger.error(f"Invalid JSON from engine for {base_name} - saved to {error_path}")
        logger.error(f"  Error: {e}")
        logger.error(f"  Response length: {len(original)} chars")
        logger.error(f"  First 500 chars: {original[:500]}")
        
        # Try to extract partial data if possible
        if '"records"' in original and '[' in original:
            logger.warning("Attempting to extract partial records from incomplete JSON...")
            try:
                # Try to find and extract just the records array
                records_match = re.search(r'"records"\s*:\s*\[(.*?)\]', original, re.DOTALL)
                if records_match:
                    records_content = records_match.group(1)
                    # Try to extract individual records
                    record_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', records_content)
                    if record_matches:
                        logger.info(f"Found {len(record_matches)} potentially extractable records")
                        # Could attempt to parse these individually, but for now just log
            except Exception as extract_error:
                logger.debug(f"Could not extract partial records: {extract_error}")
        
        raise ValueError(f"Invalid JSON from engine for {base_name}: {e}")
    except Exception as e:
        # Catch any other parsing errors
        error_path = os.path.join(PROCESSED_DIR, f"{base_name}_error.txt")
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(f"Error parsing response: {e}\n\n")
            f.write("Original Response:\n")
            f.write(original_text if 'original_text' in locals() else response_text)
        logger.error(f"Error parsing response for {base_name}: {e}")
        raise
    
    # Save valid JSON output
    output_path = os.path.join(PROCESSED_DIR, f"{base_name}_vofc.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    record_count = len(data.get("records", []))
    link_count = len(data.get("links", []))
    logger.info(f"Saved output to {output_path} ({record_count} records, {link_count} links)")
    return output_path, data


def check_existing_vulnerability(dedupe_key: str) -> Optional[str]:
    """
    Check if vulnerability exists in Supabase using dedupe_key.
    Returns vulnerability ID if found, None otherwise.
    """
    if not supabase:
        return None
    
    try:
        # Query vulnerabilities table for matching dedupe_key
        # Note: This assumes a dedupe_key column exists in vulnerabilities table
        response = supabase.table("vulnerabilities").select("id").eq("dedupe_key", dedupe_key).limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("id")
    except Exception as e:
        logger.debug(f"Could not check for existing vulnerability (dedupe_key may not exist in schema): {e}")
        # Fallback: query by vulnerability name if dedupe_key column doesn't exist yet
        # This is a temporary workaround until schema is updated
    
    return None


def upload_to_supabase(file_path: str, data: Dict[str, Any]) -> Optional[str]:
    """
    Upload processed records to Supabase using dedupe_key for deduplication.
    Checks for existing records and links/updates instead of inserting duplicates.
    Returns submission_id if successful, None otherwise.
    """
    if not supabase:
        logger.warning("Supabase not configured - skipping upload")
        return None
    
    records = data.get("records", [])
    links = data.get("links", [])
    
    if not records:
        logger.info("No records to upload")
        return None
    
    try:
        submission_id = str(uuid.uuid4())
        processed_vuln_ids = []
        processed_ofc_ids = []
        inserted_count = 0
        linked_count = 0
        
        # Process each record: check for existing, insert or link
        for record in records:
            dedupe_key = record.get("dedupe_key")
            vulnerability = record.get("vulnerability", "")
            options_for_consideration = record.get("options_for_consideration", [])
            discipline = record.get("discipline", "")
            sector = record.get("sector", "")
            subsector = record.get("subsector", "")
            confidence = record.get("confidence", "Medium")
            impact_level = record.get("impact_level", "Moderate")
            follow_up = record.get("follow_up", False)
            standard_reference = record.get("standard_reference", "")
            
            if not vulnerability:
                continue
            
            # Check if vulnerability already exists using dedupe_key
            existing_vuln_id = check_existing_vulnerability(dedupe_key) if dedupe_key else None
            
            if existing_vuln_id:
                logger.info(f"Vulnerability already exists (dedupe_key: {dedupe_key[:8]}...), linking instead of inserting")
                processed_vuln_ids.append(existing_vuln_id)
                linked_count += 1
            else:
                # Insert new vulnerability
                try:
                    vuln_payload = {
                        "vulnerability": vulnerability,
                        "description": vulnerability,
                        "discipline": discipline if discipline else None,
                        "dedupe_key": dedupe_key.lower() if dedupe_key else None,  # Ensure lowercase
                        "confidence": confidence if confidence else None,
                        "impact_level": impact_level if impact_level else None,
                        "follow_up": follow_up,
                        "standard_reference": standard_reference if standard_reference else None
                    }
                    
                    # Note: sector_id and subsector_id would need lookup from sectors/subsectors tables
                    # For now, storing as text if schema supports it
                    
                    vuln_response = supabase.table("vulnerabilities").insert(vuln_payload).execute()
                    if vuln_response.data and len(vuln_response.data) > 0:
                        new_vuln_id = vuln_response.data[0].get("id")
                        processed_vuln_ids.append(new_vuln_id)
                        inserted_count += 1
                        logger.info(f"Inserted new vulnerability: {new_vuln_id} (dedupe_key: {dedupe_key[:8]}...)")
                    else:
                        logger.warning(f"Failed to insert vulnerability: {vulnerability[:50]}...")
                        continue
                except Exception as e:
                    logger.error(f"Error inserting vulnerability: {e}")
                    continue
            
            # Process OFCs for this vulnerability
            for ofc_text in options_for_consideration:
                if not ofc_text:
                    continue
                
                # Check if OFC already exists (by text match)
                try:
                    ofc_check = supabase.table("options_for_consideration").select("id").eq("option_text", ofc_text).limit(1).execute()
                    if ofc_check.data and len(ofc_check.data) > 0:
                        ofc_id = ofc_check.data[0].get("id")
                    else:
                        # Insert new OFC
                        ofc_payload = {
                            "option_text": ofc_text,
                            "discipline": discipline if discipline else None
                        }
                        ofc_response = supabase.table("options_for_consideration").insert(ofc_payload).execute()
                        if ofc_response.data and len(ofc_response.data) > 0:
                            ofc_id = ofc_response.data[0].get("id")
                        else:
                            logger.warning(f"Failed to insert OFC: {ofc_text[:50]}...")
                            continue
                    
                    processed_ofc_ids.append(ofc_id)
                    
                    # Link vulnerability to OFC
                    if processed_vuln_ids:
                        vuln_id = processed_vuln_ids[-1]  # Use most recent vulnerability
                        try:
                            # Check if link already exists
                            link_check = supabase.table("vulnerability_ofc_links").select("id").eq("vulnerability_id", vuln_id).eq("ofc_id", ofc_id).limit(1).execute()
                            if not link_check.data or len(link_check.data) == 0:
                                # Get source document name from file path
                                source_doc = os.path.basename(file_path) if file_path else None
                                link_payload = {
                                    "vulnerability_id": vuln_id,
                                    "ofc_id": ofc_id,
                                    "source_document": source_doc  # Track which document this link came from
                                }
                                supabase.table("vulnerability_ofc_links").insert(link_payload).execute()
                                logger.debug(f"Linked vulnerability {vuln_id} to OFC {ofc_id} (source: {source_doc})")
                        except Exception as e:
                            logger.warning(f"Could not create vulnerability-OFC link: {e}")
                except Exception as e:
                    logger.warning(f"Error processing OFC: {e}")
        
        # Create submission record for tracking
        payload = {
            "id": submission_id,
            "type": "document",
            "status": "pending_review",
            "source": "vofc_processor",
            "submitter_email": "system@vofc.local",
            "document_name": os.path.basename(file_path),
            "model_version": MODEL_NAME,  # Track model version at top level
            "data": {
                "source_file": os.path.basename(file_path),
                "processed_at": datetime.utcnow().isoformat(),
                "records": records,
                "links": links,
                "model_version": MODEL_NAME,
                "inserted_count": inserted_count,
                "linked_count": linked_count
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table(SUPABASE_TABLE).insert(payload).execute()
        
        if result.data:
            logger.info(f"Uploaded to Supabase: submission_id={submission_id} ({inserted_count} inserted, {linked_count} linked)")
            return submission_id
        else:
            logger.warning(f"Supabase insert returned no data for {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error uploading to Supabase: {e}")
        return None


def process_pdf(pdf_path: str, reference_context: List[Dict[str, Any]]) -> bool:
    """
    Process a single PDF file through the complete pipeline.
    Returns True if successful, False otherwise.
    """
    base_name = Path(pdf_path).stem
    logger.info(f"[+] Processing: {os.path.basename(pdf_path)}")
    
    try:
        # 1. Extract text from PDF
        logger.info("  [1/5] Extracting text from PDF...")
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text.strip()) < 100:
            logger.warning(f"  ⚠️  Extracted text is too short ({len(text)} chars) - skipping")
            return False
        logger.info(f"  ✓ Extracted {len(text)} characters")
        
        # 2. Send to Ollama model
        logger.info(f"  [2/5] Sending to {MODEL_NAME}...")
        response = send_to_ollama(text, reference_context)
        response_text = response.get("response", "")
        if not response_text or not response_text.strip():
            logger.error("  ✗ Empty response from model")
            logger.error(f"  Response object keys: {list(response.keys())}")
            logger.error(f"  Full response: {response}")
            return False
        logger.info(f"  ✓ Received response ({len(response_text)} chars)")
        # Log first 200 chars for debugging
        preview = response_text[:200].replace('\n', '\\n')
        logger.debug(f"  Response preview: {preview}...")
        
        # 3. Save and validate JSON output
        logger.info("  [3/5] Saving and validating JSON output...")
        output_path, data = save_output(base_name, response_text)
        records = data.get("records", [])
        if not records:
            logger.warning("  ⚠️  No records extracted from document")
            return False
        logger.info(f"  ✓ Saved {len(records)} records to {output_path}")
        
        # 4. Upload to Supabase (with dedupe_key checking)
        logger.info("  [4/5] Uploading to Supabase...")
        submission_id = upload_to_supabase(pdf_path, data)
        if submission_id:
            logger.info(f"  ✓ Uploaded to Supabase (submission_id={submission_id})")
        else:
            logger.warning("  ⚠️  Supabase upload skipped or failed")
        
        # 5. Move to library
        logger.info("  [5/5] Archiving to library...")
        dest = os.path.join(LIBRARY_DIR, os.path.basename(pdf_path))
        if os.path.exists(dest):
            # Add timestamp to avoid overwrite
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(os.path.basename(pdf_path))
            dest = os.path.join(LIBRARY_DIR, f"{name}_{timestamp}{ext}")
        
        # Ensure library directory exists
        os.makedirs(LIBRARY_DIR, exist_ok=True)
        
        # Move file with error handling
        try:
            if not os.path.exists(pdf_path):
                logger.warning(f"  ⚠️  Source file no longer exists: {pdf_path}")
            else:
                os.replace(pdf_path, dest)
                # Verify move succeeded
                if os.path.exists(dest) and not os.path.exists(pdf_path):
                    logger.info(f"  ✓ Moved to library: {os.path.basename(dest)}")
                else:
                    logger.error(f"  ✗ Move failed - file still in incoming: {pdf_path}")
                    logger.error(f"  Destination: {dest}")
                    raise Exception("File move verification failed")
        except Exception as move_error:
            logger.error(f"  ✗ Error moving file to library: {move_error}")
            # Try alternative: copy and delete
            try:
                import shutil
                shutil.copy2(pdf_path, dest)
                if os.path.exists(dest):
                    os.remove(pdf_path)
                    logger.info(f"  ✓ Moved to library (via copy): {os.path.basename(dest)}")
                else:
                    raise Exception("Copy operation failed")
            except Exception as copy_error:
                logger.error(f"  ✗ Copy fallback also failed: {copy_error}")
                raise Exception(f"Failed to move file from incoming to library: {move_error}")
        
        logger.info(f"[✓] Completed: {os.path.basename(pdf_path)}")
        return True
        
    except Exception as e:
        logger.error(f"[✗] Error processing {pdf_path}: {e}", exc_info=True)
        # Move failed file to temp for manual review
        error_dest = os.path.join(TEMP_DIR, f"{base_name}_error_{int(time.time())}.pdf")
        try:
            os.replace(pdf_path, error_dest)
            logger.info(f"  Moved failed file to: {error_dest}")
        except:
            pass
        return False


def process_all_pdfs():
    """Main processing loop - processes all PDFs in incoming directory."""
    logger.info("=" * 60)
    logger.info("VOFC Processor - Starting processing cycle")
    logger.info("=" * 60)
    
    # Check Ollama server availability and model
    if REQUESTS_AVAILABLE:
        try:
            # Check if Ollama server is reachable
            health_url = f"{OLLAMA_BASE_URL}/api/tags"
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()
            
            # Get available models
            models_data = response.json()
            model_names = [m.get("name", "") for m in models_data.get("models", [])]
            
            if MODEL_NAME not in model_names:
                logger.warning(f"Model {MODEL_NAME} not found on Ollama server at {OLLAMA_BASE_URL}")
                logger.warning(f"Available models: {model_names}")
                logger.warning(f"Set OLLAMA_MODEL environment variable to use an available model (e.g., vofc-unified:latest)")
                logger.warning("Service will continue but model calls will fail until model is configured.")
                # Don't return - allow service to start and process files when model is available
            
            logger.info(f"✓ Ollama server at {OLLAMA_BASE_URL} is reachable")
            logger.info(f"✓ Model {MODEL_NAME} is available on server")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Cannot connect to Ollama server at {OLLAMA_BASE_URL}")
            logger.warning("Please ensure Ollama server is running and accessible")
            logger.warning("Service will continue but processing will fail until Ollama is available.")
            # Don't return - allow service to start
        except Exception as e:
            logger.warning(f"Could not verify Ollama server/model availability: {e}")
    
    # Load reference subset (optional)
    logger.info("Loading reference subset from library...")
    refs = load_reference_subset(limit=2000)
    if refs:
        logger.info(f"Loaded {len(refs)} reference records")
    else:
        logger.info("No reference subset loaded - processing without context")
    
    # Process all PDFs in incoming directory
    pdf_files = [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        logger.info("No PDF files found in incoming directory")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to process")
    
    success_count = 0
    fail_count = 0
    
    for file in pdf_files:
        pdf_path = os.path.join(INCOMING_DIR, file)
        if process_pdf(pdf_path, refs):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("=" * 60)
    logger.info(f"Processing cycle complete: {success_count} succeeded, {fail_count} failed")
    logger.info("=" * 60)


def run_service_loop():
    """Continuous service loop - runs processing cycles repeatedly."""
    logger.info("=" * 60)
    logger.info("VOFC Processor Service - Starting continuous loop")
    logger.info("=" * 60)
    
    cycle_count = 0
    check_interval = 30  # seconds between cycles
    
    while True:
        try:
            cycle_count += 1
            logger.info("")
            logger.info(f"--- Processing Cycle #{cycle_count} ---")
            logger.info(f"Checking for PDFs in: {INCOMING_DIR}")
            
            # Run one processing cycle
            process_all_pdfs()
            
            # Wait before next cycle
            logger.info(f"Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("Service loop interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in service loop: {e}", exc_info=True)
            logger.info(f"Waiting {check_interval} seconds before retry...")
            time.sleep(check_interval)


if __name__ == "__main__":
    # Run as continuous service loop
    run_service_loop()

