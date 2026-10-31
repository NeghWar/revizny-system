"""Záložka 5: Ročná história vykonaných prác + história porúch + export do Excelu."""

from datetime import date

import streamlit as st

from src.config import POSLEDNA_NAZVY
from src.db import supabase_client as db
from src.services import excel


def render(supabase, vsetky_stroje: list[dict]) -> None:
    st.header("📜 Ročná história vykonaných prác a porúch")

    dnes = date.today()

    # ==================== ROČNÁ HISTÓRIA VYKONANÝCH PRÁC ====================
    st.subheader("✅ Vykonané kontroly podľa rokov")

    roky = list(range(dnes.year, dnes.year - 11, -1))
    zvoleny_rok = st.selectbox("Zvoľte rok:", roky, index=0, key="hist_rok")

    # Načítanie histórie z DB pre zvolený rok
    zaznamy_hist = db.get_historia_rokov(supabase, zvoleny_rok)

    # --- Fallback: ak história v DB nie je, odvodíme ju z aktuálnych "posledná" dátumov ---
    if not zaznamy_hist:
        st.caption(
            "ℹ️ História ešte nie je v databáze — nižšie je prehľad odvodený z "
            "aktuálne uložených dátumov „posledná kontrola“."
        )
        odvodene = []
        for stroj in vsetky_stroje:
            for posl_col, nazov_kontroly in POSLEDNA_NAZVY.items():
                datum_iso = stroj.get(posl_col)
                if not datum_iso:
                    continue
                try:
                    rok_v = int(str(datum_iso)[:4])
                except ValueError:
                    continue
                if rok_v != zvoleny_rok:
                    continue
                odvodene.append({
                    "rok": rok_v,
                    "datum_vykonu": str(datum_iso),
                    "nazov_stroja": stroj.get("nazov"),
                    "evidencne_cislo": stroj.get("evidencne_cislo"),
                    "voj": stroj.get("voj"),
                    "umiestnenie": stroj.get("umiestnenie"),
                    "typ_kontroly": nazov_kontroly,
                })
        zaznamy_hist = odvodene

    if not zaznamy_hist:
        st.info(f"Za rok {zvoleny_rok} nie sú evidované žiadne vykonané kontroly.")
    else:
        st.success(f"Za rok {zvoleny_rok} bolo evidovaných **{len(zaznamy_hist)}** vykonaných kontrol.")
        st.dataframe(
            zaznamy_hist,
            use_container_width=True,
            hide_index=True,
            column_config={
                "rok": "Rok",
                "datum_vykonu": "Dátum vykonania",
                "nazov_stroja": "Názov stroja",
                "evidencne_cislo": "Evidenčné číslo",
                "voj": "VOJ",
                "umiestnenie": "Umiestnenie",
                "typ_kontroly": "Vykonaná kontrola",
            },
        )

        # Export ročnej histórie do Excelu
        excel_data = excel.export_historia_rokov_excel(zaznamy_hist)
        st.download_button(
            label=f"🟢 Stiahnuť históriu za rok {zvoleny_rok} (.xlsx)",
            data=excel_data,
            file_name=f"historia_vykonanych_prac_{zvoleny_rok}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")

    # ==================== HISTÓRIA PORÚCH ====================
    st.subheader("🔧 História porúch (archív poznámok)")
    st.caption(
        "Sem sa automaticky zapisujú staré poznámky pri ich prepise — "
        "aby zostal záznam, kedy a prečo bol stroj v poruche."
    )

    poruchy = db.get_historia_poruch(supabase)
    if not poruchy:
        st.info("Zatiaľ nie sú evidované žiadne záznamy o poruchách.")
    else:
        st.dataframe(
            poruchy,
            use_container_width=True,
            hide_index=True,
            column_config={
                "datum_zapisu": "Dátum zápisu",
                "nazov_stroja": "Názov stroja",
                "evidencne_cislo": "Evidenčné číslo",
                "text_poruchy": "Text poruchy / poznámky",
            },
        )
