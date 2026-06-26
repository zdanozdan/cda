"""Persisted upload UI for files restored after page reload."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

import streamlit as st

if TYPE_CHECKING:
    LoadFn = Callable[[], tuple[bytes, str] | None]

UploadAction = Literal["clear", "replace"]


def format_file_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 0.1:
        return f"{mb:.1f}MB"
    kb = num_bytes / 1024
    if kb >= 0.1:
        return f"{kb:.1f}KB"
    return f"{num_bytes}B"


def uploader_was_cleared(uploader_key: str, has_persisted_file: bool) -> bool:
    """True when the user cleared the native uploader but a persisted file still exists."""
    return uploader_key in st.session_state and st.session_state[uploader_key] is None and has_persisted_file


def should_show_persisted_row(
    uploader_key: str,
    cleared_key: str,
    replace_key: str,
    load_fn: LoadFn,
) -> tuple[bool, bytes, str]:
    """Show a restored file row after reload (before the user touches file_uploader)."""
    if st.session_state.get(cleared_key, False):
        return False, b"", ""
    if st.session_state.get(replace_key, False):
        return False, b"", ""

    stored = load_fn()
    if stored is None or uploader_key in st.session_state:
        return False, b"", ""

    data, name = stored
    return True, data, name


def render_persisted_file_uploader(
    label: str,
    filename: str,
    file_size_bytes: int,
    clear_button_key: str,
    replace_button_key: str,
) -> UploadAction | None:
    """Render an uploaded-file row using native Streamlit widgets."""
    st.markdown(f"**{label}**")
    dropzone_col, add_col = st.columns([11, 1], vertical_alignment="center", gap="small")
    with dropzone_col:
        with st.container(border=True):
            icon_col, meta_col, clear_col = st.columns([0.6, 9, 0.8], vertical_alignment="center", gap="small")
            with icon_col:
                st.markdown(":material/description:")
            with meta_col:
                st.markdown(f"**{filename}**")
                st.caption(format_file_size(file_size_bytes))
            with clear_col:
                if st.button("✕", key=clear_button_key, help="Usuń plik", type="tertiary"):
                    return "clear"
    with add_col:
        if st.button("＋", key=replace_button_key, help="Dodaj plik", type="tertiary"):
            return "replace"
    return None
