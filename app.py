"""Medication Information Translator (MIT 2.0) Streamlit application."""

from __future__ import annotations

import difflib
import html
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import streamlit as st

from services.ai_translator import AITranslator, AI_RATE_LIMIT_MESSAGE
from services.fda_client import FDAClient
from services.recall_checker import RecallChecker
from services.search_history import clear_history, load_history, save_search
from services.saved_medications import add_saved, is_saved, load_saved, remove_saved


ROOT = Path(__file__).resolve().parent

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#F4F8F7; --muted:#A8B8BC; --green:#86E4C3; --lime:#86E4C3; --paper:#0B1118; --line:#2D3E4D; --panel:#151F2B; --panel2:#1B2835; --surface-strong:#223241; --green-deep:#1A3A30; --amber:#F6C86E; --coral:#FF817A; --blue:#8AB9FF; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
.stApp { background:var(--paper); }
header[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1120px; padding-top:1.8rem; padding-bottom:5rem; }
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,.stApp [data-testid="stSubheader"] { font-family:'Manrope',sans-serif; letter-spacing:-.035em; color:var(--ink)!important; }
h1 { font-size:clamp(2rem,5vw,3.5rem)!important; line-height:1.08!important; }
h2 { font-size:1.65rem!important; }
p, li { line-height:1.6; }
section[data-testid="stSidebar"] { background:#0B1118; border-right:1px solid #2D3E4D; min-width:225px; width:225px; }
section[data-testid="stSidebar"] > div { padding:1rem .85rem; }
section[data-testid="stSidebar"] [data-testid="stButton"] button { text-align:left; background:transparent; border-color:transparent; color:#A8B8BC; justify-content:flex-start; }
section[data-testid="stSidebar"] [data-testid="stButton"] button:hover { background:#1A3A30; color:var(--green); }
div[data-testid="stTextInput"] input { background:#1B2835; color:var(--ink); border:1px solid #2D3E4D; border-radius:13px; min-height:3.25rem; }
div[data-testid="stTextInput"] input::placeholder { color:var(--muted); opacity:1; }
div.stButton > button { background:#223241; color:var(--ink); border-radius:12px; min-height:2.85rem; font-weight:700; border:1px solid var(--line); }
div[data-testid="stButton"] button[kind="secondary"] { background:#223241!important; color:var(--ink)!important; border-color:var(--line)!important; }
div[data-testid="stButton"] button[kind="primary"] { background:var(--green)!important; border-color:var(--green)!important; color:#08271E!important; }
div[data-testid="stButton"] button:hover { border-color:var(--green)!important; color:var(--green)!important; }
.stApp .card,.stApp .card-title,.stApp .alert,.stApp .notice,.stApp .ai-box,.stApp .translate-box,.stApp .safety-box,.stApp .source-note,.stApp .recall-step { color:var(--ink)!important; }
[data-testid="stRadio"] > div { gap:.4rem; }
[data-testid="stRadio"] label { background:#151F2B; border:1px solid var(--line); border-radius:999px; padding:.4rem .8rem; color:var(--ink); }
.mit-brand { display:flex; align-items:center; gap:9px; color:#F4F8F7; font-family:Manrope,sans-serif; font-weight:800; letter-spacing:-.03em; line-height:1.1; }
.mit-brand small { color:var(--muted); font:400 .65rem 'DM Sans',sans-serif; letter-spacing:0; display:block; margin-top:3px; }
.mit-mark { width:35px;height:35px;border-radius:50%;background:#86E4C3;display:grid;place-items:center;color:#08271E;font-size:21px; flex:none; }
.mit-topbrand { display:none; }
.eyebrow { display:inline-block; color:#86E4C3; background:#1A3A30; border:1px solid #315F50; border-radius:99px; padding:.3rem .7rem; font-weight:600; font-size:.78rem; }
.subtle { color:var(--muted); }
.hero { background:transparent; border:0; border-radius:0; padding:1.5rem 0 .5rem; margin:1rem 0 1.2rem; }
.hero h1 { max-width:560px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:15px; padding:1.05rem 1.15rem; height:100%; }
.card-title { font-family:Manrope,sans-serif; font-weight:800; font-size:1rem; margin-bottom:.5rem; color:var(--ink); }
.alert { background:#351E22; border:1px solid #FF817A; border-left:5px solid #FF817A; border-radius:14px; padding:1rem 1.15rem; color:#F4F8F7; }
.notice { background:#163229; border:1px solid #315F50; border-radius:14px; padding:.9rem 1.1rem; color:#F4F8F7; }
.st-key-home_actions { padding-top:1rem; }
.ai-box { background:#17283E; border:1px solid #8AB9FF; border-radius:14px; padding:1rem 1.1rem; color:#F4F8F7; }
.translate-box { background:#17283E; border:1px solid #2D3E4D; border-radius:14px; padding:.9rem 1.1rem; color:#F4F8F7; }
.safety-box { background:#332B1A; border:1px solid #6D5626; border-left:4px solid #F6C86E; border-radius:14px; padding:.9rem 1.1rem; color:#F4F8F7; }
.recall-step { background:#151F2B; border:1px solid #2D3E4D; border-radius:14px; padding:1rem; height:100%; }
.source-note { background:#17283E; border-left:4px solid #8AB9FF; border-radius:12px; padding:.85rem 1rem; color:#F4F8F7; }
.pill { display:inline-block; padding:.35rem .7rem; border-radius:99px; background:#1A3A30; color:var(--green); border:1px solid #315F50; font-size:.8rem; font-weight:700; }
.stCaption { color:var(--muted); }
hr { border-color:#2D3E4D!important; }
div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--line); border-radius:12px; }
.history-day { margin:.5rem 0 .85rem; color:var(--muted); font-size:.82rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
.speech-controls { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin:.5rem 0; }
.speech-controls button,.speech-controls select { font:inherit; min-height:44px; border-radius:10px; padding:.65rem .85rem; }
.speech-controls button { background:#223241; color:#F4F8F7; border:1px solid #2D3E4D; cursor:pointer; }
.speech-controls button[data-speech="play"] { background:#86E4C3; color:#08271E; border-color:#86E4C3; font-weight:700; }
.speech-controls select { background:#1B2835; color:#F4F8F7; border:1px solid #2D3E4D; }
@media(max-width:700px) {
 section[data-testid="stSidebar"] { display:none; }
 .block-container { padding:1rem 1rem 7rem!important; }
 .mit-topbrand { display:flex; }
 .st-key-mobile_nav { position:fixed; z-index:999; bottom:0; left:0; right:0; padding:.35rem .5rem calc(.35rem + env(safe-area-inset-bottom)); background:#0E1620; border-top:1px solid #2D3E4D; }
 .st-key-mobile_nav [data-testid="stHorizontalBlock"] { display:flex!important; flex-wrap:nowrap!important; gap:0!important; }
 .st-key-mobile_nav [data-testid="stColumn"] { flex:1 1 50%!important; width:50%!important; min-width:0!important; padding:0 .2rem; }
 .st-key-mobile_nav [data-testid="stButton"] button { width:100%; min-height:3rem; border-radius:10px; }
 .st-key-mobile_nav [data-testid="stButton"] button[kind="secondary"] { background:transparent!important; border-color:transparent!important; color:var(--muted)!important; }
 .st-key-result_tab [data-testid="stRadio"] > div { justify-content:space-between; gap:.2rem; overflow-x:auto; }
 .st-key-result_tab [data-testid="stRadio"] label { padding:.35rem .5rem; font-size:.75rem; white-space:nowrap; }
 .hero { border-radius:0; }
 div[data-testid="stHorizontalBlock"] { gap:.65rem; }
 div.stButton > button { min-height:3rem; }
}
@media(min-width:701px) { .st-key-mobile_nav { display:none; } }
</style>
"""


def ai_response_is_error(message: str) -> bool:
    return message.startswith("AI service unavailable") or message == AI_RATE_LIMIT_MESSAGE


def show_ai_response_error(message: str) -> bool:
    if message == AI_RATE_LIMIT_MESSAGE:
        st.info(message)
        return True
    if message.startswith("AI service unavailable"):
        st.error(message)
        return True
    return False


def services():
    return FDAClient(), RecallChecker(), AITranslator()


def set_view(view: str, *, tab: str | None = None):
    st.session_state.view = view
    st.session_state.pending_mobile_nav = {"result": "Home", "recall": "Home", "home": "Home", "saved": "Saved"}.get(view, "Home")
    if tab:
        st.session_state.result_tab = tab


def set_medication(name: str, data: dict | None = None):
    st.session_state.medication_name = name
    st.session_state.medication_data = data
    st.session_state.pop("recall_acknowledged_for", None)
    st.session_state.pending_mobile_nav = "Home"
    st.session_state.view = "recall" if data and data.get("recall", {}).get("recalled") else "result"
    st.session_state.result_tab = "Quick summary"


def switch_result_tab(tab: str):
    """Queue tab changes for the next run before Streamlit builds the radio widget."""
    st.session_state.pending_result_tab = tab


def clear_widget_value(key: str):
    """Clear an existing widget value from its Streamlit pre-run callback."""
    st.session_state[key] = ""


def format_history_time(value: str) -> tuple[str, str]:
    """Return a day group and readable local timestamp without rejecting old entries."""
    try:
        parsed = datetime.fromisoformat(str(value))
        day = parsed.date()
        group = "Today" if day == date.today() else "Earlier"
        return group, parsed.strftime("%H:%M · %d %b")
    except (TypeError, ValueError):
        return "Earlier", str(value)[:16]


def card(title: str, body: str, marker: str = ""):
    marker_html = f'<span class="pill">{html.escape(marker)}</span>' if marker else ""
    st.markdown(
        f'<div class="card"><div class="card-title">{html.escape(title)} {marker_html}</div>'
        f'<div>{body or "This information is not present in the available FDA label."}</div></div>',
        unsafe_allow_html=True,
    )


def get_suggestions(query: str) -> list[str]:
    cache = st.session_state.setdefault("suggestion_cache", {})
    if query not in cache:
        cache[query] = FDAClient(timeout=4).suggest_drugs(query)
    return cache[query]


def load_medication(name: str) -> dict:
    client, recall_checker, _ = services()
    data = client.fetch_drug_info(name)
    data["recall"] = recall_checker.check_recall(name)
    save_search(name)
    st.session_state.ai_explanations = st.session_state.get("ai_explanations", {})
    return data


def explain_if_requested(data: dict, language: str = "English") -> str:
    translator = AITranslator()
    name = st.session_state.medication_name
    cached = st.session_state.get("ai_explanations", {})
    cache_key = f"{name.casefold()}::{language}::{translator.model}"
    if cache_key not in cached:
        explanation = translator.explain(data, language=language)
        if ai_response_is_error(explanation):
            return explanation
        cached[cache_key] = explanation
        st.session_state.ai_explanations = cached
    return cached[cache_key]


def get_cached_explanation(name: str, language: str) -> str | None:
    """Avoid reusing English-only results cached from an older model."""
    model = AITranslator().model
    return st.session_state.get("ai_explanations", {}).get(f"{name.casefold()}::{language}::{model}")


def contextual_follow_up_prompts(info: dict) -> list[tuple[str, str]]:
    """Offer only questions connected to topics present in this FDA label."""
    instructions = str(info.get("instructions", ""))
    safety_text = " ".join(str(info.get(key, "")) for key in ("warnings", "precautions", "contraindications", "interactions"))
    prompts = []
    if re.search(r"\b(food|meal|eat|with or without|empty stomach)\b", instructions + " " + safety_text, re.I):
        prompts.append(("Can I take it with food?", "followup_food"))
    if re.search(r"\b(child|children|pediatric|paediatric)\b", instructions, re.I):
        prompts.append(("Explain child dosing", "followup_child_dosing"))
    if info.get("overdosage"):
        prompts.append(("What does the label say about overdose?", "followup_overdose"))
    if not prompts and (info.get("warnings") or info.get("contraindications") or info.get("precautions")):
        prompts.append(("What cautions should I check?", "followup_cautions"))
    return prompts


def render_recall(data: dict):
    recall = data.get("recall", {})
    if not recall.get("recalled"):
        return
    st.title("Medication safety alert")
    st.caption("This alert applies only to the product and batch listed in the FDA record.")
    st.markdown(
        f"<div class='alert'><strong>Recall alert</strong><br>"
        f"<b>Product:</b> {html.escape(str(recall.get('product') or 'Product not specified'))}<br>"
        f"<b>Affected batch / code:</b> {html.escape(str(recall.get('affected_batch') or 'Not specified in this FDA record'))}<br>"
        f"<b>Reason:</b> {html.escape(str(recall.get('reason') or 'Reason not provided'))}<br>"
        f"<b>Company:</b> {html.escape(str(recall.get('company') or 'Company not provided'))} | "
        f"<b>Date:</b> {html.escape(str(recall.get('date') or 'Date not provided'))}<br>"
        f"<b>Status:</b> {html.escape(str(recall.get('status') or 'Status not provided'))} | "
        f"<b>Class:</b> {html.escape(str(recall.get('classification') or 'Not provided'))}</div>", unsafe_allow_html=True)

    st.subheader("Check the product and batch on your pack")
    action = str(recall.get("action") or "").strip()
    if action:
        st.markdown(
            f"<div class='safety-box'><b>FDA recall instructions</b><br>{html.escape(action)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("This FDA record does not include next-step instructions. Contact a pharmacist or the manufacturer for guidance before deciding what to do.")
    st.caption("Check the product name and batch/code above against the packaging. The alert may not apply to other products or batches.")

    action_lower = action.casefold()
    stop_guidance = any(term in action_lower for term in ("stop using", "do not use", "discontinue", "quarantine", "separate", "return the product"))
    step_a, step_b, step_c = st.columns(3)
    with step_a:
        if stop_guidance:
            st.markdown(f"<div class='recall-step'><b>1. Stop and separate</b><p>{html.escape(action)}</p></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='recall-step'><b>1. Check the affected batch</b><p>Compare the product and batch on your pack with the FDA record above. Follow any instructions included in that record.</p></div>", unsafe_allow_html=True)
    with step_b:
        st.markdown("<div class='recall-step'><b>2. Contact a pharmacist</b><p>A pharmacist can help you understand the notice and what to do next.</p></div>", unsafe_allow_html=True)
    with step_c:
        st.markdown("<div class='recall-step'><b>3. Get help if unwell</b><p>If you feel unwell after using this product, contact a health professional. For severe symptoms or suspected overdose, seek urgent medical care.</p></div>", unsafe_allow_html=True)

    source = str(recall.get("source") or "FDA Drug Enforcement database")
    recall_number = recall.get("recall_number")
    suffix = f" | Recall {html.escape(str(recall_number))}" if recall_number else ""
    st.caption(f"Source: {source}{suffix}. No official notice link is available in the returned record.")
    left, right = st.columns(2)
    with left:
        if st.button("Back to Home", key="recall_home"):
            set_view("home")
            st.rerun()
    with right:
        if st.button("View medication information", key="recall_view_info", type="primary"):
            st.session_state.recall_acknowledged_for = st.session_state.medication_name.casefold()
            set_view("result")
            st.rerun()

def render_result():
    name = st.session_state.get("medication_name", "")
    data = st.session_state.get("medication_data")
    if not name:
        st.session_state.view = "home"
        st.rerun()
    if data is None:
        try:
            with st.spinner(f"Finding official information for {name}…"):
                data = load_medication(name)
                st.session_state.medication_data = data
        except Exception as error:
            if isinstance(error, LookupError):
                st.error(f"No FDA label information is available for {name} right now. Try another medication name or search again later.")
            elif isinstance(error, ConnectionError):
                st.error("We couldn’t reach the FDA medication information service. Check your connection and try again.")
            else:
                st.error("We couldn’t load this medication information. Please try again in a moment.")
            if st.button("Back to search", type="primary"):
                set_view("home")
                st.rerun()
            return

    if data.get("recall", {}).get("recalled") and st.session_state.get("recall_acknowledged_for") != name.casefold():
        st.session_state.view = "recall"
        st.session_state.pending_mobile_nav = "Home"
        st.rerun()

    info = data.get("extracted", {})
    display_name = data.get("display_name") or name.title()
    st.markdown(f"<span class='eyebrow'>Medication information</span>", unsafe_allow_html=True)
    st.title(display_name)
    label_context = data.get("label_context", {})
    ingredients = label_context.get("active_ingredients") or label_context.get("generic_names", [])
    if ingredients:
        st.caption("Active ingredient(s) listed by FDA: " + ", ".join(html.escape(item) for item in ingredients[:5]))
    categories = label_context.get("categories", [])
    if categories:
        st.markdown(" ".join(f"<span class='pill'>{html.escape(item)}</span>" for item in categories[:3]), unsafe_allow_html=True)
    other_listed_names = [item for item in data.get("listed_names", []) if item.casefold() != name.casefold()]
    if other_listed_names:
        st.caption("Other names listed on this FDA label: " + ", ".join(html.escape(item) for item in other_listed_names[:5]))
    st.caption("Based on information available in the FDA drug label. Labels can vary by product and strength.")
    col_a, col_b = st.columns([4, 1])
    with col_a:
        if st.button("← Back to Home", key="result_home"):
            set_view("home")
            st.rerun()
    with col_b:
        saved = is_saved(name)
        if st.button("♥ Saved" if saved else "♡ Save", key="save_result", use_container_width=True):
            if saved:
                remove_saved(name)
            else:
                add_saved(name)
            st.rerun()

    # Streamlit locks a widget's keyed state once it has been instantiated in a run.
    # Buttons below the radio queue a change for the next run, then apply it here.
    pending_tab = st.session_state.pop("pending_result_tab", None)
    if pending_tab:
        st.session_state.result_tab = pending_tab
    tabs = ["Quick summary", "Full information", "AI explanation", "Translation", "Listen"]
    selected = st.radio("Information view", tabs, horizontal=True, key="result_tab", label_visibility="collapsed")
    st.divider()
    if selected == "Quick summary":
        st.subheader("Quick Summary")
        st.caption("Based on the FDA label for this medication. Follow the directions on your exact product.")
        first, second = st.columns(2)
        with first:
            card("What it is used for", html.escape(info.get("usage", "")), "FDA LABEL")
        with second:
            card("Dose basics", html.escape(info.get("instructions", "")), "FDA LABEL")
        third, fourth = st.columns(2)
        with third:
            card("Important cautions", html.escape(info.get("warnings", "")), "FDA LABEL")
        with fourth:
            card("Possible side effects", html.escape(info.get("side_effects", "")), "FDA LABEL")
        if info.get("available_forms"):
            st.caption("Dosage forms and strengths in the FDA label: " + html.escape(info["available_forms"]))
        if info.get("overdosage"):
            st.markdown(
                f"<div class='safety-box'><b>Overdosage information in the FDA label</b><br>{html.escape(info['overdosage'])}</div>",
                unsafe_allow_html=True,
            )
        st.caption("Information, not diagnosis. Ask a pharmacist or clinician if you are unsure how the label applies to you.")
        action_cols = st.columns(4)
        for col, label, tab_name, key in (
            (action_cols[0], "Full Information", "Full information", "summary_full"),
            (action_cols[1], "Explain with AI", "AI explanation", "summary_ai"),
            (action_cols[2], "Translate", "Translation", "summary_translate"),
            (action_cols[3], "Listen", "Listen", "summary_listen"),
        ):
            with col:
                if st.button(label, key=key, use_container_width=True, type="primary" if tab_name == "Full information" else "secondary"):
                    switch_result_tab(tab_name)
                    st.rerun()
    elif selected == "Full information":
        st.subheader("Full medication information")
        section = st.radio(
            "Information section",
            ["Overview", "How to take", "Safety", "Side effects", "Sources"],
            horizontal=True,
            key="full_info_section",
            label_visibility="collapsed",
        )
        fields = {
            "Overview": [("usage", "What the FDA label says it is used for"), ("other_information", "Other label information")],
            "How to take": [("instructions", "Dosage and administration"), ("available_forms", "Dosage forms and strengths")],
            "Safety": [("warnings", "Warnings"), ("contraindications", "Contraindications"), ("precautions", "Precautions"), ("interactions", "Drug interactions"), ("overdosage", "Overdosage information")],
            "Side effects": [("side_effects", "Adverse reactions")],
        }
        if section == "Sources":
            st.markdown("<div class='source-note'><b>Source</b><br>Information on this page comes from the FDA drug label API.</div>", unsafe_allow_html=True)
            results = (data.get("raw") or {}).get("results") or []
            record = results[0] if results else {}
            openfda = record.get("openfda", {})
            metadata = []
            if record.get("effective_time"):
                metadata.append(("FDA label effective date", record["effective_time"]))
            for key, label in (("manufacturer_name", "Manufacturer"), ("product_ndc", "Product NDC"), ("brand_name", "Brand name"), ("generic_name", "Generic name")):
                value = openfda.get(key)
                if value:
                    metadata.append((label, ", ".join(str(item) for item in value[:3]) if isinstance(value, list) else str(value)))
            for label, value in metadata:
                st.write(f"**{label}:** {value}")
            if not metadata:
                st.info("No additional source metadata was included in the available FDA record.")
        else:
            shown = False
            for key, title in fields[section]:
                value = info.get(key)
                if value:
                    st.markdown(f"#### {title}")
                    st.write(value)
                    shown = True
            if not shown:
                st.info("This section is not included in the available FDA label.")
        st.caption("FDA labels can vary by product, strength, and formulation. Check the label for the product you have.")
    elif selected == "AI explanation":
        st.subheader("In simple terms")
        st.markdown("<div class='ai-box'><b>Safety note</b><br>AI can help explain the FDA label. It cannot diagnose or replace advice from a pharmacist or clinician.</div>", unsafe_allow_html=True)
        explanation = get_cached_explanation(name, "English")
        if explanation:
            formatted_explanation = html.escape(explanation).replace("\n", "<br>")
            st.markdown(f"<div class='ai-box'><b>TL;DR</b><br>{formatted_explanation}</div>", unsafe_allow_html=True)
        elif st.button("Explain this information", type="primary"):
            with st.spinner("Preparing a plain-language explanation..."):
                explanation = explain_if_requested(data)
            if not show_ai_response_error(explanation):
                st.rerun()
        if explanation and not ai_response_is_error(explanation) and st.button("Listen to explanation", key="ai_listen"):
            st.session_state.listen_language = "English"
            switch_result_tab("Listen")
            st.rerun()

        prompts = contextual_follow_up_prompts(info)
        if prompts:
            st.markdown("#### Questions you may want to ask")
            answers = st.session_state.setdefault("follow_up_answers", {})
            answer_cols = st.columns(len(prompts))
            for col, (question, key) in zip(answer_cols, prompts):
                with col:
                    if st.button(question, key=key, use_container_width=True):
                        with st.spinner("Checking the FDA label..."):
                            answer = AITranslator().answer_follow_up(data, question)
                        if not show_ai_response_error(answer):
                            answers[f"{name.casefold()}::{question}"] = answer
            for question, _ in prompts:
                answer = answers.get(f"{name.casefold()}::{question}")
                if answer:
                    formatted_answer = html.escape(answer).replace("\n", "<br>")
                    st.markdown(f"<div class='source-note'><b>{html.escape(question)}</b><br>{formatted_answer}</div>", unsafe_allow_html=True)
    elif selected == "Translation":
        st.subheader("Understand it in your language")
        language = st.selectbox("Choose a language", ["English", "Nigerian Pidgin", "Yoruba", "Igbo", "Hausa"], key="translation_language")
        source_fields = [("Uses", info.get("usage")), ("Dosage and administration", info.get("instructions")), ("Warnings", info.get("warnings"))]
        with st.expander("English source information from the FDA label"):
            found_source = False
            for label, value in source_fields:
                if value:
                    st.markdown(f"**{label}**")
                    st.write(value)
                    found_source = True
            if not found_source:
                st.info("The FDA label did not include these summary fields.")

        if language == "English":
            translated = get_cached_explanation(name, "English")
            if not translated:
                st.info("Generate the plain-language explanation first.")
                if st.button("Generate English explanation", type="primary"):
                    with st.spinner("Preparing the explanation..."):
                        translated = explain_if_requested(data)
                    if not show_ai_response_error(translated):
                        st.rerun()
            else:
                formatted_translation = html.escape(translated).replace("\n", "<br>")
                st.markdown(f"<div class='translate-box'><b>English explanation</b><br>{formatted_translation}</div>", unsafe_allow_html=True)
        else:
            translated = get_cached_explanation(name, language)
            if translated:
                formatted_translation = html.escape(translated).replace("\n", "<br>")
                st.markdown(f"<div class='translate-box'><b>{html.escape(language)}</b><br>{formatted_translation}</div>", unsafe_allow_html=True)
                if st.button(f"Listen in {language}", key="listen_translation", use_container_width=True):
                    st.session_state.listen_language = language
                    switch_result_tab("Listen")
                    st.rerun()
            elif st.button(f"Translate to {language}", type="primary"):
                with st.spinner(f"Preparing the explanation in {language}..."):
                    translated = explain_if_requested(data, language)
                if not show_ai_response_error(translated):
                    st.rerun()
        st.markdown("<div class='source-note'><b>Translation note</b><br>Medication names and dose numbers are kept where possible. Check critical details against the original product label; device speech voices may not pronounce every language naturally.</div>", unsafe_allow_html=True)
    else:
        st.subheader("Listen to the explanation")
        language = st.selectbox("Spoken language", ["English", "Nigerian Pidgin", "Yoruba", "Igbo", "Hausa"], key="listen_language")
        explanation = get_cached_explanation(name, language)
        if not explanation and language == "English":
            explanation = get_cached_explanation(name, "English")
        if not explanation:
            st.info("Generate an explanation in this language first.")
            if st.button("Generate explanation", type="primary"):
                with st.spinner("Preparing the explanation..."):
                    explanation = explain_if_requested(data, language)
                if not show_ai_response_error(explanation):
                    st.rerun()
        else:
            speech_lang = {"English": "en-NG", "Nigerian Pidgin": "en-NG", "Yoruba": "yo-NG", "Igbo": "ig-NG", "Hausa": "ha-NG"}.get(language, "en-NG")
            js_text = json.dumps(explanation).replace("</", "<\\/")
            st.iframe(f"""<!doctype html><html><head><meta charset="utf-8"><style>
              * {{ box-sizing:border-box; }}
              html,body {{ margin:0; background:transparent; color:#F4F8F7; font:16px Arial,sans-serif; }}
              #mit-speech-player {{ padding:8px 4px; }}
              .speech-controls {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
              .speech-controls button,.speech-controls select {{ font:inherit; min-height:44px; border-radius:10px; padding:9px 12px; }}
              .speech-controls button {{ background:#223241; color:#F4F8F7; border:1px solid #2D3E4D; cursor:pointer; }}
              .speech-controls button[data-speech="play"] {{ background:#86E4C3; color:#08271E; border-color:#86E4C3; font-weight:700; }}
              .speech-controls select {{ background:#1B2835; color:#F4F8F7; border:1px solid #2D3E4D; }}
              .speech-controls label {{ display:flex; align-items:center; gap:6px; }}
              [data-speech="status"] {{ color:#A8B8BC; line-height:1.5; margin:8px 0 0; }}
              @media(max-width:520px) {{ .speech-controls {{ gap:6px; }} .speech-controls button {{ padding:8px 9px; }} }}
            </style></head><body><div id="mit-speech-player">
              <div class="speech-controls" aria-label="Speech playback controls">
                <button data-speech="play" aria-label="Play explanation">Listen</button>
                <button data-speech="pause" aria-label="Pause or resume playback">Pause / resume</button>
                <button data-speech="stop" aria-label="Stop playback">Stop</button>
                <button data-speech="restart" aria-label="Restart playback">Restart</button>
                <label>Speed <select data-speech="speed" aria-label="Playback speed"><option value="0.8">0.8x</option><option value="1" selected>1x</option><option value="1.2">1.2x</option></select></label>
                <label>Voice <select data-speech="voice" aria-label="Speech voice"><option value="">Best available</option></select></label>
              </div>
              <p data-speech="status" role="status" aria-live="polite" style="color:#A8B8BC">Ready to read this explanation aloud.</p>
              <script>
                (() => {{
                  // Streamlit may commit the HTML container just after running
                  // its inline script. Retry briefly so controls always bind.
                  const bindPlayer = () => {{
                  const player = document.getElementById("mit-speech-player");
                  if (!player) {{ window.setTimeout(bindPlayer, 50); return; }}
                  if (player.dataset.bound === "true") return;
                  player.dataset.bound = "true";
                  const text = {js_text};
                  const requestedLang = {json.dumps(speech_lang)};
                  const languageName = {json.dumps(language)};
                  const status = player.querySelector('[data-speech="status"]');
                  const synth = window.speechSynthesis;
                  const voiceSelect = player.querySelector('[data-speech="voice"]');
                  const speedSelect = player.querySelector('[data-speech="speed"]');
                  const populateVoices = () => {{
                    if (!synth || !voiceSelect) return;
                    const previous = voiceSelect.value;
                    voiceSelect.innerHTML = '<option value="">Best available</option>';
                    synth.getVoices().forEach((voice, index) => {{
                      const option = document.createElement("option");
                      option.value = String(index);
                      option.textContent = `${{voice.name}} (${{voice.lang}})`;
                      voiceSelect.appendChild(option);
                    }});
                    if ([...voiceSelect.options].some(option => option.value === previous)) voiceSelect.value = previous;
                  }};
                  if (synth) {{ populateVoices(); synth.onvoiceschanged = populateVoices; }}
                  const play = () => {{
                    if (!synth || !window.SpeechSynthesisUtterance) {{
                      status.textContent = "Speech playback is not supported in this browser. The explanation text is available below.";
                      return;
                    }}
                    synth.cancel();
                    const utterance = new SpeechSynthesisUtterance(text);
                    const primaryLang = requestedLang.split("-")[0].toLowerCase();
                    const voices = synth.getVoices();
                    const chosenIndex = voiceSelect && voiceSelect.value ? Number(voiceSelect.value) : -1;
                    const voice = voices[chosenIndex] || voices.find(v => v.lang.toLowerCase().replace("_", "-").startsWith(primaryLang + "-")) || voices.find(v => v.lang.toLowerCase() === primaryLang);
                    utterance.rate = Number(speedSelect.value || 1);
                    if (voice) {{ utterance.voice = voice; utterance.lang = voice.lang; }}
                    else {{ utterance.lang = primaryLang === "en" ? "en-US" : requestedLang; }}
                    status.textContent = `Starting ${{languageName}} playback...`;
                    utterance.onstart = () => {{ status.textContent = "Playing explanation..."; }};
                    utterance.onend = () => {{ status.textContent = "Playback finished."; }};
                    utterance.onerror = event => {{ status.textContent = `Playback failed (${{event.error || "unknown error"}}). Check device volume and browser speech support.`; }};
                    synth.speak(utterance);
                  }};
                  player.querySelector('[data-speech="play"]').addEventListener("click", play);
                  player.querySelector('[data-speech="restart"]').addEventListener("click", play);
                  player.querySelector('[data-speech="pause"]').addEventListener("click", () => {{
                    if (!synth) return;
                    if (synth.paused) {{ synth.resume(); status.textContent = "Playback resumed."; }}
                    else if (synth.speaking) {{ synth.pause(); status.textContent = "Playback paused."; }}
                    else {{ status.textContent = "Press Listen to start playback first."; }}
                  }});
                  player.querySelector('[data-speech="stop"]').addEventListener("click", () => {{
                    if (synth) synth.cancel();
                    status.textContent = "Playback stopped.";
                  }});
                  }};
                  bindPlayer();
                }})();
              </script>
            </div></body></html>""", height=220)
            st.markdown(f"#### Transcript - {html.escape(language)}")
            transcript = html.escape(explanation).replace("\n", "<br>")
            st.markdown(f"<div class='card'>{transcript}</div>", unsafe_allow_html=True)


def render_home():
    st.markdown("<div class='hero'><span class='eyebrow'>Medication information, made clearer</span><h1>Know what you're taking.</h1><p class='subtle'>Understand medication labels with clear information from the FDA, explained in everyday language.</p></div>", unsafe_allow_html=True)
    st.subheader("What medication are you looking for?")
    requested_search = st.session_state.pop("search_input", None)
    if requested_search is not None:
        st.session_state.home_query = requested_search
    query = st.text_input("Search medication", placeholder="Try a generic or brand name...", label_visibility="collapsed", key="home_query")
    if query.strip():
        st.button("Clear search", key="clear_home_search", on_click=clear_widget_value, args=("home_query",))
    suggestions = []
    if len(query.strip()) >= 2:
        try:
            suggestions = get_suggestions(query.strip())
        except Exception:
            suggestions = []
    if suggestions:
        chosen = st.selectbox("Suggestions from FDA drug labels", ["Choose a suggestion..."] + suggestions, label_visibility="collapsed")
        if chosen != "Choose a suggestion...":
            query = chosen
    elif len(query.strip()) >= 3:
        known = ["paracetamol", "acetaminophen", "ibuprofen", "aspirin", "amoxicillin", "metformin", "panadol"]
        close = difflib.get_close_matches(query.casefold(), known, n=1, cutoff=.72)
        if close and close[0] != query.casefold():
            suggestion = close[0].title()
            st.info(f"Did you mean {suggestion}?")
            if st.button(f"Use {suggestion}", key="inline_typo_suggestion"):
                st.session_state.search_input = suggestion
                st.rerun()
    search = st.button("Search medication >", type="primary", use_container_width=True)
    if search:
        cleaned = query.strip()
        if not cleaned:
            st.warning("Enter a medication name to search.")
        else:
            try:
                with st.spinner("Searching official medication information..."):
                    data = load_medication(cleaned)
                set_medication(cleaned, data)
                st.rerun()
            except LookupError:
                known = ["paracetamol", "acetaminophen", "ibuprofen", "aspirin", "amoxicillin", "metformin", "panadol"]
                close = difflib.get_close_matches(cleaned.casefold(), known, n=1, cutoff=.72)
                if close:
                    st.warning(f"We could not find {cleaned}. Did you mean **{close[0].title()}**?")
                    if st.button(f"Search {close[0].title()}", key="typo_suggestion"):
                        st.session_state.search_input = close[0].title()
                        st.rerun()
                else:
                    st.error(f"No FDA label information was found for {cleaned}. Try another medication name or check the spelling.")
            except Exception as error:
                if isinstance(error, ConnectionError):
                    st.error("The FDA medication information service is temporarily unavailable. Please try again in a moment.")
                else:
                    st.error("We could not complete that search. Check the medication name and try again.")
    st.markdown("<div class='notice'><b>Use trusted information</b><br>MIT explains medication information. It does not diagnose or replace advice from a qualified health professional.</div>", unsafe_allow_html=True)
    with st.container(key="home_actions"):
        history_col, about_col = st.columns(2)
        with history_col:
            if st.button("Search history", key="home_history", use_container_width=True):
                set_view("history")
                st.rerun()
        with about_col:
            if st.button("About MIT", key="home_about", use_container_width=True):
                set_view("about")
                st.rerun()
    st.markdown("#### Popular searches")
    cols = st.columns(4)
    for col, name in zip(cols, ["Paracetamol", "Ibuprofen", "Amoxicillin", "Metformin"]):
        with col:
            if st.button(name, key=f"popular_{name}", use_container_width=True):
                st.session_state.search_input = name
                st.rerun()
    feature_cols = st.columns(3)
    features = [
        ("01", "Easy to understand", "AI explanations in clear, simple language."),
        ("02", "Multiple languages", "English, Nigerian Pidgin, Yoruba, Igbo and Hausa."),
        ("03", "Safety focused", "FDA label warnings, side effects and recall records."),
    ]
    for col, (icon, title, description) in zip(feature_cols, features):
        with col:
            card(f"{icon}  {title}", html.escape(description))


def render_saved():
    st.markdown("<span class='eyebrow'>Your library</span>", unsafe_allow_html=True)
    st.title("Saved medications")
    saved = load_saved()
    st.caption(f"{len(saved)} saved - stored for this session")
    saved_filter = st.text_input("Search saved medications", placeholder="Search saved medicines", key="saved_filter")
    if saved_filter.strip():
        st.button("Clear filter", key="clear_saved_filter", on_click=clear_widget_value, args=("saved_filter",))
    visible = [name for name in saved if saved_filter.strip().casefold() in name.casefold()]
    if not saved:
        st.markdown("<div class='card'><div class='card-title'>Your saved medications will appear here</div><p class='subtle'>Save a medication from its information page to find it again quickly.</p></div>", unsafe_allow_html=True)
        if st.button("Search medications", type="primary"):
            set_view("home")
            st.rerun()
        return
    if not visible:
        st.info("No saved medication matches that search.")
        return
    for name in visible:
        a, b = st.columns([5, 1])
        with a:
            if st.button(f"{name}", key=f"open_saved_{name}", use_container_width=True):
                set_medication(name)
                st.rerun()
        with b:
            if st.button("Remove", key=f"remove_saved_{name}"):
                remove_saved(name)
                st.rerun()
    st.markdown("<div class='source-note'><b>Saved information may change</b><br>Open a medication to load the latest available FDA label and check the product you have.</div>", unsafe_allow_html=True)


def render_history():
    st.markdown("<span class='eyebrow'>Your activity</span>", unsafe_allow_html=True)
    st.title("Search history")
    if st.button("Home", key="history_home"):
        set_view("home")
        st.rerun()
    history = list(reversed(load_history()))
    if st.button("Clear history", key="clear_history"):
        clear_history()
        st.rerun()
    if not history:
        st.markdown("<div class='card'><div class='card-title'>No searches yet</div><p class='subtle'>Medication searches you make will appear here. Saved medications are kept separately.</p></div>", unsafe_allow_html=True)
        return
    grouped = {"Today": [], "Earlier": []}
    for entry in history:
        group, readable_time = format_history_time(entry.get("timestamp", ""))
        grouped.setdefault(group, []).append((entry, readable_time))
    for group in ("Today", "Earlier"):
        entries = grouped.get(group, [])
        if not entries:
            continue
        st.markdown(f"<div class='history-day'>{group}</div>", unsafe_allow_html=True)
        for index, (entry, readable_time) in enumerate(entries):
            name = str(entry.get("medication", "Medication"))
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"<div class='card'><b>{html.escape(name)}</b><br><span class='subtle'>{html.escape(readable_time)} | Search</span></div>", unsafe_allow_html=True)
            with right:
                if st.button("Open result", key=f"open_history_{group}_{index}_{entry.get('timestamp', '')}", use_container_width=True):
                    set_medication(name)
                    st.rerun()


def render_about():
    st.markdown("<span class='eyebrow'>About MIT</span>", unsafe_allow_html=True)
    st.title("Medication information, made clearer")
    st.markdown("<div class='card'><div class='card-title'>What MIT does</div><p>MIT helps people understand medication information by presenting details from FDA drug labels and explaining label language in simpler terms.</p><p>AI explanations and translations are educational aids. They can make mistakes and do not diagnose, prescribe, or replace advice from a pharmacist or other qualified health professional.</p><p>Always check the label for the exact product and strength you have. If you are unsure about a medication or a warning, ask a pharmacist or clinician.</p></div>", unsafe_allow_html=True)
    st.caption("Information, not diagnosis.")
    if st.button("Back to Home", key="about_home", type="primary"):
        set_view("home")
        st.rerun()


def main():
    st.set_page_config(page_title="MIT | Medication information, made clearer", page_icon="M", layout="wide", initial_sidebar_state="expanded")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    if "view" not in st.session_state:
        st.session_state.view = "home"
    if "result_tab" not in st.session_state:
        st.session_state.result_tab = "Quick summary"
    st.markdown("<div class='mit-brand mit-topbrand'><span class='mit-mark'>&#10047;</span><span>MIT<small>Medication Information Translator</small></span></div>", unsafe_allow_html=True)
    desktop_current = {"home": "home", "result": "home", "recall": "home", "saved": "saved", "history": "history", "about": "about"}.get(st.session_state.view, "home")
    mobile_current = "Saved" if st.session_state.view == "saved" else "Home"
    with st.sidebar:
        st.markdown("<div class='mit-brand'><span class='mit-mark'>&#10047;</span><span>MIT<small>Medication Information Translator</small></span></div>", unsafe_allow_html=True)
        st.write("")
        for label, view in (("Home", "home"), ("Saved", "saved"), ("History", "history"), ("About", "about")):
            if st.button(label, key=f"side_{view}", use_container_width=True, type="primary" if desktop_current == view else "secondary"):
                set_view(view)
                st.rerun()
        st.markdown("<div class='card' style='margin-top:2rem'><b>Information, not diagnosis</b><br><small class='subtle'>MIT provides general medication information and is not a substitute for advice from a qualified healthcare professional.</small></div>", unsafe_allow_html=True)
    st.session_state.pop("pending_mobile_nav", None)
    with st.container(key="mobile_nav"):
        home_col, saved_col = st.columns(2)
        with home_col:
            if st.button("Home", key="mobile_home", type="primary" if mobile_current == "Home" else "secondary", use_container_width=True):
                set_view("home")
                st.rerun()
        with saved_col:
            if st.button("Saved", key="mobile_saved", type="primary" if mobile_current == "Saved" else "secondary", use_container_width=True):
                set_view("saved")
                st.rerun()
    if st.session_state.view == "home":
        render_home()
    elif st.session_state.view == "saved":
        render_saved()
    elif st.session_state.view == "history":
        render_history()
    elif st.session_state.view == "about":
        render_about()
    elif st.session_state.view == "recall":
        data = st.session_state.get("medication_data")
        if data and data.get("recall", {}).get("recalled"):
            render_recall(data)
        else:
            set_view("home")
            st.rerun()
    else:
        render_result()
    st.divider()
    st.caption("MIT provides general medication information, not medical advice. Always consult a qualified health professional about your care.")


if __name__ == "__main__":
    # `python app.py` starts Streamlit; `streamlit run app.py` renders this module.
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        in_streamlit = get_script_run_ctx(suppress_warning=True) is not None
    except (ImportError, TypeError):
        in_streamlit = bool(os.environ.get("STREAMLIT_SERVER_PORT"))
    if not in_streamlit:
        raise SystemExit(subprocess.call([
            sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ], cwd=ROOT))
    main()
else:
    main()
