from cda_calc.models import TirePreset

# Source: Bicycle Rolling Resistance — GP5000 TT TR
# https://www.bicyclerollingresistance.com/road-bike-reviews/continental-grand-prix-5000-tt-tr
GP5000_TT_PRESETS: list[TirePreset] = [
    TirePreset(
        name="GP5000 TT 25mm @ 80 psi",
        size_mm=25,
        pressure_psi=80,
        crr=0.0026,
        estimated=True,
    ),
    TirePreset(
        name="GP5000 TT 28mm @ 72 psi (BRR)",
        size_mm=28,
        pressure_psi=72,
        crr=0.00249,
        estimated=False,
    ),
    TirePreset(
        name="GP5000 TT 28mm @ 90 psi",
        size_mm=28,
        pressure_psi=90,
        crr=0.0023,
        estimated=True,
    ),
    TirePreset(
        name="GP5000 TT 30mm @ 72 psi",
        size_mm=30,
        pressure_psi=72,
        crr=0.0024,
        estimated=True,
    ),
]

DEFAULT_PRESET_INDEX = 0


def preset_labels() -> list[str]:
    return [p.name for p in GP5000_TT_PRESETS]


def preset_by_index(index: int) -> TirePreset:
    return GP5000_TT_PRESETS[index]
