"""Per-session storage for medications saved by the current visitor."""

import streamlit as st


_SAVED_KEY = "mit_saved_medications"


def load_saved() -> list[str]:
    items = st.session_state.get(_SAVED_KEY, [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, str) and item.strip()]


def _write(names: list[str]) -> None:
    st.session_state[_SAVED_KEY] = names


def add_saved(name: str) -> None:
    clean_name = name.strip()
    if clean_name and not is_saved(clean_name):
        _write(load_saved() + [clean_name])


def remove_saved(name: str) -> None:
    _write([item for item in load_saved() if item.casefold() != name.casefold()])


def is_saved(name: str) -> bool:
    return any(item.casefold() == name.casefold() for item in load_saved())
