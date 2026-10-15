"""Per-session search history for the current Streamlit visitor."""

from datetime import datetime

import streamlit as st


_HISTORY_KEY = "mit_search_history"


def load_history() -> list[dict]:
    entries = st.session_state.get(_HISTORY_KEY, [])
    if not isinstance(entries, list):
        return []
    return [dict(entry) for entry in entries if isinstance(entry, dict)]


def save_search(name: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Medication name must be a non-empty string.")

    entries = load_history()
    entries.append({
        "medication": name.strip(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    st.session_state[_HISTORY_KEY] = entries


def clear_history() -> None:
    st.session_state[_HISTORY_KEY] = []
