"""Legislatívne pravidlá: periódy kontrol podľa kategórie zariadenia.

Zdroje (PDF sú v priečinku `subory/`):
  - VTZ: vyhláška MPSVR SR č. 508/2009 Z. z., príloha č. 7
         (PREHLIADKY A SKÚŠKY TECHNICKÝCH ZARIADENÍ ZDVÍHACÍCH POČAS PREVÁDZKY)
  - UTZ: vyhláška MDPT SR č. 205/2010 Z. z., príloha č. 4, časť 1
         (OVERENIE SPÔSOBILOSTI URČENÝCH TECHNICKÝCH ZARIADENÍ DOPRAVNÝCH A ZDVÍHACÍCH)

Hodnota pravidla pre konkrétnu kontrolu je:
  - číslo (int/float) -> perióda v rokoch,
  - `NEVYKONAVA` (None) -> kontrola sa nevykonáva ("X" vo vyhláške),
  - `VYROBCA` -> lehotu určí výrobca (treba doplniť ručne).

POZNÁMKA: ide o informatívny prepis tabuliek. Pri pochybnostiach over v PDF.
Kategórie, ktoré reálne používaš (VTZ A/b, B/a2, B/i a UTZ Z1.5-Z2.3), sú
skrížené s existujúcimi dátami a sedia.
"""

NEVYKONAVA = None
VYROBCA = "vyrobca"


def _r(revizia, revizna_skuska, uradna_skuska, odborna_prehliadka, odborna_skuska, podrobna_ok):
    """Zostaví pravidlo pre jednu kategóriu (kľúče = stĺpce 'nasledujuca_*')."""
    return {
        "nasledujuca_revizia": revizia,
        "nasledujuca_revizna_skuska": revizna_skuska,
        "nasledujuca_uradna_skuska": uradna_skuska,
        "nasledujuca_odborna_prehliadka": odborna_prehliadka,
        "nasledujuca_odborna_skuska": odborna_skuska,
        "nasledujuca_podrobna_prehliadka_ok": podrobna_ok,
    }


# ---------------------------------------------------------------------------
# UTZ — 205/2010, príloha č. 4, časť 1
#   R = revízia (1 r), RS = revízna skúška, ÚS = opakovaná úradná skúška,
#   OK = prehliadka oceľovej konštrukcie
#   Pre UTZ sa odborná prehliadka a odborná skúška NEVYKONÁVAJÚ (X).
# ---------------------------------------------------------------------------
UTZ_PRAVIDLA: dict[str, dict] = {
    "D1": _r(NEVYKONAVA, 1, 3, NEVYKONAVA, NEVYKONAVA, VYROBCA),
    "D2": _r(VYROBCA, VYROBCA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
    "D3": _r(1, 2, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
    "Z1.1": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.2": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.3": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.4": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.5": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.6": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.7": _r(1, 3, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.8": _r(1, 3, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.9": _r(1, 3, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.10": _r(1, 3, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.11": _r(1, 2, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.12": _r(1, 3, 6, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.13": _r(1, 3, 9, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.14": _r(VYROBCA, VYROBCA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA, 5),
    "Z1.15": _r(VYROBCA, VYROBCA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
    "Z2.1": _r(1, 2, 5, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
    "Z2.2": _r(1, 2, 4, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
    "Z2.3": _r(VYROBCA, VYROBCA, 6, NEVYKONAVA, NEVYKONAVA, NEVYKONAVA),
}


# ---------------------------------------------------------------------------
# VTZ — 508/2009, príloha č. 7 (zdvíhacie)
#   Opakovaná úradná skúška | Odborná prehliadka | Odborná skúška
#   Revízia, revízna skúška a podrobná prehliadka OK sa pri VTZ nevykonávajú.
#   Pozn.: pre trvalé žeriavové dráhy, stavebné/mobilné/lanové/nakladacie/
#   železničné žeriavy a žeriavy v horúcom/agresívnom prostredí platí
#   odborná prehliadka 1 rok a odborná skúška 2 roky.
# ---------------------------------------------------------------------------
def _r_vtz(uradna_skuska, odborna_prehliadka, odborna_skuska):
    return _r(NEVYKONAVA, NEVYKONAVA, uradna_skuska, odborna_prehliadka, odborna_skuska, NEVYKONAVA)


VTZ_PRAVIDLA: dict[str, dict] = {
    # Skupina A
    "A/A": _r_vtz(10, 2, 4),
    "A/B": _r_vtz(10, 1, 2),
    "A/C1": _r_vtz(6, 0.25, 3),
    "A/C2": _r_vtz(10, 0.5, 6),
    "A/C3": _r_vtz(10, 0.5, 6),
    "A/C4": _r_vtz(6, 0.25, 3),
    "A/D1": _r_vtz(10, 0.25, 3),
    "A/D2": _r_vtz(10, VYROBCA, VYROBCA),
    "A/E": _r_vtz(10, 1, 2),
    "A/F": _r_vtz(10, 0.25, 3),
    "A/G": _r_vtz(10, VYROBCA, 1),
    "A/H": _r_vtz(10, VYROBCA, VYROBCA),
    "A/I1": _r_vtz(10, 0.5, 1),
    "A/I2": _r_vtz(10, 0.5, 1),
    "A/J1": _r_vtz(10, VYROBCA, 2),
    "A/J2": _r_vtz(10, VYROBCA, 2),
    "A/K": _r_vtz(6, 0.25, 3),
    # Skupina B (opakovaná úradná skúška sa nevykonáva)
    "B/A1": _r_vtz(NEVYKONAVA, 3, 6),
    "B/A2": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/B": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/C1": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/C2": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/D1": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/D2": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/D3": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/D4": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/E": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/F": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/G": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/H": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "B/I": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    # Skupina C
    "C/A": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "C/B": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "C/C": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
    "C/D": _r_vtz(NEVYKONAVA, VYROBCA, VYROBCA),
}


# ---------------------------------------------------------------------------
# POMOCNÉ FUNKCIE
# ---------------------------------------------------------------------------
def normalizuj(hodnota) -> str:
    """Zjednotí kategóriu: bez medzier, veľké písmená ('Z 1.15' -> 'Z1.15')."""
    if not hodnota:
        return ""
    return "".join(str(hodnota).split()).upper()


def najdi_pravidla(druh_systemu, legislativna_skupina, legislativny_druh=None) -> dict | None:
    """Vráti pravidlá pre danú kategóriu stroja, alebo None (neznáma kategória)."""
    system = normalizuj(druh_systemu)
    if system == "UTZ":
        return UTZ_PRAVIDLA.get(normalizuj(legislativna_skupina))
    if system == "VTZ":
        kluc = f"{normalizuj(legislativna_skupina)}/{normalizuj(legislativny_druh)}"
        return VTZ_PRAVIDLA.get(kluc)
    return None


# Ku ktorej kontrole patrí ktorý stĺpec periódy v DB (None = perióda je pevná).
PERIODA_STLPEC_KONTROLY: dict[str, str | None] = {
    "nasledujuca_revizia": None,
    "nasledujuca_revizna_skuska": "perioda_reviznej_skusky",
    "nasledujuca_uradna_skuska": "perioda_uradnej_skusky",
    "nasledujuca_odborna_prehliadka": "interval_odborna_pr",
    "nasledujuca_odborna_skuska": "perioda_odbornej_skusky",
    "nasledujuca_podrobna_prehliadka_ok": None,
}

# Tieto kontroly sa pri automatickom prepise NIKDY nemažú (z bezpečnostných
# dôvodov) — napr. stroj môže patriť do viacerých kategórií (Essel = Z1.7 + Z2.2),
# takže by sme mu omylom zmazali povinnú kontrolu. Radšej ostane „naviac".
KONTROLY_NEZMAZAT: set[str] = {"nasledujuca_podrobna_prehliadka_ok"}


