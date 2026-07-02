from cda_calc.i18n import CDA_REFERENCE_ROW_KEYS, _MESSAGES, fmt_decimal, t


def test_all_keys_exist_in_both_languages():
    pl_keys = set(_MESSAGES["pl"])
    en_keys = set(_MESSAGES["en"])
    assert pl_keys == en_keys


def test_reference_row_keys_have_translations():
    for key, *_ in CDA_REFERENCE_ROW_KEYS:
        assert key in _MESSAGES["pl"]
        assert key in _MESSAGES["en"]


def test_t_english():
    assert "Calculator" in t("title", lang="en")
    assert "Kalkulator" in t("title", lang="pl")


def test_fmt_decimal_polish_uses_comma():
    assert fmt_decimal(0.23, lang="pl") == "0,23"


def test_fmt_decimal_english_uses_dot():
    assert fmt_decimal(0.23, lang="en") == "0.23"


def test_meta_description_keys():
    assert "CdA" in t("meta_description", lang="pl")
    assert "CdA" in t("meta_description", lang="en")
    assert "Virtual Elevation" in t("meta_description_chung", lang="pl")
