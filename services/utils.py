# utils.py
import re
from typing import List, Optional

def validate_medication_name(name: str) -> bool:
    """
    Validate a medication name using regex.
    Allow letters, numbers, spaces, hyphens, apostrophes, and periods.
    Reject empty or purely numeric strings.
    """
    if not name or not name.strip():
        return False
    # Allow common characters in drug names
    pattern = r"^[A-Za-z0-9\s\-'\.]+$"
    if not re.match(pattern, name):
        return False
    # Reject if only numbers
    if re.match(r"^\d+$", name):
        return False
    return True

def clean_medical_text(text: str) -> str:
    """
    Clean raw medical text:
    - Remove extra whitespace and newlines
    - Replace multiple spaces with single space
    - Remove non-printable characters
    - Optionally remove special characters, but preserve punctuation.
    """
    if not text:
        return ""
    # Replace newlines and carriage returns with space
    text = re.sub(r"[\r\n]+", " ", text)
    # Replace multiple spaces with one
    text = re.sub(r"\s+", " ", text)
    # Remove non-ASCII characters (keep only printable)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    # Remove leading/trailing whitespace
    return text.strip()

def extract_warning_keywords(text: str) -> List[str]:
    """
    Use regex to extract common warning-related keywords/phrases.
    Returns a list of unique matched warning terms.
    """
    if not text:
        return []
    # Define pattern for warning-related terms (case-insensitive)
    pattern = r"(?i)\b(black box warning|contraindication|boxed warning|serious reaction|fatal|severe|life-threatening|allergic reaction|anaphylaxis|stevens-johnson|torsades|qt prolongation|hepatotoxicity|nephrotoxicity|cardiotoxicity|myopathy|rhabdomyolysis|pancreatitis|blood dyscrasia|suicidal|depression|psychosis|dependence|withdrawal|toxicity|overdose|hepatic impairment|renal impairment|pregnancy|breastfeeding|pediatric|geriatric)\b"
    matches = re.findall(pattern, text)
    # Return unique matches (lowercase)
    return list(set(match.lower() for match in matches))

def format_drug_info(raw_data: dict) -> dict:
    """
    Extract relevant fields from the openFDA drug labeling response.
    Return a dictionary with keys: usage, warnings, side_effects, instructions.
    """
    result = {
        "usage": "",
        "warnings": "",
        "side_effects": "",
        "instructions": "",
        "contraindications": "",
        "precautions": "",
        "interactions": "",
        "overdosage": "",
        "other_information": "",
        "available_forms": "",
    }
    try:
        # The API returns a list under 'results'
        if "results" in raw_data and raw_data["results"]:
            first_result = raw_data["results"][0]
            # Usage: often under 'indications_and_usage'
            if "indications_and_usage" in first_result:
                result["usage"] = clean_medical_text(first_result["indications_and_usage"][0])
            # Warnings: combine 'warnings' and 'boxed_warning' if present
            warnings_list = []
            if "warnings" in first_result:
                warnings_list.extend(first_result["warnings"])
            if "boxed_warning" in first_result:
                warnings_list.extend(first_result["boxed_warning"])
            result["warnings"] = clean_medical_text(" ".join(warnings_list))
            # Side effects: 'adverse_reactions'
            if "adverse_reactions" in first_result:
                result["side_effects"] = clean_medical_text(first_result["adverse_reactions"][0])
            # Instructions: 'dosage_and_administration'
            if "dosage_and_administration" in first_result:
                result["instructions"] = clean_medical_text(first_result["dosage_and_administration"][0])
            for source, target in (
                ("contraindications", "contraindications"),
                ("precautions", "precautions"),
                ("drug_interactions", "interactions"),
                ("overdosage", "overdosage"),
                ("clinical_pharmacology", "other_information"),
                ("dosage_forms_and_strengths", "available_forms"),
            ):
                values = first_result.get(source) or []
                if values:
                    result[target] = clean_medical_text(" ".join(values))
    except (KeyError, IndexError, TypeError):
        # If data structure is not as expected, return empty fields
        pass
    return result
