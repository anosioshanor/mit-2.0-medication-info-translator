import re
import requests
from typing import Dict, Any

from services.utils import validate_medication_name


class RecallChecker:
    """
    Client for interacting with the openFDA Drug Enforcement API.

    Responsibilities:
    - Validate medication names.
    - Find ongoing recall records for the exact product or FDA-listed brand.
    - Avoid treating ingredient-level matches as product-specific recalls.
    """

    BASE_URL = "https://api.fda.gov/drug/enforcement.json"
    ALIASES = {"paracetamol": "acetaminophen"}

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "MedicationInformationTranslator/1.0"
        })

    def check_recall(self, medication_name: str) -> Dict[str, Any]:
        """
        Return only an ongoing recall that identifies the searched product/brand.

        Args:
            medication_name (str): Name of the medication to check.

        Returns:
            Dict[str, Any]: Recall information.
        """

        if not validate_medication_name(medication_name):
            raise ValueError(
                f"Invalid medication name: '{medication_name}'."
            )

        safe_name = medication_name.replace('"', '')
        search_name = self.ALIASES.get(safe_name.casefold(), safe_name)
        params = {
            "search": f'openfda.brand_name:"{search_name}" OR openfda.generic_name:"{search_name}"',
            "limit": 25
        }

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 404:
                return {"recalled": False}
            response.raise_for_status()

            data = response.json()

            query_name = self._normalize(medication_name)
            for recall in data.get("results", []):
                # Historical/terminated recalls should not be presented as current alerts.
                if str(recall.get("status", "")).casefold() != "ongoing":
                    continue

                openfda = recall.get("openfda", {})
                brand_names = [self._normalize(value) for value in openfda.get("brand_name", [])]
                generic_names = [self._normalize(value) for value in openfda.get("generic_name", [])]
                product = self._normalize(recall.get("product_description", ""))
                generic_query = self._normalize(search_name) in generic_names

                # Ingredient-only matches are too broad for lot-specific recalls.
                # Require the exact FDA-listed brand, or a full product phrase supplied by the user.
                brand_match = query_name in brand_names and not generic_query
                full_product_match = len(query_name.split()) >= 2 and query_name in product
                if not (brand_match or full_product_match):
                    continue

                return {
                    "recalled": True,
                    "reason": recall.get("reason_for_recall", "Recall reason not provided"),
                    "company": recall.get("recalling_firm", "Company not provided"),
                    "date": recall.get("report_date", "Date not provided"),
                    "status": recall.get("status", "Status not provided"),
                    "classification": recall.get("classification", "Classification not provided"),
                    "recall_number": recall.get("recall_number", ""),
                    "affected_batch": recall.get("code_info", ""),
                    "action": recall.get("more_code_info") or recall.get("initial_firm_notification", ""),
                    "product": recall.get("product_description", "Product description not provided"),
                    "source": "FDA Drug Enforcement database",
                }

            return {"recalled": False}

        except requests.exceptions.Timeout:
            return {
                "recalled": False,
                "error": "The FDA recall lookup timed out.",
            }

        except requests.exceptions.RequestException as e:
            return {
                "recalled": False,
                "error": f"The FDA recall lookup failed: {str(e)}",
            }

        except Exception as e:
            return {
                "recalled": False,
                "error": f"The FDA recall lookup failed: {str(e)}",
            }

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


if __name__ == "__main__":
    print("✅ Program started!")

    checker = RecallChecker()

    print("✅ RecallChecker object created!")

    drug = input("Enter medication name: ")

    try:
        result = checker.check_recall(drug)

        print("\nRecall Check Result\n")
        print("-" * 50)

        if result["recalled"]:
            print("⚠️ Recall Found!")
            print(f"Reason: {result['reason']}")
            print(f"Company: {result['company']}")
            print(f"Date: {result['date']}")
            print(f"Product: {result['product']}")
        # No message is printed when there is no matching ongoing product recall.

    except Exception as e:
        print("\nError:", e)
