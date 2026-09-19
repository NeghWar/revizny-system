"""Bezpečnostný zámok aplikácie — príhlasenie cez heslo zo secrets."""

import streamlit as st

MOJE_TAJNE_HESLO: str = st.secrets["MOJE_TAJNE_HESLO"]


def login_zamok() -> None:
    """Zobrazí príhlasovací formulár, ak používateľ ešte nie je overený.

    Pri nesprávnom hesle pokračuje sa do st.stop() — zvyšok stránky sa nespadne.
    """
    if "overeny" not in st.session_state:
        st.session_state.overeny = False

    if not st.session_state.overeny:
        st.title("🔒 Chránený revízny systém")
        st.subheader("Vstup len pre oprávnené osoby")

        zadane_heslo = st.text_input("Zadajte prístupové heslo:", type="password")
        tlacidlo_prihlasit = st.button("Prihlásiť sa")

        if tlacidlo_prihlasit:
            if zadane_heslo == MOJE_TAJNE_HESLO:
                st.session_state.overeny = True
                st.rerun()
            else:
                st.error("Nesprávne heslo! Prístup odmietnutý.")

        st.stop()


def odhlasit_sidebar() -> None:
    """Tlačidlo na odhlásenie v bočnom menu."""
    if st.sidebar.button("🔒 Odhlásiť sa"):
        st.session_state.overeny = False
        st.rerun()