"""Záložka 2: Mesačný archív a plánovač — stav revízií pre zvolený mesiac/rok."""

from datetime import date

import streamlit as st

from src.config import KONTROLY, MESIACE_SK, ODPOVEDAJUCE_POSLEDNE
from src.services.revizie import parsuj_datum


def render(supabase, vsetky_stroje: list[dict]) -> None:
    st.header("📅 Inteligentný archív a plánovač podľa mesiacov")
    st.caption("Vyberte si ľubovoľný mesiac a rok pre zobrazenie stavu revízií.")

    dnesny_dt = date.today()

    # --- Selectboxy pre rok a mesiac ---
    c_rok, c_mes = st.columns(2)
    with c_rok:
        roky_na_vyber = list(range(2019, 2100))
        predvoleny_rok_idx = roky_na_vyber.index(dnesny_dt.year) if dnesny_dt.year in roky_na_vyber else 0
        izvoleny_rok = st.selectbox("Vyberte rok:", roky_na_vyber, index=predvoleny_rok_idx, key="arch_rok")

    with c_mes:
        izvoleny_mesiac_nazov = st.selectbox("Vyberte mesiac:", MESIACE_SK, index=dnesny_dt.month - 1, key="arch_mes")
        izvoleny_mesiac_num = MESIACE_SK.index(izvoleny_mesiac_nazov) + 1

    st.subheader(f"📊 Stav revízií pre obdobie: {izvoleny_mesiac_nazov} {izvoleny_rok}")
    nasli_sa_zaznamy = False

    for stroj in vsetky_stroje:
        for stlpec_nasl, nazov_kontroly in KONTROLY.items():
            stlpec_posl = ODPOVEDAJUCE_POSLEDNE.get(stlpec_nasl)
            iso_nasl = stroj.get(stlpec_nasl)
            iso_posl = stroj.get(stlpec_posl) if stlpec_posl else None

            posl_dt = parsuj_datum(iso_posl)
            nasl_dt = parsuj_datum(iso_nasl)

            # 1. PRÍPAD: VYKONANÁ REVIZIA (ZELENÁ ✅) — v mesiaci, kedy bola reálne vykonaná
            if posl_dt and posl_dt.year == izvoleny_rok and posl_dt.month == izvoleny_mesiac_num:
                nasli_sa_zaznamy = True
                pekny_d = posl_dt.strftime('%d.%m.%Y')
                st.success(
                    f"✅ **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) "
                    f"-> **{nazov_kontroly}** [VYKONANÉ]"
                )
                continue  # Ak bola spravená, nevypisujeme ju duplicitne ako plánovanú

            # 2. PRÍPAD: PLÁNOVANÁ REVIZIA (ČERVENÁ 🚨 alebo MODRÁ 🔵)
            if nasl_dt and nasl_dt.year == izvoleny_rok and nasl_dt.month == izvoleny_mesiac_num:
                nasli_sa_zaznamy = True
                pekny_d = nasl_dt.strftime('%d.%m.%Y')

                if nasl_dt < dnesny_dt:
                    st.error(
                        f"🚨 **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) "
                        f"-> **{nazov_kontroly}** [TERMÍN UPLYNUL / NESPLNENÉ]"
                    )
                else:
                    st.info(
                        f"🔵 **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) "
                        f"-> **{nazov_kontroly}** [PLÁNOVANÉ / ČAKÁ NA VYKONANIE]"
                    )

    if not nasli_sa_zaznamy:
        st.caption("Pre toto obdobie nie sú zaznamenané žiadne splnené ani plánované revízie.")