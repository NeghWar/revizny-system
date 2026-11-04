"""Jednorazovy nastroj na prepocet terminov v Supabase.

Prepocita vsetky stlpce 'nasledujuca_*' v tabulke 'stroje' podla noveho
kalendarneho pravidla (presna perioda, bez odpoctu 1 dna) - vid
`src/services/revizie.py -> vypocitaj_nasledujuci()`.

Termin sa pocita vyhradne z datumu "posledna" + perioda:
    - nasledujuca_revizia               <- posledna_revizia + 1 rok
    - nasledujuca_revizna_skuska        <- posledna_revizna_skuska + perioda_reviznej_skusky
    - nasledujuca_podrobna_prehliadka_ok<- posledna_podrobna_prehliadka_ok + 5 rokov
    - nasledujuca_uradna_skuska         <- posledna_uradna_skuska + perioda_uradnej_skusky
    - nasledujuca_odborna_prehliadka    <- posledna_odborna_prehliadka + interval_odborna_pr
    - nasledujuca_odborna_skuska        <- posledna_odborna_skuska + perioda_odbornej_skusky
    - nasledujuca_geometria             <- posledna_geometria + 10 rokov

STROJE, KTORÉ NEMAJÚ VYPLNENÚ "POSLEDNÚ" KONTROLU, SA NEPREPOČÍTAVAJÚ
(termin nema z coho vychadzat).

POZOR: kontrola s prázdnym ďalším termínom (ale vyplnenou poslednou) sa berie ako
„neopakuje sa" (nastavené v aplikácii pri stroji) a štandardne sa PRESKAKUJE.
Ak ich chceš násilne prepnúť na ďalší termín, použi prepínač --vratane-vypnutych.

Pouzitie (spustaj z korena projektu):

    python nastroje/prepocitaj_terminy.py            # DRY-RUN (len vypise zmeny + report)
    python nastroje/prepocitaj_terminy.py --zapis    # zapise zmeny do databazy

Vzdy sa vytvori aj CSV report zmien (stara -> nova hodnota), takze zapis
je spatne dohladatelny:  nastroje/report_prepoctu_<datum>.csv
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

# Aby fungoval import "from src..." aj pri priamom spusteni skriptu.
KOREN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOREN))

# Windows konzola casto nezvladne UTF-8 -> prepnime vystup, ak sa da.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from supabase import create_client  # noqa: E402

from src.services.revizie import parsuj_datum, vypocitaj_nasledujuci  # noqa: E402

# (nasledujuci_stlpec, posledny_stlpec, stlpec_s_periodou | None, default_perioda_v_rokoch)
PERIODY: list[tuple[str, str, str | None, float]] = [
    ("nasledujuca_revizia", "posledna_revizia", None, 1),
    ("nasledujuca_revizna_skuska", "posledna_revizna_skuska", "perioda_reviznej_skusky", 2),
    ("nasledujuca_podrobna_prehliadka_ok", "posledna_podrobna_prehliadka_ok", None, 5),
    ("nasledujuca_uradna_skuska", "posledna_uradna_skuska", "perioda_uradnej_skusky", 5),
    ("nasledujuca_odborna_prehliadka", "posledna_odborna_prehliadka", "interval_odborna_pr", 1.0),
    ("nasledujuca_odborna_skuska", "posledna_odborna_skuska", "perioda_odbornej_skusky", 1),
    ("nasledujuca_geometria", "posledna_geometria", None, 10),
]

# Hranica (v dnoch), nad ktorou uz zmenu oznacime za "velky rozdiel".
HRANICA_VELKY_ROZDIEL_DNI = 31


def _nacitaj_klienta():
    """Vytvori Supabase klienta z .streamlit/secrets.toml (rovnako ako aplikacia).

    Pouziva serverovy "secret" kluc (SUPABASE_SECRET_KEY, obchadza RLS).
    Stary SUPABASE_KEY ponechavame len ako nudzovy fallback pocas prechodu.
    """
    secrets_subor = KOREN / ".streamlit" / "secrets.toml"
    if not secrets_subor.is_file():
        raise SystemExit(f"Chyba subor s klucmi: {secrets_subor}")
    with secrets_subor.open("rb") as f:
        data = tomllib.load(f)
    url = data.get("SUPABASE_URL")
    key = data.get("SUPABASE_SECRET_KEY") or data.get("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit(
            "V secrets.toml chyba SUPABASE_URL alebo SUPABASE_SECRET_KEY."
        )
    return create_client(url, key)


def _perioda(stroj: dict, perioda_stlpec: str | None, default: float) -> float:
    """Vrati periodu stroja z DB, alebo nahradnu hodnotu, ak chyba."""
    if perioda_stlpec is None:
        return default
    hodnota = stroj.get(perioda_stlpec)
    if hodnota in (None, ""):
        return default
    try:
        return float(hodnota)
    except (TypeError, ValueError):
        return default


def _kategoria(stara: str | None, posun_dni: int | None) -> str:
    """Zaradi zmenu do kategorie pre report."""
    if stara is None:
        return "doplnene"
    if posun_dni is None:
        return "nezname"
    if abs(posun_dni) > HRANICA_VELKY_ROZDIEL_DNI:
        return "velky_rozdiel"
    return "posun_dni"


def _zapis_report(riadky: list[dict]) -> Path:
    """Zapise CSV report zmien vedla skriptu a vrati cestu."""
    cas = datetime.now().strftime("%Y%m%d_%H%M%S")
    cesta = KOREN / "nastroje" / f"report_prepoctu_{cas}.csv"
    with cesta.open("w", newline="", encoding="utf-8-sig") as f:
        zapis = csv.DictWriter(
            f,
            fieldnames=["nazov_stroja", "stlpec", "stara_hodnota", "nova_hodnota", "posun_dni", "kategoria"],
        )
        zapis.writeheader()
        for r in riadky:
            zapis.writerow(r)
    return cesta


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepocet nasledujucich terminov v DB.")
    parser.add_argument(
        "--zapis",
        action="store_true",
        help="Zapise zmeny do databazy (bez tohto prepinaca ide len o dry-run).",
    )
    parser.add_argument(
        "--vratane-vypnutych",
        action="store_true",
        help=(
            "Prepocita aj kontroly s prazdnym dalsim terminom (v aplikacii oznacene "
            "ako 'neopakuje sa'). Bez tohoto prepinaca sa take kontroly preskakuju."
        ),
    )
    args = parser.parse_args()

    supabase = _nacitaj_klienta()
    odpoved = supabase.table("stroje").select("*").order("nazov").execute()
    stroje = odpoved.data or []

    print(f"Nacitanych strojov: {len(stroje)}")
    print("Rezim:", "ZAPIS DO DB" if args.zapis else "DRY-RUN (nic sa nezapise)")
    print("-" * 70)

    riadky_reportu: list[dict] = []
    pocet_dotknutych_strojov = 0
    kategorie = {"doplnene": 0, "posun_dni": 0, "velky_rozdiel": 0, "nezname": 0}

    for stroj in stroje:
        zmeny: dict[str, str | None] = {}
        for nasl_col, posl_col, per_col, default in PERIODY:
            posl_dt = parsuj_datum(stroj.get(posl_col))
            if posl_dt is None:
                # Bez datumu "posledna" sa nic neprepocitava.
                continue

            perioda = _perioda(stroj, per_col, default)
            novy = vypocitaj_nasledujuci(posl_dt, perioda)
            novy_iso = novy.isoformat() if novy else None
            stary_iso = stroj.get(nasl_col)

            # Ak je ďalší termín prázdny a posledná kontrola vyplnená, znamená to,
            # že kontrola sa na stroji NEOpakuje (nastavené v aplikácii) — nechávame tak.
            if stary_iso is None and not args.vratane_vypnutych:
                continue

            if novy_iso != stary_iso:
                zmeny[nasl_col] = novy_iso

                posun_dni = None
                stary_dt = parsuj_datum(stary_iso)
                if stary_dt and novy:
                    posun_dni = (novy - stary_dt).days

                kateg = _kategoria(stary_iso, posun_dni)
                kategorie[kateg] = kategorie.get(kateg, 0) + 1
                riadky_reportu.append({
                    "nazov_stroja": stroj["nazov"],
                    "stlpec": nasl_col,
                    "stara_hodnota": stary_iso if stary_iso is not None else "",
                    "nova_hodnota": novy_iso if novy_iso is not None else "",
                    "posun_dni": posun_dni if posun_dni is not None else "",
                    "kategoria": kateg,
                })
                print(f"  {stroj['nazov']}: {nasl_col}: {stary_iso} -> {novy_iso}")

        if zmeny:
            pocet_dotknutych_strojov += 1
            if args.zapis:
                supabase.table("stroje").update(zmeny).eq("id", stroj["id"]).execute()

    cesta_reportu = _zapis_report(riadky_reportu)

    print("-" * 70)
    print(f"Strojov so zmenou: {pocet_dotknutych_strojov}")
    print(f"Zmenenych terminov spolu: {len(riadky_reportu)}")
    print(f"  - doplnene (chybajuce):        {kategorie['doplnene']}")
    print(f"  - maly posun (<= {HRANICA_VELKY_ROZDIEL_DNI} dni):    {kategorie['posun_dni']}")
    print(f"  - velky rozdiel (> {HRANICA_VELKY_ROZDIEL_DNI} dni):     {kategorie['velky_rozdiel']}")
    print(f"Report zmien: {cesta_reportu}")
    if not args.zapis:
        print(">> Pre ostry zapis spusti znova s parametrom --zapis")
    else:
        print("OK - zmeny boli zapisane do databazy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
