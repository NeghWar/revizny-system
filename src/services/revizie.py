"""Čistá logika výpočtu termínov a kalendárových udalostí (bez UI závysov).

Tento modul je bez Streamlit, takže sa dá jednoducho pokryť unit testami.
"""

from datetime import date, timedelta

from src.config import KONTROLY, ODPOVEDAJUCE_POSLEDNE


def vypocitaj_nasledujuci(posledny_datum: date | None, roky) -> date | None:
    """Vypočíta nasledujúci termín kontrol = posledný + perióda.

    Vzorec (roky * 365 - 1) dní zachováva existujúce správanie aplikácie
    (termín vychádza o deň skôr, než presné výročie).
    """
    if posledny_datum is None:
        return None
    dni = int((roky * 365) - 1)
    return posledny_datum + timedelta(days=dni)


def parsuj_datum(hodnota) -> date | None:
    """Bezpečne prevedie ISO dátum na date; pri zlom/None formáte vráti None."""
    if not hodnota:
        return None
    try:
        return date.fromisoformat(str(hodnota).strip())
    except (ValueError, TypeError):
        return None


def build_udalosti(stroje: list[dict], rok: int, mesiac: int, dnes: date) -> dict[int, list[dict]]:
    """Vytvorí kalendárové udalosti pre jeden mesiac.

    Vráti dict: {den_mesiaca: [udalosť, ...]}, kde každá udalosť má klúče
    "stroj", "miesto", "kontrola", "status" ("zelena" | "oranzova" | "cervena").

    Logika semafora:
      - zelena  = posledná (vykonaná) kontrola padá do tohto mesiaca
      - oranzova = nasledujúca kontrola padá do tohto mesiaca a ešte nie je po termíne
      - cervena  = nasledujúca kontrola padá do tohto mesiaca a JE už po termíne
    """
    udalosti: dict[int, list[dict]] = {}
    for stroj in stroje:
        for stlpec_nasl, nazov_kontroly in KONTROLY.items():
            stlpec_posl = ODPOVEDAJUCE_POSLEDNE.get(stlpec_nasl)
            iso_nasl = stroj.get(stlpec_nasl)
            iso_posl = stroj.get(stlpec_posl) if stlpec_posl else None

            # 1. Vykonaná (zelena) — zobrazí sa v mesiaci, kedy bola reálne vykonaná
            if iso_posl:
                posl_dt = parsuj_datum(iso_posl)
                if posl_dt and posl_dt.year == rok and posl_dt.month == mesiac:
                    den = posl_dt.day
                    udalosti.setdefault(den, []).append({
                        "stroj": stroj["nazov"],
                        "miesto": stroj["umiestnenie"] or "Nezadané",
                        "kontrola": nazov_kontroly,
                        "status": "zelena",
                    })
                    continue

            # 2. Plánovaná — oranzova, alebo cervena ak termín už uplynul
            if iso_nasl:
                nasl_dt = parsuj_datum(iso_nasl)
                if nasl_dt and nasl_dt.year == rok and nasl_dt.month == mesiac:
                    den = nasl_dt.day
                    status = "cervena" if nasl_dt < dnes else "oranzova"
                    udalosti.setdefault(den, []).append({
                        "stroj": stroj["nazov"],
                        "miesto": stroj["umiestnenie"] or "Nezadané",
                        "kontrola": nazov_kontroly,
                        "status": status,
                    })
    return udalosti