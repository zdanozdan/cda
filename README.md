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
cda.enduhub.com     — konfiguracja nginx
deploy/
  cda-streamlit.service — unit systemd
```

## Deploy (cda.enduhub.com)

Produkcja: **Streamlit** za nginx (HTTPS), nasłuch na `127.0.0.1:8502`. Ustawienia serwera w `.streamlit/config.toml`; lokalnie `./run_local.sh` nadpisuje port na **8501**.

### 1. Kod i venv na serwerze

```bash
cd /home/enduhub/enduhub.com/cda
git pull
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest   # opcjonalnie przed restartem
```

### 2. systemd

```bash
sudo cp deploy/cda-streamlit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cda-streamlit
sudo systemctl status cda-streamlit
```

Logi: `journalctl -u cda-streamlit -f`

### 3. nginx + certbot

```bash
sudo cp cda.enduhub.com /etc/nginx/sites-available/cda.enduhub.com
sudo ln -s /etc/nginx/sites-available/cda.enduhub.com /etc/nginx/sites-enabled/
sudo certbot certonly --nginx -d cda.enduhub.com
sudo nginx -t && sudo systemctl reload nginx
```

Plik `cda.enduhub.com` zawiera własne strefy rate limit (`cda_general_limit`, `cda_api_limit`) — nie kolidują ze strefami w `p3.enduhub.com`. Dyrektywa `limit_req_status` jest tylko w `p3.enduhub.com` (nginx pozwala na jedną w kontekście `http`).

### 4. Aktualizacja po zmianach w kodzie

```bash
cd /home/enduhub/enduhub.com/cda
git pull
source .venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart cda-streamlit
```

## Licencja

MIT (kod aplikacji). Metoda VE: Robert Chung (CC BY 3.0).
