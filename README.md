# CdA Kalkulator TT

Kalkulator współczynnika oporu aerodynamicznego **CdA** dla jazdy na czas (TT) na podstawie plików **TCX** z Garmina. Metoda **Virtual Elevation** (Robert Chung). Dane przetwarzane lokalnie — plik nie jest wysyłany na serwer.

## Wymagania sprzętowe

- **Power meter** (watts w TCX) — obowiązkowy
- **Prędkość** — najlepiej czujnik koła; GPS jako fallback
- **Wysokość** — barometr w Garminie
- Opony: presety **Continental GP5000 TT** (Crr z [Bicycle Rolling Resistance](https://www.bicyclerollingresistance.com/road-bike-reviews/continental-grand-prix-5000-tt-tr))

## Instalacja

```bash
cd cda_calc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uruchomienie

```bash
streamlit run app.py
```

Otwórz adres z terminala (zwykle http://localhost:8501), wgraj plik `.tcx` i kliknij **Oblicz CdA**.

### Wybór segmentu

Na wykresie **mocy i prędkości** możesz zaznaczyć prostokątem fragment trasy (jeśli przeglądarka to obsłuży). **Zawsze działa suwak „Zakres segmentu (km)”** pod wykresem — metryki i CdA aktualizują się od razu po jego przesunięciu.

## Testy

```bash
pytest
```

## Protokół jazdy (out-and-back)

1. Wybierz prostą trasę **tam i z powrotem** (5–15 km w jedną stronę), lekki profil wysokościowy pomaga dopasowaniu VE.
2. Jedź w **stałej pozycji TT**, bez hamowania i bez zmiany pozycji.
3. Utrzymuj **równomierną moc** (np. 250–300 W), unikaj sprintów i coastingu.
4. Najlepiej w **bez wietrzny** dzień; wiatr zafałszuje CdA w jednym kierunku.
5. Zaznacz na wykresie mocy/prędkości stabilny odcinek i kliknij **Oblicz CdA**.

## Filtry jakości danych

Domyślnie do optymalizacji CdA wchodzą tylko punkty z:

| Filtr | Domyślnie |
|-------|-----------|
| Min. prędkość | ≥ 29 km/h |
| Max. prędkość | opcjonalnie (0 = bez limitu) |
| Min. moc | ≥ 150 W |
| Przyspieszenie | \|a\| ≤ 0.5 m/s² (opcjonalnie) |

Punkty odrzucone (zakręty, zwrot, postój) są widoczne na wykresie, ale nie wpływają na RMSE. Jeśli po filtrze zostaje <30% punktów — obniż progi lub wybierz inny segment.

## Interpretacja CdA

- Typowa pozycja TT: **0.20–0.28 m²**
- **CdA względne** (porównanie pozycji/sprzętu) jest wiarygodniejsze niż absolutne, jeśli Crr z presetu nie idealnie pasuje do nawierzchni.
- Suwak **CdA** pozwala ręcznie dopasować VE do wysokości i zobaczyć wpływ na moc przy 40 km/h.
- RMSE VE < 1 m na dobrym segmencie = sensowne dopasowanie.

## Struktura

```
app.py              — interfejs Streamlit
cda_calc/
  tcx_parser.py     — parsowanie TCX
  physics.py        — Virtual Elevation
  filters.py        — filtry prędkość/moc/przyspieszenie
  optimizer.py      — auto-fit CdA
  presets.py        — GP5000 TT Crr
```

## Licencja

MIT (kod aplikacji). Metoda VE: Robert Chung (CC BY 3.0).
