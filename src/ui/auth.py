"""Bezpečnostný zámok aplikácie — príhlasenie cez heslo zo secrets."""

from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

import streamlit as st

# Koreň projektu odvodíme z umiestnenia tohto súboru (src/ui/auth.py),
# aby sme se nezáviseli od aktuálneho pracovného adresára (CWD).
KOREN_PROJEKTU = Path(__file__).resolve().parents[2]


def _najdi_secrets_subor() -> Path | None:
    """Vráti existujúci secrets.toml (najprv projektový, potom CWD)."""
    kandidati = [
        KOREN_PROJEKTU / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    ]
    for cesta in kandidati:
        if cesta.is_file():
            return cesta
    return None


def _nacitaj_heslo() -> tuple[str | None, str]:
    """Načíta heslo priamo z secrets.toml z disku (bez cachovania).

    `st.secrets` cachuje hodnoty v pamäti servera, takže zmena v súbore
    by sa prejavila len po restarte. Čítame preto TOML priamo z disku
    pri každom pokuse. Fallback na `st.secrets` len vtedy, keď miestny
    súbor neexistuje (typicky Streamlit Cloud → Secrets v UI).

    Návrat: (heslo, popis zdroja) — zdroj sa zobrazí na ladenie.
    """
    subor = _najdi_secrets_subor()
    if subor is not None:
        try:
            with subor.open("rb") as f:
                data = tomllib.load(f)
            heslo = data.get("MOJE_TAJNE_HESLO")
            if heslo is not None:
                return heslo, f"súbor {subor}"
        except (OSError, tomllib.TOMLDecodeError):
            pass

    # Fallback: oblačné secrets (Streamlit Cloud a pod.) — len ak miestny
    # súbor naozaj neexistuje, aby sme nedostali zastaralú hodnotu.
    try:
        return st.secrets.get("MOJE_TAJNE_HESLO"), "Streamlit secrets (cloud)"
    except Exception:
        return None, "žiadny zdroj"


def login_zamok() -> None:
    """Zobrazí príhlasovací formulár, ak používateľ ešte nie je overený.

    Pri nesprávnom hesle pokračuje sa do st.stop() — zvyšok stránky sa nespadne.
    """
    # Heslo čítame pri každom pokuse priamo z disku, aby zmena v secrets.toml
    # sa prejavila bez restartu servera (bez cache na úrovni modulu alebo st.secrets).
    moje_tajne_heslo, zdroj = _nacitaj_heslo()

    if "overeny" not in st.session_state:
        st.session_state.overeny = False

    if not st.session_state.overeny:
        st.title("🔒 Chránený revízny systém")
        st.subheader("Vstup len pre oprávnené osoby")

        if moje_tajne_heslo is None:
            st.error("Heslo sa nepodarilo načítať zo secrets.toml.")
            st.stop()

        zadane_heslo = st.text_input("Zadajte prístupové heslo:", type="password")
        tlacidlo_prihlasit = st.button("Prihlásiť sa")

        # Len na ladenie — ukáže, odkiaľ sa heslo načítalo.
        st.caption(f"🔑 Zdroj hesla: {zdroj}")

        if tlacidlo_prihlasit:
            if zadane_heslo == moje_tajne_heslo:
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


def _nastav_rezim(rezim: str) -> None:
    """Nastaví režim v session a zapíše ho aj do URL (aby ho ikonka 'zapamätala')."""
    st.session_state["rezim"] = rezim
    try:
        st.query_params["rezim"] = rezim
    except Exception:
        pass
    st.rerun()


def vyber_zariadenia() -> None:
    """Pred prihlásením sa opýta, či sa pracuje na počítači alebo na mobile/tablete.

    Podľa voľby sa prispôsobia dostupné záložky a funkcie (mobil = len čítanie).
    Ak je režim už v URL (?rezim=...), otázka sa preskočí.
    """
    if st.session_state.get("rezim"):
        return

    st.title("⚙️ Revízny systém strojov")
    st.subheader("Na akom zariadení budete pracovať?")
    st.caption("Podľa voľby sa prispôsobia dostupné záložky a funkcie.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💻 Notebook / počítač", use_container_width=True, key="btn_rezim_pc"):
            _nastav_rezim("pc")
    with c2:
        if st.button("📱 Mobil / tablet", use_container_width=True, key="btn_rezim_mobil"):
            _nastav_rezim("mobil")

    st.stop()


def prepni_rezim_sidebar() -> None:
    """V bočnom menu ponúkne prepnutie medzi počítačovým a mobilným zobrazením."""
    aktualny = st.session_state.get("rezim", "pc")
    ciel = "mobil" if aktualny == "pc" else "počítač"
    if st.sidebar.button(f"🔄 Prepnúť na {ciel}"):
        _nastav_rezim("mobil" if aktualny == "pc" else "pc")

