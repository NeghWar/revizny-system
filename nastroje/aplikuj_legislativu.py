"""Aplikuje legislatívne pravidlá (periódy) na stroje podľa kategórie.

Použitie (z koreňa projektu):
    python nastroje/aplikuj_legislativu.py            # DRY-RUN (len náhľad + report)
    python nastroje/aplikuj_legislativu.py --zapis    # zapíše zmeny do DB

Pre kategórie, ktoré majú lehotu určenú výrobcom (TPV), sa perióda NEMENÍ —
tie stroje nástroj vypíše na manuálne doplnenie.
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

KOREN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOREN))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from supabase import create_client  # noqa: E402

from src.services.legislativa import navrhni_zmeny, normalizuj  # noqa: E402


def _klient():
    subor = KOREN / ".streamlit" / "secrets.toml"
    data = tomllib.load(subor.open("rb"))
    return create_client(data["SUPABASE_URL"], data["SUPABASE_KEY"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zapis", action="store_true", help="Zapíše zmeny do DB.")
    args = parser.parse_args()

    sb = _klient()
    stroje = sb.table("stroje").select("*").order("nazov").execute().data or []

    print(f"Strojov: {len(stroje)}   režim: {'ZÁPIS' if args.zapis else 'DRY-RUN'}\n")

    riadky_reportu: list[dict] = []
    manualne_podla_kat: dict[str, list[str]] = defaultdict(list)
    nezname_kat: dict[str, int] = defaultdict(int)
    dotknute = 0

    for s in stroje:
        kat_kluc = normalizuj(s.get("druh_systemu")) + " " + normalizuj(s.get("legislativna_skupina"))
        if (s.get("legislativny_druh") or "").strip():
            kat_kluc += "/" + normalizuj(s.get("legislativny_druh"))
        vysledok = navrhni_zmeny(s)
        if vysledok is None:
            nezname_kat[kat_kluc] += 1
            continue

        zmeny, manualne = vysledok
        for k in manualne:
            manualne_podla_kat[kat_kluc].append(f"{s['nazov']} :: {k}")

        if zmeny:
            dotknute += 1
            for stlpec, hodnota in zmeny.items():
                riadky_reportu.append({
                    "nazov_stroja": s["nazov"],
                    "kategoria": kat_kluc,
                    "stlpec": stlpec,
                    "stara_hodnota": "" if s.get(stlpec) is None else s.get(stlpec),
                    "nova_hodnota": "" if hodnota is None else hodnota,
                })
            if args.zapis:
                sb.table("stroje").update(zmeny).eq("id", s["id"]).execute()

    cas = datetime.now().strftime("%Y%m%d_%H%M%S")
    cesta = KOREN / "nastroje" / f"report_legislativa_{cas}.csv"
    with cesta.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["nazov_stroja", "kategoria", "stlpec", "stara_hodnota", "nova_hodnota"])
        w.writeheader()
        w.writerows(riadky_reportu)

    print(f"Strojov so zmenou: {dotknute}   zmien spolu: {len(riadky_reportu)}")
    print(f"Report: {cesta}\n")

    if nezname_kat:
        print("Neznáme kategórie (preskočené):")
        for k, n in sorted(nezname_kat.items()):
            print(f"  {n:3}  {k}")
        print()

    if manualne_podla_kat:
        print("TREBA DOPLNIŤ RUČNE (lehotu určuje výrobca):")
        for k, polozky in sorted(manualne_podla_kat.items()):
            print(f"  [{k}]  {len(polozky)}×")
        print()

    if not args.zapis:
        print(">> Pre zápis spusti znova s --zapis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
