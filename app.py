"""Hlavný vstupný bod aplikácie (entry point).

Stránka je rozdelená na moduly v `src/`:
    - src/config.py                konštanty a konfigurácia kontrol
    - src/db/supabase_client.py    všetky DB hovory
    - src/services/                čistá logika (výpočet termínov, Excel)
    - src/ui/                      Streamlit komponenty a záložky

Tento súbor len nastaví stránku, overí používateľa a vykreslí jednotlivé záložky.
"""

import streamlit as st

from src.db.supabase_client import chyba_klucov, get_stroje, get_supabase
from src.ui.auth import (
    login_zamok,
    odhlasit_sidebar,
    prepni_rezim_sidebar,
    vyber_zariadenia,
)

st.set_page_config(page_title="Revízny Systém Strojov", page_icon="⚙️", layout="wide")

# Režim vieme mať zapísaný aj v URL (napr. ...?rezim=mobil). Vďaka tomu sa po
# otvorení z ikonky na ploche nemusíš znovu pýtať — rovno sa použije mobilný režim.
rezim_z_url = st.query_params.get("rezim")
if rezim_z_url in ("pc", "mobil"):
    st.session_state["rezim"] = rezim_z_url

# 0) Výber režimu (počítač / mobil) — ešte pred prihlásením
vyber_zariadenia()

# Bez prístupových kľúčov k databáze sa zastavíme s jasnou hláškou (nie traceback).
chyba_db = chyba_klucov()
if chyba_db:
    st.error(f"⚠️ **Nepodarilo sa pripojiť k databáze.**\n\n{chyba_db}")
    st.stop()

try:
    supabase = get_supabase()
except Exception as chyba:
    st.error(f"⚠️ **Nepodarilo sa pripojiť k databáze.**\n\n{chyba}")
    st.stop()

# 🔒 Bezpečnostný zámok (st.stop() vnútri, ak používateľ nie je overený)
login_zamok()

# Odhlásenie + prepnutie režimu v bočnom menu
odhlasit_sidebar()
prepni_rezim_sidebar()

# Načítanie všetkých strojov pre potreby všetkých záložiek
vsetky_stroje = get_stroje(supabase)

# --- MOBILNÝ REŽIM: len čítanie, obmedzené záložky ---
if st.session_state.get("rezim") == "mobil":
    st.markdown(
        "<style>.block-container {max-width: 48rem; margin: auto;}</style>",
        unsafe_allow_html=True,
    )
    st.title("⚙️ Revízny systém (mobil)")

    tab_kalendar, tab_po_termine, tab_zoznam = st.tabs([
        "📅 Čo máš v mesiaci",
        "⚠️ Nevykonané",
        "📋 Zoznam strojov",
    ])

    with tab_kalendar:
        from src.ui.tabs import kalendar
        kalendar.render(supabase, vsetky_stroje)

    with tab_po_termine:
        from src.ui.tabs import prehlad
        prehlad.render_po_termine(supabase, vsetky_stroje)

    with tab_zoznam:
        from src.ui.tabs import zoznam
        zoznam.render_kompaktny(supabase, vsetky_stroje)

    st.stop()

# ===================== POČÍTAČOVÝ REŽIM: všetky záložky =====================
st.title("⚙️ Profesionálny Systém Revízií a Prehliadok")

# --- Rozdelenie stránky na päť záložiek ---
tab_prehlad, tab_kalendar, tab_pridat, tab_zoznam, tab_historia = st.tabs([
    "🔔 Prehľad a Upozornenia",
    "📅 Mesačný Kalendár",
    "➕ Pridať / Evidovať Stroj",
    "📋 Zoznam strojov a úprava",
    "📜 Ročná história",
])

with tab_prehlad:
    from src.ui.tabs import prehlad
    prehlad.render(supabase, vsetky_stroje)

with tab_kalendar:
    from src.ui.tabs import kalendar
    kalendar.render(supabase, vsetky_stroje)

with tab_pridat:
    from src.ui.tabs import pridaj
    pridaj.render(supabase, vsetky_stroje)

with tab_zoznam:
    from src.ui.tabs import zoznam
    zoznam.render(supabase, vsetky_stroje)

with tab_historia:
    from src.ui.tabs import historia
    historia.render(supabase, vsetky_stroje)