"""UI translations (PL / EN) for Streamlit app."""

from __future__ import annotations

from typing import Any

import streamlit as st

DEFAULT_LANG = "pl"

_MESSAGES: dict[str, dict[str, str]] = {
    "pl": {
        "page_title": "CdA Kalkulator TT",
        "title": "CdA Kalkulator",
        "seo_intro": (
            "**Darmowy kalkulator CdA online** — oblicz współczynnik oporu aerodynamicznego "
            "(*coefficient of drag × frontal area*, m²) z pliku **TCX** z Garmina (power meter, prędkość, wysokość). "
            "Metoda **Virtual Elevation** Roberta Chunga dla **time trial**, **triathlonu** i testów pozycji aero na szosie. "
            "Wgraj plik, wybierz segment trasy i porównaj profil VE z wysokością barometryczną. "
            "Dane przetwarzane **lokalnie** — plik nie jest wysyłany na serwer."
        ),
        "ref_table_who": "Kto / pozycja",
        "ref_table_cda": "CdA (m²)",
        "ref_table_power": "Moc przy 40 km/h (W)",
        "ref_pro_uci": "Pro UCI (TT / tor, tunel)",
        "ref_very_good_amateur": "Bardzo dobry amator TT",
        "ref_typical_amateur": "Typowy amator TT / triathlon",
        "ref_drops": "Szosa, chwyty dolne",
        "ref_hoods": "Szosa, kierownica",
        "ref_city": "Rower miejski / turystyczny",
        "ref_grandma": "Babcia na Wigry 6",
        "ref_scale_title": "**Skala orientacyjna CdA**",
        "ref_scale_caption": (
            "Moc przy 40 km/h dla masy {mass:.0f} kg (płasko, bez wiatru, "
            "ρ = 1,225 kg/m³, strata napędu 2%). Crr: opony TT dla pozycji aero, wyższe dla szosy, "
            "miasta i Wigry."
        ),
        "protocol": (
            "Pośrednie szacowanie **CdA** z power metera według Roberta Chunga "
            "(*Estimating CdA with a power meter*, 2012) — "
            "[pełna dokumentacja (PDF)]({pdf_url}).\n\n"
            "**Protokół jazdy testowej**\n\n"
            "1. **Trasa** — okrążenia lub out-and-back na tym samym odcinku; droga nie musi być płaska "
            "(lekkie wzniesienie pomaga rozróżnić efekty).\n"
            "2. **Moc i prędkość** — nie muszą być stałe; lepiej je zmieniać niż trzymać jedno tempo.\n"
            "3. **Pozycja** — utrzymuj stałą pozycję TT przez cały segment; **nie hamuj**.\n"
            "4. **Warunki** — wiatr jak najbliżej zera; przy małych różnicach w CdA testuj w bez wietrzny dzień.\n"
            "5. **Pomiar** — zapis mocy i prędkości co ~1 s (TCX z Garmina); zmierz lub oszacuj gęstość powietrza.\n"
            "6. **Analiza** — z mocy i prędkości liczymy profil **Virtual Elevation** i szukamy CdA, "
            "przy którym VE najlepiej pokrywa zmierzoną wysokość (zerowy bilans na okrążenie / minimalne RMSE).\n\n"
            "Dobre miejsca: pętla w parku przemysłowym, out-and-back na łagodnym podjeździe, krótsze okrążenia "
            "(dają więcej powtórzeń). Unikaj tras z hamowaniem, podmuchami wiatru i ruchem wymuszającym postoje."
        ),
        "help_dialog_title": "CdA — jak to działa?",
        "help_dialog_tooltip": "CdA — jak to działa?",
        "help_body": (
            "**CdA** (coefficient of drag × frontal area) to współczynnik oporu aerodynamicznego w m². "
            "Im niższy, tym mniej mocy potrzeba na tę samą prędkość.\n\n"
            "### Co robi „Oblicz CdA”?\n\n"
            "1. Bierze wybrany **segment** (okrążenia lub zakres km).\n"
            "2. Z mocy, prędkości i wysokości liczy **Virtual Elevation (VE)** — „sztuczny” profil "
            "wysokości przy założonym CdA.\n"
            "3. **Szuka CdA** (zakres 0,15–0,35 m²), przy którym VE najlepiej pokrywa zmierzoną "
            "wysokość (minimalizuje **RMSE**).\n"
            "4. Wynik zapisuje jako **CdA (obliczone)** i **ustawia suwak** na tę wartość.\n\n"
            "### Co robi suwak ręcznie?\n\n"
            "Suwak pozwala zmieniać CdA **bez ponownego liczenia**:\n\n"
            "- przesuwasz go → od razu przeliczane są wykresy VE i RMSE dla tej wartości,\n"
            "- możesz sprawdzić np. *„co jeśli CdA było o 0,01 m² wyższe?”*,\n"
            "- pod wykresem pojawia się szacunek wpływu na moc przy 40 km/h.\n\n"
            "To **symulator**, nie nowa optymalizacja.\n\n"
            "### Dwie wartości na ekranie\n\n"
            "| Metryka | Znaczenie |\n"
            "|--------|-----------|\n"
            "| **CdA (obliczone)** | Wynik z ostatniego „Oblicz CdA” — nie zmienia się przy ruszaniu suwaka |\n"
            "| **CdA (suwak)** | Wartość używana do wykresów — po obliczeniu = obliczone, potem możesz ją zmieniać |\n\n"
            "### Skala orientacyjna — od pro do babci na Wigry 6\n\n"
            "Szacunkowe wartości CdA (m²) — żeby wiedzieć, gdzie na skali jesteś:\n\n"
            "{ref_table}\n\n"
            "Moc przy **40 km/h** dla masy **{mass:.0f} kg** (płasko, bez wiatru, ρ = 1,225 kg/m³, "
            "strata napędu 2%). Crr: opony TT dla pozycji aero, wyższe dla szosy, miasta i Wigry.\n\n"
            "Wartości zależą od pozycji, sprzętu i jakości pomiaru — traktuj jako punkt odniesienia, nie prawdę absolutną.\n\n"
            "### Kiedy liczyć ponownie?\n\n"
            "Gdy zmienisz **segment** (inne okrążenia lub zakres km), kliknij **Oblicz CdA** ponownie — "
            "**CdA (obliczone)** dotyczy tylko segmentu, dla którego je wyznaczono."
        ),
        "sidebar_settings": "Ustawienia",
        "mass_kg": "Masa łączna (kg)",
        "tires_preset": "Opony — preset Crr",
        "crr_estimated": "Szacunkowa wartość Crr (BRR nie publikuje dokładnej liczby dla tego presetu).",
        "crr_slider": "Crr (współczynnik toczenia)",
        "air_section": "Powietrze",
        "temperature": "Temperatura (°C)",
        "altitude": "Wysokość n.p.m. (m)",
        "humidity": "Wilgotność (%)",
        "air_density": "Gęstość powietrza ρ",
        "drivetrain_loss": "Strata napędu (%)",
        "filters_section": "Filtry jakości",
        "min_speed": "Min. prędkość (km/h)",
        "max_speed": "Max. prędkość (km/h)",
        "max_speed_help": "0 = bez limitu",
        "min_power": "Min. moc (W)",
        "filter_accel": "Odrzuć |przyspieszenie| > 0.5 m/s²",
        "min_coverage": "Min. pokrycie danych (%)",
        "upload_tcx": "Wgraj plik TCX z Garmina",
        "upload_info": "Wgraj plik `.tcx` z jazdy TT (power meter + prędkość + wysokość).",
        "upload_splits": "Wgraj plik podziałów CSV z Garmina (opcjonalnie)",
        "upload_splits_help": "Eksport okrążeń z Garmin Connect — umożliwia wybór lapów do analizy CdA.",
        "distance_error": "Nie udało się obliczyć dystansu jazdy z pliku TCX.",
        "speed_gps_warning": "Prędkość wyłącznie z GPS — dla lepszej dokładności użyj czujnika koła.",
        "speed_mixed_warning": "Część punktów ma prędkość z GPS (brak Speed w TPX).",
        "splits_error": "Plik podziałów: {error}",
        "csv_distance_warning": (
            "Dystans w CSV ({csv:.1f} km) różni się od TCX ({tcx:.1f} km). "
            "Zakresy okrążeń zostaną przeskalowane do długości jazdy z TCX."
        ),
        "segment_mode_label": "Tryb wyboru segmentu",
        "segment_mode_laps": "Okrążenia (CSV)",
        "segment_mode_manual": "Ręczny zakres (km)",
        "laps_multiselect": "Okrążenia do analizy CdA",
        "select_lap_warning": "Wybierz co najmniej jedno okrążenie do analizy CdA.",
        "chart_caption_laps": (
            "Niebieskie pasy = wybrane okrążenia. Szare linie = granice lapów z CSV. "
            "Przełącz na „Ręczny zakres (km)”, aby użyć suwaka lub zaznaczenia na wykresie."
        ),
        "chart_caption_manual": (
            "Niebieski pas = wybrany segment. Zaznacz prostokątem na wykresie lub użyj suwaka poniżej."
        ),
        "segment_slider": "Zakres segmentu (km)",
        "segment_slider_help": "Wybierz stabilny odcinek jazdy TT (bez postojów i hamowania).",
        "whole_ride_btn": "Cała jazda",
        "select_lap_continue": "Wybierz co najmniej jedno okrążenie, aby kontynuować analizę.",
        "segment_time": "Czas segmentu",
        "segment_distance": "Dystans segmentu",
        "avg_power": "Śr. moc",
        "normalized_power": "Normalized Power",
        "avg_speed": "Śr. prędkość",
        "compute_cda": "Oblicz CdA",
        "optimizing": "Optymalizacja CdA...",
        "compute_success": "CdA = {cda:.3f} m² · RMSE = {rmse:.2f} m · pokrycie {coverage:.0f}%",
        "compute_error": "Błąd optymalizacji: {error}",
        "segment_changed": "Segment zmienił się od ostatniego obliczenia — kliknij **Oblicz CdA** ponownie.",
        "cda_slider": "CdA (ręczna korekta / eksperyment)",
        "cda_slider_metric": "CdA (suwak)",
        "cda_computed_metric": "CdA (obliczone)",
        "rmse_ve": "RMSE VE",
        "data_coverage": "Pokrycie danych",
        "info_laps": "Wybierz okrążenia z CSV i kliknij **Oblicz CdA**.",
        "info_manual": "Ustaw zakres segmentu suwakiem km, potem kliknij **Oblicz CdA**.",
        "low_coverage": (
            "Za mało punktów po filtrach ({pct:.1f}% < {min_pct}%). "
            "Obniż progi prędkości/mocy lub wybierz inny segment."
        ),
        "comparison_title": "**Porównanie CdA obliczone vs suwak**",
        "comparison_caption": (
            "Szacunki na płaskiej trasie bez wiatru (masa {mass:.0f} kg, Crr {crr:.4f}, "
            "ρ = {rho:.3f} kg/m³, strata napędu {loss:.0f}%). "
            "Prędkość i czas liczone przy średniej mocy segmentu ({power:.0f} W)."
        ),
        "table_metric": "Metryka",
        "table_computed": "CdA obliczone ({cda:.3f} m²)",
        "table_slider": "CdA suwak ({cda:.3f} m²)",
        "table_diff": "Różnica",
        "table_power_40": "Moc przy 40 km/h (płasko, bez wiatru)",
        "table_speed_at_power": "Prędkość przy {power} W (płasko, bez wiatru)",
        "table_time_at_distance": "Szac. czas na {distance} (płasko, bez wiatru)",
        "chart_power_speed": "Moc i prędkość",
        "chart_power": "Moc (W)",
        "chart_speed": "Prędkość (km/h)",
        "chart_distance": "Dystans (km)",
        "chart_height": "Wysokość (m)",
        "chart_ve_title": "Wysokość zmierzona vs Virtual Elevation",
        "chart_elev_rejected": "Wysokość (odrzucone)",
        "chart_elev_measured": "Wysokość (zmierzona)",
        "chart_virtual_elevation": "Virtual Elevation",
        "chart_residuals": "Reszty VE − zmierzona wysokość",
        "chart_residuals_valid": "Reszty (valid)",
        "filter_details": "Szczegóły filtrów",
        "filter_low_speed": "Odrzucone (niska prędkość)",
        "filter_high_speed": "Odrzucone (wysoka prędkość)",
        "filter_low_power": "Odrzucone (niska moc)",
        "filter_high_accel": "Odrzucone (wysokie |a|)",
        "limitations": "Ograniczenia",
        "limitations_body": (
            "- Wybierz **stabilny odcinek** (bez postojów, zakrętów, coastingu).\n"
            "- Filtry odcinają punkty poniżej progów prędkości/mocy — zostaw ≥30% punktów w segmencie.\n"
            "- Stały Crr z presetu GP5000 TT daje dobrą dokładność **względną** (porównanie pozycji).\n"
            "- Najlepsze wyniki: stała pozycja TT, bez hamowania, bez wiatru, równomierna moc."
        ),
        "lap_word": "Okr.",
    },
    "en": {
        "page_title": "CdA Calculator TT",
        "title": "CdA Calculator",
        "seo_intro": (
            "**Free online CdA calculator** — estimate your aerodynamic drag coefficient "
            "(*coefficient of drag × frontal area*, m²) from a Garmin **TCX** file (power meter, speed, elevation). "
            "Uses Robert Chung's **Virtual Elevation** method for **time trial**, **triathlon**, and aero position testing. "
            "Upload a file, pick a route segment, and compare the VE profile with barometric elevation. "
            "Data is processed **locally** — your file is never sent to a server."
        ),
        "ref_table_who": "Rider / position",
        "ref_table_cda": "CdA (m²)",
        "ref_table_power": "Power at 40 km/h (W)",
        "ref_pro_uci": "Pro UCI (TT / track, wind tunnel)",
        "ref_very_good_amateur": "Very strong amateur TT",
        "ref_typical_amateur": "Typical amateur TT / triathlon",
        "ref_drops": "Road, drops",
        "ref_hoods": "Road, hoods",
        "ref_city": "City / touring bike",
        "ref_grandma": "Grandma on a charity ride",
        "ref_scale_title": "**CdA reference scale**",
        "ref_scale_caption": (
            "Power at 40 km/h for {mass:.0f} kg (flat, no wind, "
            "ρ = 1.225 kg/m³, 2% drivetrain loss). Crr: TT tires for aero positions, higher for road, "
            "city, and touring setups."
        ),
        "protocol": (
            "Indirect **CdA** estimation from a power meter by Robert Chung "
            "(*Estimating CdA with a power meter*, 2012) — "
            "[full documentation (PDF)]({pdf_url}).\n\n"
            "**Test ride protocol**\n\n"
            "1. **Route** — laps or out-and-back on the same stretch; the road need not be flat "
            "(a gentle climb helps separate effects).\n"
            "2. **Power and speed** — need not be constant; varying them is better than holding one pace.\n"
            "3. **Position** — keep a steady TT position for the whole segment; **do not brake**.\n"
            "4. **Conditions** — wind as close to zero as possible; for small CdA differences, test on a calm day.\n"
            "5. **Recording** — power and speed logged ~every 1 s (Garmin TCX); measure or estimate air density.\n"
            "6. **Analysis** — from power and speed we compute **Virtual Elevation** and find the CdA "
            "where VE best matches measured elevation (zero net on a loop / minimum RMSE).\n\n"
            "Good options: industrial-park loop, out-and-back on a gentle grade, shorter laps "
            "(more repetitions). Avoid routes with braking, gusts, and traffic forcing stops."
        ),
        "help_dialog_title": "CdA — how it works",
        "help_dialog_tooltip": "CdA — how it works",
        "help_body": (
            "**CdA** (coefficient of drag × frontal area) is the aerodynamic drag coefficient in m². "
            "The lower it is, the less power you need for the same speed.\n\n"
            "### What does “Calculate CdA” do?\n\n"
            "1. Takes the selected **segment** (laps or km range).\n"
            "2. Computes **Virtual Elevation (VE)** from power, speed, and elevation — a synthetic "
            "elevation profile for a given CdA.\n"
            "3. **Searches for CdA** (range 0.15–0.35 m²) where VE best matches measured elevation "
            "(minimizes **RMSE**).\n"
            "4. Stores the result as **CdA (computed)** and **sets the slider** to that value.\n\n"
            "### What does the manual slider do?\n\n"
            "The slider lets you change CdA **without re-running optimization**:\n\n"
            "- move it → VE charts and RMSE update immediately for that value,\n"
            "- explore e.g. *“what if CdA were 0.01 m² higher?”*,\n"
            "- a comparison table shows the effect on power at 40 km/h.\n\n"
            "It is a **simulator**, not a new optimization run.\n\n"
            "### Two values on screen\n\n"
            "| Metric | Meaning |\n"
            "|--------|---------|\n"
            "| **CdA (computed)** | Result from the last “Calculate CdA” — unchanged when you move the slider |\n"
            "| **CdA (slider)** | Value used for charts — equals computed after calculation, then adjustable |\n\n"
            "### Reference scale — from pro to touring setup\n\n"
            "Approximate CdA values (m²) — to see where you sit:\n\n"
            "{ref_table}\n\n"
            "Power at **40 km/h** for **{mass:.0f} kg** (flat, no wind, ρ = 1.225 kg/m³, "
            "2% drivetrain loss). Crr: TT tires for aero positions, higher for road and city setups.\n\n"
            "Values depend on position, equipment, and measurement quality — use as a reference, not absolute truth.\n\n"
            "### When to recalculate?\n\n"
            "When you change the **segment** (different laps or km range), click **Calculate CdA** again — "
            "**CdA (computed)** applies only to the segment it was calculated for."
        ),
        "sidebar_settings": "Settings",
        "mass_kg": "Total mass (kg)",
        "tires_preset": "Tires — Crr preset",
        "crr_estimated": "Estimated Crr (BRR does not publish an exact value for this preset).",
        "crr_slider": "Crr (rolling resistance)",
        "air_section": "Air",
        "temperature": "Temperature (°C)",
        "altitude": "Altitude (m)",
        "humidity": "Humidity (%)",
        "air_density": "Air density ρ",
        "drivetrain_loss": "Drivetrain loss (%)",
        "filters_section": "Quality filters",
        "min_speed": "Min. speed (km/h)",
        "max_speed": "Max. speed (km/h)",
        "max_speed_help": "0 = no limit",
        "min_power": "Min. power (W)",
        "filter_accel": "Reject |acceleration| > 0.5 m/s²",
        "min_coverage": "Min. data coverage (%)",
        "upload_tcx": "Upload Garmin TCX file",
        "upload_info": "Upload a `.tcx` file from a TT ride (power meter + speed + elevation).",
        "upload_splits": "Upload Garmin splits CSV (optional)",
        "upload_splits_help": "Lap export from Garmin Connect — enables lap selection for CdA analysis.",
        "distance_error": "Could not compute ride distance from the TCX file.",
        "speed_gps_warning": "Speed from GPS only — use a wheel sensor for better accuracy.",
        "speed_mixed_warning": "Some points use GPS speed (missing Speed in TPX).",
        "splits_error": "Splits file: {error}",
        "csv_distance_warning": (
            "CSV distance ({csv:.1f} km) differs from TCX ({tcx:.1f} km). "
            "Lap ranges will be scaled to the TCX ride length."
        ),
        "segment_mode_label": "Segment selection mode",
        "segment_mode_laps": "Laps (CSV)",
        "segment_mode_manual": "Manual range (km)",
        "laps_multiselect": "Laps for CdA analysis",
        "select_lap_warning": "Select at least one lap for CdA analysis.",
        "chart_caption_laps": (
            "Blue bands = selected laps. Gray lines = lap boundaries from CSV. "
            "Switch to “Manual range (km)” to use the slider or chart selection."
        ),
        "chart_caption_manual": (
            "Blue band = selected segment. Box-select on the chart or use the slider below."
        ),
        "segment_slider": "Segment range (km)",
        "segment_slider_help": "Pick a stable TT segment (no stops or braking).",
        "whole_ride_btn": "Full ride",
        "select_lap_continue": "Select at least one lap to continue analysis.",
        "segment_time": "Segment time",
        "segment_distance": "Segment distance",
        "avg_power": "Avg. power",
        "normalized_power": "Normalized Power",
        "avg_speed": "Avg. speed",
        "compute_cda": "Calculate CdA",
        "optimizing": "Optimizing CdA...",
        "compute_success": "CdA = {cda:.3f} m² · RMSE = {rmse:.2f} m · coverage {coverage:.0f}%",
        "compute_error": "Optimization error: {error}",
        "segment_changed": "Segment changed since the last calculation — click **Calculate CdA** again.",
        "cda_slider": "CdA (manual tweak / what-if)",
        "cda_slider_metric": "CdA (slider)",
        "cda_computed_metric": "CdA (computed)",
        "rmse_ve": "RMSE VE",
        "data_coverage": "Data coverage",
        "info_laps": "Select laps from CSV and click **Calculate CdA**.",
        "info_manual": "Set the segment range with the km slider, then click **Calculate CdA**.",
        "low_coverage": (
            "Too few points after filters ({pct:.1f}% < {min_pct}%). "
            "Lower speed/power thresholds or pick another segment."
        ),
        "comparison_title": "**CdA computed vs slider comparison**",
        "comparison_caption": (
            "Estimates on a flat course with no wind (mass {mass:.0f} kg, Crr {crr:.4f}, "
            "ρ = {rho:.3f} kg/m³, drivetrain loss {loss:.0f}%). "
            "Speed and time computed at segment average power ({power:.0f} W)."
        ),
        "table_metric": "Metric",
        "table_computed": "CdA computed ({cda:.3f} m²)",
        "table_slider": "CdA slider ({cda:.3f} m²)",
        "table_diff": "Difference",
        "table_power_40": "Power at 40 km/h (flat, no wind)",
        "table_speed_at_power": "Speed at {power} W (flat, no wind)",
        "table_time_at_distance": "Est. time over {distance} (flat, no wind)",
        "chart_power_speed": "Power and speed",
        "chart_power": "Power (W)",
        "chart_speed": "Speed (km/h)",
        "chart_distance": "Distance (km)",
        "chart_height": "Elevation (m)",
        "chart_ve_title": "Measured elevation vs Virtual Elevation",
        "chart_elev_rejected": "Elevation (rejected)",
        "chart_elev_measured": "Elevation (measured)",
        "chart_virtual_elevation": "Virtual Elevation",
        "chart_residuals": "VE residuals − measured elevation",
        "chart_residuals_valid": "Residuals (valid)",
        "filter_details": "Filter details",
        "filter_low_speed": "Rejected (low speed)",
        "filter_high_speed": "Rejected (high speed)",
        "filter_low_power": "Rejected (low power)",
        "filter_high_accel": "Rejected (high |a|)",
        "limitations": "Limitations",
        "limitations_body": (
            "- Pick a **stable segment** (no stops, corners, or coasting).\n"
            "- Filters drop points below speed/power thresholds — keep ≥30% of points in the segment.\n"
            "- Fixed GP5000 TT Crr gives good **relative** accuracy (position comparison).\n"
            "- Best results: steady TT position, no braking, no wind, even power."
        ),
        "lap_word": "Lap",
    },
}

CDA_REFERENCE_ROW_KEYS: list[tuple[str, float, float, float]] = [
    ("ref_pro_uci", 0.17, 0.20, 0.0026),
    ("ref_very_good_amateur", 0.20, 0.23, 0.0026),
    ("ref_typical_amateur", 0.23, 0.27, 0.0026),
    ("ref_drops", 0.27, 0.32, 0.0032),
    ("ref_hoods", 0.32, 0.37, 0.0038),
    ("ref_city", 0.37, 0.42, 0.0060),
    ("ref_grandma", 0.45, 0.55, 0.0080),
]


def get_lang() -> str:
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in _MESSAGES else DEFAULT_LANG


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    code = lang or get_lang()
    messages = _MESSAGES.get(code, _MESSAGES[DEFAULT_LANG])
    template = messages.get(key, _MESSAGES[DEFAULT_LANG][key])
    return template.format(**kwargs) if kwargs else template


def language_selector() -> None:
    current = get_lang()
    choice = st.radio(
        "Language",
        options=["pl", "en"],
        format_func=lambda code: "PL" if code == "pl" else "EN",
        horizontal=True,
        index=0 if current == "pl" else 1,
        label_visibility="collapsed",
        key="lang_selector",
    )
    if choice != current:
        st.session_state.lang = choice
        st.rerun()


def fmt_decimal(value: float, decimals: int = 2, lang: str | None = None) -> str:
    text = f"{value:.{decimals}f}"
    if (lang or get_lang()) == "pl":
        return text.replace(".", ",")
    return text
