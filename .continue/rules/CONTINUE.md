# CONTINUE.md — Sprievodca projektom

> Systém revízií a prehliadok strojov (Streamlit + Supabase).
> Tento dokument je určený pre developerov a AI asistentov pracujúcich na projekte.
> Obsahuje architektúru, konvencie a návody na bežné úlohy.

---

## 1. Project Overview

**Profesionálny Systém Revízií a Prehliadok** je interná webová aplikácia na evidenciu strojov a plánovanie zákonných kontrol (revízie, revízne skúšky, úradné/odborné skúšky, geometrické zameranie dráhy). Zameriava sa na zdvíhacie zariadenia, žeriavy a klasifikácie VTZ/UTZ.

**Kľúčové technológie:**
- **UI:** [Streamlit](https://streamlit.io/) (Python)
- **Backend / DB:** [Supabase](https://supabase.com/) (PostgreSQL cez Python SDK)
- **Dáta:** [Pandas](https://pandas.pydata.org/)
- **Excel:** [openpyxl](https://openpyxl.readthedocs.io/) (štýlovanie exportu)
- **Kalendár / dátumy:** štandardný Python `calendar`, `datetime`

**High-level architektúra:** dvojvrstvová aplikácia — Streamlit klient sa pripája priamo na Supabase pomocou credentials zo secrets. Žiadny vlastný backend server. Logika je oddelená na čistú (testovateľnú, bez Streamlit) a UI vrstvu:

```
app.py (entry point)
 └─ src/db/       — všetky DB hovory (Supabase)
 └─ src/services/ — čistá logika (výpočty, Excel)
 └─ src/ui/       — Streamlit komponenty a záložky
```

| Vrstva | Zodpovednosť | Závisí na |
|---|---|---|
| `src/db` | CRUD nad tabuľkami `stroje`, `poznamky_restov` | Supabase SDK |
| `src/services` | Výpočet termínov, kalendárové udalosti, Excel import/export | `src/config` |
| `src/ui` | Vykreslenie záložiek, formulárov, komponentov | `src/db`, `src/services`, Streamlit |

---

## 2. Getting Started

### Prerekvizity
- **Python 3.9+** (odporúčané 3.11+, kvôli `tomllib` v `src/ui/auth.py`)
- Prístup k Supabase projektu (URL + public key)

### Inštalácia
```bash
pip install -r requirements.txt
```
Obsah `requirements.txt`: `streamlit>=1.29`, `pandas>=2.0`, `openpyxl>=3.1`, `supabase>=2.0`.

### Konfigurácia (⚠️ pozor na preklep v názve súboru)
Aplikácia číta tajomstvá z `.streamlit/secrets.toml`:
```toml
MOJE_TAJNE_HESLO = "..."        # heslo na prihlásenie do aplikácie
SUPABASE_URL = "https://<projekt>.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
```
> ⚠️ **Existujúca pasca:** v repozitári je súbor pomenovaný `.streamlit/seacrets.toml` (chybné „a"). Aby ho Streamlit načítal, musí sa volať **`secrets.toml`**. `src/ui/auth.py` hľadá priamo `secrets.toml`.

### Spustenie
```bash
streamlit run app.py
```

### Testy
> ⚠️ **Nutné overiť:** V projekte nie je zavedený `tests/` adresár ani test runner. `src/services/revizie.py` je zámerne bez Streamlit závislostí („dá sa pokryť unit testami"), ale testy zatiaľ neexistujú. Ak pridáš `pytest`, testuj hlavne `vypocitaj_nasledujuci` a `build_udalosti`.

---

## 3. Project Structure

```
app.py                        Entry point — set_page_config, login, načítanie strojov, 4 záložky
requirements.txt              Python závislosti
GEMINI.md                     Detailný kontext (obdoba tohto súboru, pôvodný)
.streamlit/                   Konfigurácia + secrets.toml (pozor na preklep „seacrets")
src/
  config.py                   ⭐ Jediný zdroj pravdy o sledovaných kontrolách (KONTROLY, periódy, SK mesiace)
  db/
    supabase_client.py        Všetky DB hovory (get/insert/update/delete), cachovaný klient
  services/
    revizie.py                Čistá logika: výpočet termínov, parsovanie dátumov, kalendárové udalosti
    excel.py                  Export (štýlovaný .xlsx) a import (SK dátumy → ISO, čistenie floatov)
  ui/
    auth.py                   Prihlásenie cez heslo; číta secrets priamo z disku (bez cache)
    components.py             Zdieľané UI: kalendárový stĺpec, farebné formátovanie dátumov
    tabs/
      prehlad.py              Záložka 1: duálny kalendár + kritické nedoplatky + poznámky
      kalendar.py             Záložka 2: archív/plánovač pre ľubovoľný mesiac a rok
      pridaj.py               Záložka 3: evidencia nového stroja + ochrana proti duplicitám
      zoznam.py               Záložka 4: filtre, Excel export/import, inline úprava a mazanie
```

**Dôležité konfiguračné súbory:** `src/config.py` (definícia kontrol), `.streamlit/secrets.toml` (credentials).

### Databázová schéma (Supabase)

**Tabuľka `stroje`** (hlavná):
- Identifikácia: `id` (PK), `nazov` (unique), `umiestnenie`, `evidencne_cislo`, `cislo_vybavenia`, `firma`, `voj`
- Legislatíva: `druh_systemu` (VTZ/UTZ), `legislativna_skupina`, `legislativny_druh`
- Pre každú kontrolu dvojica `posledna_*` / `nasledujuca_*` (ISO `YYYY-MM-DD`):
  - `revizia` (ročne), `revizna_skuska`, `podrobna_prehliadka_ok` (5 r.), `uradna_skuska`, `odborna_prehliadka`, `odborna_skuska`, `geometria` (10 r.)
- Periódy: `perioda_reviznej_skusky`, `perioda_uradnej_skusky`, `interval_odborna_pr`, `perioda_odbornej_skusky`
- Prepínač: `vykonava_sa_geometria` (bool)

**Tabuľka `poznamky_restov`** (dôvody zameškania):
- `stroj_id` (FK → `stroje.id`), `typ_kontroly` (názov stĺpca „nasledujuca_*"), `text_poznamky`

---

## 4. Development Workflow

### Konvencie
- **Jazyk:** UI, texty a komentáre v **slovenčine**; názvy premenných/funkcií mix SK/EN (`vypocitaj_nasledujuci`, `vsetky_stroje`), ale **DB kľúče vždy slovensky** (`nasledujuca_revizia`). Toto dodržuj.
- **Dátumy:**
  - DB vždy ISO `YYYY-MM-DD` (string).
  - Zobrazenie slovensky `DD.MM.YYYY`.
  - Výpočty cez `datetime.date` / `timedelta`.
- **Vzorec výpočtu termínu:** `nasledujuci = posledny + (roky * 365 - 1) dní`
  - Zámerne o deň skôr než presné výročie — **zachováva existujúce správanie**.
  - Inverzný vzorec v `zoznam.py:_zisti_predvoleny_datum` — pri zmene jednoho treba zmeniť aj druhý, inak vzniká dátumový „drift".
- **Robustnosť:** pri čítaní z DB vždy počítaj s `None` a poskytni fallback (napr. predvolené periódy v `zoznam.py`). DB volania obaľuj `try/except` a chyby zobraz cez `st.error(...)`.

### Build a nasadenie
> ⚠️ **Nutné overiť:** Bez vlastného build kroku — čistý Python. Nasadenie je pravdepodobne na **Streamlit Community Cloud** (chovanie `auth.py` fallback na cloud secrets to naznačuje). Pri nasadení nastav secrets cez *Settings → Secrets* v UI.

### Prispievanie
- Vetvy `master` (main). Commituj malé, logické celky s jasným popisom v SK.
- Pred commitom over, že zmeny v `src/config.py` (nová kontrola) sa premietnu konzistentne do `excel.py`, `revizie.py` a príslušných záložiek.

---

## 5. Key Concepts

- **Kontrola (sledovaná revízia):** definovaná v `src/config.py:KONTROLY` ako `{"nasledujuca_*": "Zobrazovaný názov"}`. Pridanie novej kontroly = úprava `KONTROLY` + `ODPOVEDAJUCE_POSLEDNE` (generuje sa automaticky z kľúča).
- **Semafor status (kalendár):**
  - 🟢 `zelena` — posledná (vykonaná) kontrola padá do zobrazeného mesiaca.
  - 🟠 `oranzova` — nasledujúca kontrola padá do mesiaca a ešte nie je po termíne.
  - 🔴 `cervena` — nasledujúca kontrola v mesiaci a **už je po termíne**.
- **Perióda vs. interval:** väčšina periód je `int` (roky), ale `interval_odborna_pr` je `float` (0.25 / 0.5 / 1.0 / 2.0 / 3.0). Pri importe sa konvertuje cez `konvertuj_periodu`.
- **Poznámka k meškaniu:** viaže sa na konkrétny `(stroj_id, typ_kontroly)` — ukladá sa do `poznamky_restov`.
- **Duplicita:** detekcia je **case-insensitive podľa `nazov`**; pri zhode sa ponúkne prepis (overwrite) existujúceho záznamu namiesto vloženia nového.

**Použité vzory:** oddelenie čistej logiky od UI (testovateľnosť), centralizovaná konfigurácia (`config.py` ako jediný zdroj pravdy), cache klienta (`@st.cache_resource`), session_state na riadenie UI stavu (zvolený deň, režim úpravy, potvrdenie prepisu).

---

## 6. Common Tasks

### Pridať novú sledovanú kontrolu
1. Pridaj stĺpce `posledna_*` a `nasledujuca_*` do tabuľky `stroje` v Supabase.
2. Doplň nový riadok do `KONTROLY` v `src/config.py` (kľúč = stĺpec „nasledujuca_*"). `ODPOVEDAJUCE_POSLEDNE` sa dopočíta automaticky.
3. Doplň stĺpec do `STLPCE_PRE_EXCEL` v `src/services/excel.py`.
4. Doplň pole do formulárov v `src/ui/tabs/pridaj.py` a `src/ui/tabs/zoznam.py` (aj výpočet `vypocitaj_nasledujuci`).
5. Ak treba zobraziť v detaile, doplň do `zoznam.py` (sekcia „Nasledujúce termíny").

### Pridať úpravu/vylepšenie záložky
- Záložka je funkcia `render(supabase, vsetky_stroje)` v `src/ui/tabs/*.py`. `app.py` ju volá v `with st.tabs(...)`.
- DB operácie nevolaj priamo — používaj funkcie z `src/db/supabase_client.py`.
- Po úspešnom zápise volaj `st.rerun()`, aby sa obnovili dáta z DB.

### Pridať/upraviť výpočet termínu
- Uprav `vypocitaj_nasledujuci` v `src/services/revizie.py`.
- ⚠️ Zrkadlové zmeny urob aj v inverznom výpočte `_zisti_predvoleny_datum` v `src/ui/tabs/zoznam.py`.

### Excel export/import
- Export: `excel.export_stroje_excel(stroje) -> bytes`. Poradie stĺpcov = `STLPCE_PRE_EXCEL`.
- Import: `excel.parse_import_subor(subor) -> [{nazov, data}]`. Pri importe sa čistia float artefakty („17.0" → „17") cez `ocisti_float_cislo`.
- ⚠️ Poradie: nové stĺpce v exporte pridávaj **na koniec**, aby staré Excel súbory stále fungovali.

### (Súvisiaca požiadavka) Pridať `evidencne_cislo` / `cislo_vybavenia` do formulára
> Tieto polia **už existujú** v DB schéme a v `zoznam.py`/`excel.py`, ale **chýbajú** v evidenčnom formulári `src/ui/tabs/pridaj.py`. Na ich pridanie stačí:
> 1. V `pridaj.py` do `with st.form(...)` pridať `st.text_input("Evidenčné číslo:")` a `st.text_input("Číslo vybavenia:")`.
> 2. Do `pripravene_novy_stroj` pridať `"evidencne_cislo": evidencne.strip() or None` a `"cislo_vybavenia": vybavenie.strip() or None`.
> 3. Zvážiť doplnenie týchto polí aj do editačného formulára v `zoznam.py`.

---

## 7. Troubleshooting

| Problém | Príčina / Riešenie |
|---|---|
| Heslo sa nenačíta / login nefunguje | Súbor sa volá `seacrets.toml`. **Premenuj na `secrets.toml`.** `auth.py` hľadá presne tento názov. |
| Zmena hesla sa neprejaví | `auth.py` to rieši čítaním TOML priamo z disku pri každom pokuse — uisti sa, že upravuješ správny `secrets.toml` (projektový vs. CWD). |
| `KeyError: 'SUPABASE_URL'` | Chýbajú kľúče v `secrets.toml` (lokálne) alebo v Streamlit Cloud Secrets. |
| `TypeError`/`ValueError` pri výpočtoch termínov | Chýbajúca perióda (`None`) alebo nečitateľný dátum. Použi fallback predvolené hodnoty (vid `zoznam.py`). |
| Dátumy sa posúvajú o deň po uložení | Nekonzistentný inverzný vzorec. Skontroluj `vypocitaj_nasledujuci` a `_zisti_predvoleny_datum`, musia byť presne inverzné (`roky*365 - 1`). |
| Import z Excelu dal „17.0" namiesto „17" | Ošetrené `ocisti_float_cislo`; uisti sa, že stĺpec je v `MAPOVANIE_NA_DB` ako `cislo_vybavenia`/`evidencne_cislo`. |
| `Chýba knižnica 'openpyxl'` | `pip install openpyxl` (je v requirements.txt). |

**Tipy na ladenie:** `st.caption` v `auth.py` zobrazuje zdroj hesla. Chyby Supabase sa propagujú do `st.error`. Cache klienta zrušíš reštartom servera (`@st.cache_resource`).

---

## 8. References

- [Streamlit dokumentácia](https://docs.streamlit.io/)
- [Supabase Python SDK](https://supabase.com/docs/reference/python/introduction)
- [Pandas](https://pandas.pydata.org/docs/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- Interné: `GEMINI.md` (pôvodný detailný kontext vrátane kompletného DB popisu)

---

> 📌 **Poznámky pre údržbu tohto dokumentu:** Sekcie označené „⚠️ Nutné overiť" (testy, nasadenie) over a doplň podľa reality. Pri zmene architektúry (napr. pridanie backend vrstvy) aktualizuj aj sekciu Project Overview.