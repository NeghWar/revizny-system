"""Záložka 1: Prehľad a upozornenia — duálny kalendár + kritické nedoplatky + poznámky."""

from datetime import date

import streamlit as st

from src.config import KONTROLY
from src.db import supabase_client as db
from src.services.revizie import build_udalosti, parsuj_datum
from src.ui.components import render_kalendar_stlpec


def najdi_poznamku(vsetky_poznamky: list[dict], s_id, t_kontroly: str) -> str | None:
    """Nájde text poznámky pre daný stroj + typ kontroly, alebo None."""
    for p in vsetky_poznamky:
        if p["stroj_id"] == s_id and p["typ_kontroly"] == t_kontroly:
            return p["text_poznamky"]
    return None


def render(supabase, vsetky_stroje: list[dict]) -> None:
    st.header("🔔 Inteligentný prehľad a semafor revízií")

    dnes = date.today()
    akt_mesiac = dnes.month
    akt_rok = dnes.year

    if akt_mesiac == 12:
        nasl_mesiac = 1
        nasl_rok = akt_rok + 1
    else:
        nasl_mesiac = akt_mesiac + 1
        nasl_rok = akt_rok

    # Načítanie existujúcich poznámok z databázy
    vsetky_poznamky = db.get_poznamky(supabase)

    # Semaforové udalosti pre oba mesiace
    udalosti_aktualny = build_udalosti(vsetky_stroje, akt_rok, akt_mesiac, dnes)
    udalosti_buduci = build_udalosti(vsetky_stroje, nasl_rok, nasl_mesiac, dnes)

    if "zvoleny_den_duany" not in st.session_state:
        st.session_state["zvoleny_den_duany"] = None
    if "zvoleny_typ_mesiaca" not in st.session_state:
        st.session_state["zvoleny_typ_mesiaca"] = None

    # Duálny kalendár: aktuálny a nasledujúci mesiac
    col_kal1, col_kal2 = st.columns(2)
    with col_kal1:
        render_kalendar_stlpec(
            udalosti_aktualny, akt_rok, akt_mesiac,
            "cal_akt", "aktualny", "📅", "Aktuálny mesiac", "#1F4E78",
        )
    with col_kal2:
        render_kalendar_stlpec(
            udalosti_buduci, nasl_rok, nasl_mesiac,
            "cal_nasl", "buduci", "⏭️", "Nasledujúci mesiac", "#2E7D32",
        )

    # --- KRITICKÉ UPOZORNENIA Z MINULOSTI ---
    st.markdown("<br><br>", unsafe_allow_html=True)  # Decentná medzera na oddelenie
    st.subheader("🚨 Kritické nedoplatky (Zameškané z minulých mesiacov)")
    nasli_sa_stare_resty = False

    for stroj in vsetky_stroje:
        for stlpec, nazov_kontroly in KONTROLY.items():
            termin = parsuj_datum(stroj.get(stlpec))
            # Sledujeme len tie termíny, ktoré sú staršie ako začiatok aktuálneho mesiaca
            if termin and termin < date(akt_rok, akt_mesiac, 1):
                nasli_sa_stare_resty = True
                dni_po = (dnes - termin).days
                stroj_id = stroj["id"]

                st.error(
                    f"❌ **{stroj['nazov']}** ({stroj['umiestnenie']}) -> **{nazov_kontroly}** "
                    f"mala byť hotová do **{termin.strftime('%d.%m.%Y')}** (Mešká už {dni_po} dní!)"
                )

                existujuca_poznamka = najdi_poznamku(vsetky_poznamky, stroj_id, stlpec)
                if existujuca_poznamka:
                    st.info(f"ℹ️ **Dôvod zameškania:** {existujuca_poznamka}")

                with st.expander("📝 Upraviť poznámku k zdôvodneniu meškania"):
                    with st.form(key=f"form_poznamka_{stroj_id}_{stlpec}"):
                        nova_poznamka = st.text_area(
                            "Dôvod (napr. Stroj v poruche, čaká sa na diel / dohodnutý termín):",
                            value=existujuca_poznamka if existujuca_poznamka else "",
                            key=f"txt_{stroj_id}_{stlpec}",
                        )
                        tlacidlo_ulozit_p = st.form_submit_button("💾 Uložiť dôvod")

                        if tlacidlo_ulozit_p:
                            try:
                                if existujuca_poznamka:
                                    db.update_poznamka(supabase, stroj_id, stlpec, nova_poznamka)
                                else:
                                    db.insert_poznamka(supabase, {
                                        "stroj_id": stroj_id,
                                        "typ_kontroly": stlpec,
                                        "text_poznamky": nova_poznamka,
                                    })
                                st.toast("Poznámka bola úspešne uložená! 📝")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Chyba pri ukladaní: {err}")
                st.write("")

    if not nasli_sa_stare_resty:
        st.success("Skvelé! Nemáte žiadne staré zameškané revízie z minulých mesiacov. 🎉")