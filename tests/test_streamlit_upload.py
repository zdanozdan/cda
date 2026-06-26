import streamlit as st

from cda_calc.streamlit_upload import format_file_size, should_show_persisted_row, uploader_was_cleared


def test_format_file_size_mb():
    assert format_file_size(int(5.6 * 1024 * 1024)) == "5.6MB"
    assert format_file_size(2048) == "2.0KB"


def test_uploader_was_cleared_when_user_removed_file():
    st.session_state.clear()
    st.session_state["tcx_uploader"] = None
    assert uploader_was_cleared("tcx_uploader", has_persisted_file=True) is True


def test_uploader_was_cleared_false_on_first_visit():
    st.session_state.clear()
    assert uploader_was_cleared("tcx_uploader", has_persisted_file=False) is False


def test_should_show_persisted_row_after_reload():
    st.session_state.clear()

    def load() -> tuple[bytes, str]:
        return b"data", "ride.tcx"

    show, data, name = should_show_persisted_row("tcx_uploader", "tcx_cleared", "tcx_replace", load)
    assert show is True
    assert data == b"data"
    assert name == "ride.tcx"


def test_should_not_show_persisted_row_when_cleared():
    st.session_state.clear()
    st.session_state["tcx_cleared"] = True

    def load() -> tuple[bytes, str]:
        return b"data", "ride.tcx"

    show, _, _ = should_show_persisted_row("tcx_uploader", "tcx_cleared", "tcx_replace", load)
    assert show is False


def test_should_not_show_persisted_row_in_replace_mode():
    st.session_state.clear()
    st.session_state["tcx_replace"] = True

    def load() -> tuple[bytes, str]:
        return b"data", "ride.tcx"

    show, _, _ = should_show_persisted_row("tcx_uploader", "tcx_cleared", "tcx_replace", load)
    assert show is False
