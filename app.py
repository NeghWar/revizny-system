"""Hlavný vstupný bod aplikácie (entry point).

Stránka je rozdelená na moduly v `src/`:
    - src/config.py                konštanty a konfigurácia kontrol
    - src/db/supabase_client.py    všetky DB hovory
    - src/services/                čistá logika (výpočet termínov, Excel)
    - src/ui/                      Streamlit komponenty a záložky

Tento súbor len nastaví stránku, overí používateľa a vykreslí jednotlivé záložky.
"""

import streamlit as st

from src.db.supabase_client import get_stroje, get_supabase
from src.ui.auth import login_zamok, odhlasit_sidebar

st.set_page_config(page_title="Revízny Systém Strojov", page_icon="⚙️", layout="wide")

supabase = get_supabase()

# 🔒 Bezpečnostný zámok (st.stop() vnútri, ak používateľ nie je overený)
login_zamok()

# Tlačidlo na odhlásenie v bočnom menu
odhlasit_sidebar()

# Načítanie všetkých strojov pre potreby všetkých záložiek
vsetky_stroje = get_stroje(supabase)

st.title("⚙️ Profesionálny Systém Revízií a Prehliadok")

# --- Rozdelenie stránky na štyri záložky ---
tab_prehlad, tab_kalendar, tab_pridat, tab_zoznam = st.tabs([
    "🔔 Prehľad a Upozornenia",
    "📅 Mesačný Kalendár",
    "➕ Pridať / Evidovať Stroj",
    "📋 Zoznam strojov a úprava",
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