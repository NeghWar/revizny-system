"""Prístup k Supabase databáze — všetky hovory na databázu sú tu."""

import streamlit as st
from supabase import Client, create_client

# Načítanie zo Streamlit secrets (lokálne: .streamlit/secrets.toml;
# v produkcii: Streamlit Cloud → Settings → Secrets).
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


@st.cache_resource
def get_supabase() -> Client:
    """Vráti cachovaného Supabase klienta."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


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