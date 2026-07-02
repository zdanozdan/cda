"""SEO helpers — meta tags injected into Streamlit pages."""

from __future__ import annotations

import html

import streamlit as st

from cda_calc.i18n import t

SITE_ORIGIN = "https://cda.enduhub.com"
APP_BASE = f"{SITE_ORIGIN}/app"


def _app_url(page: str, lang: str) -> str:
    if page == "metoda-chunga":
        return f"{APP_BASE}/?page=metoda-chunga&lang={lang}"
    return f"{APP_BASE}/?lang={lang}"


def render_page_meta(*, page: str, lang: str) -> None:
    """Inject description, canonical, hreflang and Open Graph tags."""
    if page == "metoda-chunga":
        description = t("meta_description_chung", lang=lang)
        title = f"{t('summary_title', lang=lang)} — {t('page_title', lang=lang)}"
    else:
        description = t("meta_description", lang=lang)
        title = t("page_title", lang=lang)

    canonical = _app_url(page, lang)
    pl_url = _app_url(page, "pl")
    en_url = _app_url(page, "en")
    landing_pl = f"{SITE_ORIGIN}/"
    landing_en = f"{SITE_ORIGIN}/en/"

    st.markdown(
        f"""
        <meta name="description" content="{html.escape(description)}">
        <link rel="canonical" href="{html.escape(canonical)}">
        <link rel="alternate" hreflang="pl" href="{html.escape(landing_pl if page == 'calculator' else pl_url)}">
        <link rel="alternate" hreflang="en" href="{html.escape(landing_en if page == 'calculator' else en_url)}">
        <link rel="alternate" hreflang="x-default" href="{html.escape(landing_pl)}">
        <meta property="og:type" content="website">
        <meta property="og:title" content="{html.escape(title)}">
        <meta property="og:description" content="{html.escape(description)}">
        <meta property="og:url" content="{html.escape(canonical)}">
        <meta property="og:site_name" content="{html.escape(t('meta_site_name', lang=lang))}">
        <meta name="twitter:card" content="summary">
        <meta name="twitter:title" content="{html.escape(title)}">
        <meta name="twitter:description" content="{html.escape(description)}">
        """,
        unsafe_allow_html=True,
    )
