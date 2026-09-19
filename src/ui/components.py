"""Zdieľané UI komponenty (kalendárový stĺpec, formátovanie termínov)."""

import calendar
from datetime import date

import streamlit as st

from src.config import DNI_V_TYZDNU, MESIACE_SK


def render_kalendar_stlpec(
    udalosti: dict[int, list[dict]],
    rok: int,
    mesiac: int,
    key_prefix: str,
    zvoleny_typ: str,
    emoji: str,
    titul: str,
    farba: str,
) -> None:
    """Zobrazí jeden kalendárový stĺpec (7-dňový grido + detail zvoleného dňa)."""
    with st.container(border=True):
        st.markdown(
            f"<h4 style='text-align:center; color:{farba}; margin-top:0;'>"
            f"{emoji} {titul}: {MESIACE_SK[mesiac - 1]} {rok}</h4>",
            unsafe_allow_html=True,
        )

        # Hlavička dní týždna
        st_cols_dni = st.columns(7)
        for i, d_nazov in enumerate(DNI_V_TYZDNU):
            st_cols_dni[i].markdown(
                f"<p style='text-align:center; font-weight:bold; margin-bottom:5px; color:#555;'>{d_nazov}</p>",
                unsafe_allow_html=True,
            )

        # Grido s dňami (0 = prázdna bunka mimo mesiaca)
        cal = calendar.Calendar(firstweekday=0)
        for tyzden in cal.monthdayscalendar(rok, mesiac):
            st_cols = st.columns(7)
            for i, den in enumerate(tyzden):
                if den == 0:
                    st_cols[i].write("")
                    continue

                label_text = f"{den}"
                if den in udalosti:
                    statusy = [u["status"] for u in udalosti[den]]
                    if "cervena" in statusy:
                        label_text = f"{den} 🚨"
                    elif "oranzova" in statusy:
                        label_text = f"{den} ⏳"
                    elif "zelena" in statusy:
                        label_text = f"{den} ✅"

                if st_cols[i].button(label_text, key=f"{key_prefix}_{den}", use_container_width=True):
                    st.session_state["zvoleny_den_duany"] = den
                    st.session_state["zvoleny_typ_mesiaca"] = zvoleny_typ
                    st.rerun()

        # Detail pre zvolený deň
        zvoleny_den = st.session_state.get("zvoleny_den_duany")
        if zvoleny_den and st.session_state.get("zvoleny_typ_mesiaca") == zvoleny_typ:
            st.markdown("---")
            st.markdown(f"##### 🔍 Podrobnosti pre: **{zvoleny_den}. {MESIACE_SK[mesiac - 1]}**")

            if zvoleny_den in udalosti:
                for u in udalosti[zvoleny_den]:
                    if u["status"] == "zelena":
                        st.success(f"✅ **{u['stroj']}** — *{u['kontrola']}*")
                    elif u["status"] == "cervena":
                        st.error(f"🚨 **{u['stroj']}** — *{u['kontrola']}*")
                    else:
                        st.info(f"⏳ **{u['stroj']}** — *{u['kontrola']}*")
            else:
                st.success("Žiadne plánované revízie. 👍")

            if st.button("✖️ Zatvoriť", key=f"close_detail_{key_prefix}", use_container_width=True):
                st.session_state["zvoleny_den_duany"] = None
                st.session_state["zvoleny_typ_mesiaca"] = None
                st.rerun()


def formatuj_datum_s_farbou(iso_datum, dnesny_den) -> str:
    """Vráti HTML span s farbou semafora pre jeden termín.

    - červená: termín uplynul (PO TERMÍNE)
    - zelená : termín je platný
    - šedá   : hodnota chýba alebo je nečitateľná („nevykonáva sa")
    """
    if iso_datum:
        try:
            termin_date = date.fromisoformat(str(iso_datum).strip())
            r, m, d = str(iso_datum).split("-")
            pekny_format = f"{d}.{m}.{r}"
            if termin_date < dnesny_den:
                return f"<span style='color:#ff4b4b; font-weight:bold;'>{pekny_format} (PO TERMÍNE! 🚨)</span>"
            return f"<span style='color:#09ab3b; font-weight:bold;'>{pekny_format} (Platná ✅)</span>"
        except Exception:
            return "<span style='color:#777777;'>*nevykonáva sa*</span>"
    return "<span style='color:#777777;'>*nevykonáva sa*</span>"