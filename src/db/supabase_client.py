"""Prístup k Supabase databáze — všetky hovory na databázu sú tu."""

import streamlit as st
from supabase import Client, create_client

KLUCE = ("SUPABASE_URL", "SUPABASE_KEY")


def chyba_klucov() -> str | None:
    """Vráti zrozumiteľnú hlášku, ak chýbajú prístupové kľúče; inak None.

    Kľúče sa zámerne NEČÍTAJÚ pri importe modulu — inak by aplikácia spadla
    (traceback) skôr, než by sa stihla zobraziť táto hláška.
    """
    chybajuce = []
    for nazov in KLUCE:
        try:
            if not st.secrets.get(nazov):
                chybajuce.append(nazov)
        except Exception:
            chybajuce.append(nazov)

    if not chybajuce:
        return None
    return (
        f"V konfigurácii chýba: **{', '.join(chybajuce)}**.\n\n"
        "Doplň ich do súboru `.streamlit/secrets.toml` (lokálne) alebo do "
        "**Streamlit Cloud → Settings → Secrets**."
    )


@st.cache_resource
def get_supabase() -> Client:
    """Vráti cachovaného Supabase klienta (kľúče sa čítajú až teraz).

    Lokálne: .streamlit/secrets.toml; v produkcii: Streamlit Cloud → Secrets.
    """
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ---------------------------------------------------------------------------
# ČÍTANIE DÁT
# ---------------------------------------------------------------------------
def get_stroje(supabase: Client) -> list[dict]:
    """Načíta všetky stroje z tabuľky 'stroje' (poválené podľa názvu)."""
    try:
        odpoved = supabase.table("stroje").select("*").order("nazov").execute()
        return odpoved.data or []
    except Exception as e:
        st.error(f"Chyba pri načítaní dát: {e}")
        return []


def get_poznamky(supabase: Client) -> list[dict]:
    """Načíta všetky poznámky o meškaniach z tabuľky 'poznamky_restov'."""
    try:
        odpoved = supabase.table("poznamky_restov").select("*").execute()
        return odpoved.data or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# ZÁPIS / ZMENA / MAZANIE (funkcie vyhoďia výnimky — UI ich chytá a zobrazí)
# ---------------------------------------------------------------------------
def insert_stroj(supabase: Client, data: dict) -> None:
    """Prida nový radok do tabuľky 'stroje'."""
    supabase.table("stroje").insert(data).execute()


def update_stroj(supabase: Client, stroj_id, data: dict) -> None:
    """Aktualizuje existujúci radok v tabuľke 'stroje'."""
    supabase.table("stroje").update(data).eq("id", stroj_id).execute()


def delete_stroj(supabase: Client, stroj_id) -> None:
    """Vymaže stroj z tabuľky 'stroje' podľa id."""
    supabase.table("stroje").delete().eq("id", stroj_id).execute()


def insert_poznamka(supabase: Client, data: dict) -> None:
    """Prida novú poznámku k meškaniu do tabuľky 'poznamky_restov'."""
    supabase.table("poznamky_restov").insert(data).execute()


def update_poznamka(supabase: Client, stroj_id, typ_kontroly: str, text: str) -> None:
    """Aktualizuje text existujúcej poznámky o meškaniu."""
    supabase.table("poznamky_restov").update({"text_poznamky": text}).eq(
        "stroj_id", stroj_id
    ).eq("typ_kontroly", typ_kontroly).execute()


# ---------------------------------------------------------------------------
# HISTÓRIA PORÚCH (archív starých poznámok pri prepise)
# ---------------------------------------------------------------------------
def insert_historia_poruchy(
    supabase: Client,
    nazov_stroja: str,
    evidencne_cislo: str | None,
    text_poruchy: str,
) -> None:
    """Zapíše starú poznámku do histórie porúch (automaticky pri prepise)."""
    supabase.table("historia_poruch").insert({
        "nazov_stroja": nazov_stroja,
        "evidencne_cislo": evidencne_cislo,
        "text_poruchy": text_poruchy,
    }).execute()


def get_historia_poruch(supabase: Client) -> list[dict]:
    """Načíta celú históriu porúch (najnovšie prvé)."""
    try:
        odpoved = (
            supabase.table("historia_poruch")
            .select("*")
            .order("datum_zapisu", desc=True)
            .execute()
        )
        return odpoved.data or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# ROČNÁ HISTÓRIA VYKONANÝCH PRÁC
# ---------------------------------------------------------------------------
def insert_historia_rok(
    supabase: Client,
    rok: int,
    datum_vykonu: str,
    nazov_stroja: str,
    evidencne_cislo: str | None,
    voj: str | None,
    umiestnenie: str | None,
    typ_kontroly: str,
) -> None:
    """Zapíše vykonanú kontrolu do ročnej histórie."""
    supabase.table("historia_rokov").insert({
        "rok": rok,
        "datum_vykonu": datum_vykonu,
        "nazov_stroja": nazov_stroja,
        "evidencne_cislo": evidencne_cislo,
        "voj": voj,
        "umiestnenie": umiestnenie,
        "typ_kontroly": typ_kontroly,
    }).execute()


def get_historia_rokov(supabase: Client, rok: int | None = None) -> list[dict]:
    """Načíta históriu vykonaných prác (voliteľne len pre daný rok)."""
    try:
        dotaz = supabase.table("historia_rokov").select("*")
        if rok is not None:
            dotaz = dotaz.eq("rok", rok)
        odpoved = dotaz.order("datum_vykonu", desc=True).execute()
        return odpoved.data or []
    except Exception:
        return []