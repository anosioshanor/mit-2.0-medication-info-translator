"""Plain-language explanation and translation using the existing OpenRouter API."""

import os

import requests
import streamlit as st
from dotenv import load_dotenv


AI_REQUEST_LIMIT = 20
AI_RATE_LIMIT_MESSAGE = "You’ve reached the 20 AI and translation requests allowed in this session. You can continue in a new session."


class AITranslator:
    # Llama 3.2 3B repeatedly returned English for Yoruba, Igbo, and Hausa.
    # Gemini 3.1 Flash Lite returned target-language text in direct checks.
    MODEL = "google/gemini-3.1-flash-lite"

    def __init__(self):
        load_dotenv()
        self.api_key = self._setting("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = self._setting("OPENROUTER_MODEL") or self.MODEL

    @staticmethod
    def _setting(name: str) -> str | None:
        value = os.getenv(name)
        if value:
            return value
        try:
            return st.secrets.get(name)
        except Exception:
            return None

    @staticmethod
    def _reserve_request_slot() -> bool:
        try:
            used = int(st.session_state.get("mit_ai_requests_used", 0))
        except (TypeError, ValueError):
            used = 0
        if used >= AI_REQUEST_LIMIT:
            return False
        try:
            st.session_state["mit_ai_requests_used"] = used + 1
        except Exception:
            # Keep direct, non-Streamlit uses of the translator functional.
            pass
        return True

    def explain(self, medication_data: dict, language: str = "English") -> str:
        if not self.api_key:
            return "AI service unavailable: add OPENROUTER_API_KEY to your .env file to generate an explanation."

        info = medication_data.get("extracted", {})
        name = medication_data.get("display_name") or medication_data.get("drug_name", "the medication")
        fields = [
            ("Uses", info.get("usage")),
            ("Dosage and administration", info.get("instructions")),
            ("Warnings", info.get("warnings")),
            ("Side effects", info.get("side_effects")),
            ("Contraindications", info.get("contraindications")),
            ("Precautions", info.get("precautions")),
        ]
        source_text = "\n".join(f"{label}: {value}" for label, value in fields if value)
        if not source_text:
            return "AI service unavailable: the FDA label did not provide information to explain."

        language_instruction = (
            "Write the entire response in English."
            if language == "English"
            else f"Write the entire response in {language}, in natural everyday language. Do not answer in English or include English headings. Keep medicine names, dose numbers, units, and unavoidable technical names unchanged."
        )
        prompt = f"""Explain this FDA drug label information about {name} for a general reader.

{language_instruction}
Only use facts contained in the source text. Do not add a dose, diagnosis, treatment advice, or unsupported claims. Preserve the medication name, all dose numbers, units, strengths, timings, and safety qualifiers exactly. If the source is unclear or has no dosage information, say so. Clearly explain important warnings without minimizing them. Use a short summary followed by a few plain-language points. End with a brief reminder that this explanation is not a substitute for a pharmacist or clinician, written in the requested language.

FDA label source text:
{source_text}"""

        try:
            if not self._reserve_request_slot():
                return AI_RATE_LIMIT_MESSAGE
            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 700, "temperature": 0.1},
                timeout=45,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                return "AI service unavailable: the explanation service returned an empty response."
            return content.strip()
        except requests.HTTPError as error:
            return self._http_error(error, "explanation")
        except requests.RequestException:
            return "AI service unavailable: the explanation service could not be reached. Please try again later."
        except (KeyError, IndexError, TypeError, ValueError):
            return "AI service unavailable: the explanation service returned an invalid response."

    def answer_follow_up(self, medication_data: dict, question: str) -> str:
        """Answer a contextual question using only the same FDA label fields as the explanation."""
        if not self.api_key:
            return "AI service unavailable: add OPENROUTER_API_KEY to your .env file to ask a follow-up question."
        info = medication_data.get("extracted", {})
        name = medication_data.get("display_name") or medication_data.get("drug_name", "the medication")
        fields = [
            ("Uses", info.get("usage")),
            ("Dosage and administration", info.get("instructions")),
            ("Warnings", info.get("warnings")),
            ("Contraindications", info.get("contraindications")),
            ("Precautions", info.get("precautions")),
            ("Drug interactions", info.get("interactions")),
            ("Overdosage", info.get("overdosage")),
        ]
        source_text = "\n".join(f"{label}: {value}" for label, value in fields if value)
        if not source_text:
            return "AI service unavailable: the FDA label did not provide information to answer this question."
        prompt = f"""Answer this medication question about {name}: {question}

Use only facts in the FDA label text below. If the label does not answer the question, say that it does not specify and advise checking the product label or asking a pharmacist/clinician. Do not invent a dose, diagnosis, or treatment instruction. Keep the answer brief and plain-language. This is educational information, not medical advice.

FDA label:
{source_text}"""
        try:
            if not self._reserve_request_slot():
                return AI_RATE_LIMIT_MESSAGE
            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0.1},
                timeout=45,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                return "AI service unavailable: the explanation service returned an empty response."
            return content.strip()
        except requests.HTTPError as error:
            return self._http_error(error, "follow-up")
        except requests.RequestException:
            return "AI service unavailable: the explanation service could not be reached. Please try again later."
        except (KeyError, IndexError, TypeError, ValueError):
            return "AI service unavailable: the explanation service returned an invalid response."

    def translate(self, medical_text: str) -> str:
        """Keep the historical method name; translate raw text to plain English."""
        return self._request(medical_text, "English")

    def _request(self, text: str, language: str) -> str:
        if not self.api_key:
            return "AI service unavailable: add OPENROUTER_API_KEY to your .env file."
        try:
            if not self._reserve_request_slot():
                return AI_RATE_LIMIT_MESSAGE
            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": f"Rewrite this medication information in {language} using plain language. Preserve every medication name, number, dose, unit, and safety fact. Do not add facts.\n\n{text}"}],
                    "max_tokens": 700,
                    "temperature": 0.1,
                },
                timeout=45,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.HTTPError as error:
            return self._http_error(error, "translation")
        except requests.RequestException:
            return "AI service unavailable: the translation service could not be reached. Please try again later."
        except (KeyError, IndexError, TypeError, ValueError):
            return "AI service unavailable: the translation service returned an invalid response."

    @staticmethod
    def _http_error(error: requests.HTTPError, feature: str) -> str:
        status = getattr(error.response, "status_code", None)
        if status in (401, 403):
            detail = "OpenRouter rejected the API key. Check OPENROUTER_API_KEY in .env."
        elif status == 402:
            detail = "OpenRouter needs credits for this model. Check your OpenRouter balance."
        elif status == 404:
            detail = "The configured OpenRouter model is unavailable. Check OPENROUTER_MODEL."
        elif status == 429:
            detail = "OpenRouter rate limit reached. Wait briefly, then try again."
        else:
            detail = f"OpenRouter returned HTTP {status or 'error'}. Please try again later."
        return f"AI service unavailable: {feature} request failed. {detail}"
