import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional

from services.utils import format_drug_info, validate_medication_name, format_drug_info


class FDAClient:
    """
    Client for interacting with the openFDA Drug Label API.

    Responsibilities:
    - Validate medication names.
    - Retrieve medication information.
    - Format API responses.
    """

    BASE_URL = "https://api.fda.gov/drug/label.json"
    AUTOCOMPLETE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "MedicationInformationTranslator/1.0"
        })
        # openFDA can briefly drop requests or rate-limit bursts. Retry only
        # safe GET requests so a temporary service hiccup does not look like
        # a user connection problem.
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.35,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(("GET",)),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """
        Fetch medication information from the openFDA API.
        """

        if not validate_medication_name(drug_name):
            raise ValueError(
                f"Invalid medication name: '{drug_name}'."
            )

        # Handle common medication name differences
        drug_aliases = {
            "paracetamol": "acetaminophen"
        }

        search_name = drug_aliases.get(
            drug_name.lower(),
            drug_name
        )

        safe_name = search_name.replace('"', '')
        query = (
            f'openfda.brand_name:"{safe_name}" '
            f'OR openfda.generic_name:"{safe_name}"'
        )

        params = {
            "search": query,
            "limit": 1
        }

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

        except requests.exceptions.Timeout:
            raise ConnectionError(
                "Request timed out."
            )

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Could not connect to the openFDA API."
            )

        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise LookupError(
                    f"No FDA information found for '{drug_name}'."
                )

            raise Exception(
                f"HTTP Error: {e}"
            )

        except json.JSONDecodeError:
            raise Exception(
                "Invalid JSON received from the API."
            )

        if not data.get("results"):
            raise LookupError(
                f"No information found for '{drug_name}'."
            )

        extracted_info = format_drug_info(data)
        display_name = drug_name.title()
        openfda = data["results"][0].get("openfda", {})
        listed_names = []
        for field in ("brand_name", "generic_name"):
            for value in openfda.get(field, []):
                clean_value = " ".join(str(value).split()).strip()
                if clean_value and clean_value.casefold() not in {x.casefold() for x in listed_names}:
                    listed_names.append(clean_value)
        def first_values(*fields):
            values = []
            for field in fields:
                for value in openfda.get(field, []):
                    clean_value = " ".join(str(value).split()).strip()
                    if clean_value and clean_value.casefold() not in {x.casefold() for x in values}:
                        values.append(clean_value)
            return values
        label_context = {
            "generic_names": first_values("generic_name"),
            "active_ingredients": first_values("substance_name"),
            "brand_names": first_values("brand_name"),
            "categories": first_values("pharm_class_epc", "pharm_class_cs", "pharm_class_moa", "pharm_class_pe"),
        }

        return {
            "drug_name": drug_name,
            "display_name": display_name,
            "listed_names": listed_names,
            "label_context": label_context,
            "raw": data,
            "extracted": extracted_info
        }

    def suggest_drugs(self, query: str, limit: int = 8) -> list[str]:
        """Return label-backed name suggestions from openFDA for a partial query."""
        query = (query or "").strip()
        if len(query) < 2 or not validate_medication_name(query):
            return []
        if "paracetamol".startswith(query.casefold()):
            # This synonym is already an explicit, maintained mapping in this app.
            return ["Paracetamol"]
        safe = query.replace('"', '').replace("\\", "")
        # Prefix matching is supported by the openFDA search syntax. Both fields
        # come from a drug label record, so we do not invent brand/generic links.
        params = {
            "search": f'openfda.brand_name:{safe}* OR openfda.generic_name:{safe}*',
            "limit": min(max(limit, 1), 20),
        }
        try:
            response = self.session.get(self.AUTOCOMPLETE_URL, params=params, timeout=self.timeout)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            results = response.json().get("results", [])
            suggestions = []
            seen = set()
            for item in results:
                labels = item.get("openfda", {})
                for field in ("brand_name", "generic_name"):
                    for value in labels.get(field, []):
                        value = " ".join(str(value).split()).strip()
                        key = value.casefold()
                        if key.startswith(query.casefold()) and key not in seen:
                            seen.add(key)
                            suggestions.append(value.title())
            return suggestions[:limit]
        except requests.RequestException:
            return []

    def fetch_warnings_only(self, drug_name: str) -> Optional[str]:
        """
        Return only the warnings section.
        """

        try:
            result = self.fetch_drug_info(drug_name)
            return result["extracted"].get("warnings", "")

        except Exception:
            return None


# ----------------------------------------------------
# Test this module independently
# ----------------------------------------------------

if __name__ == "__main__":
    print("✅ Program started!")

    client = FDAClient()

    print("✅ FDAClient object created!")

    drug = input("Enter medication name: ")

    try:
        result = client.fetch_drug_info(drug)

        print("\nMedication Information\n")

        print(f"Drug: {result['drug_name']}")
        print("-" * 50)

        print("\nUsage:\n")
        print(result["extracted"]["usage"])

        print("\nWarnings:\n")
        print(result["extracted"]["warnings"])

        print("\nSide Effects:\n")
        print(result["extracted"]["side_effects"])

        print("\nInstructions:\n")
        print(result["extracted"]["instructions"])

    except Exception as e:
        print("\nError:", e)
