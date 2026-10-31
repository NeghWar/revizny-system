"""Konfigurácia a konštanty aplikácie — jediný zdroj pravdy o sledovaných kontrolách."""

# Rozvrhnutie sledovaných kontrol.
# Klúč  = stĺpec "nasledujúci termín" v databáze
# Hodnota = zobrazované meno v aplikácii
# Poradie tu určuje poradie v kalendári aj v Excel hlavičke (za stĺpcom VOJ).
KONTROLY: dict[str, str] = {
    "nasledujuca_revizia": "Revízia (ročne)",
    "nasledujuca_revizna_skuska": "Revízna skúška",
    "nasledujuca_uradna_skuska": "Úradná skúška",
    "nasledujuca_odborna_prehliadka": "Odborná prehliadka",
    "nasledujuca_odborna_skuska": "Odborná skúška",
    "nasledujuca_podrobna_prehliadka_ok": "Podrobná prehliadka OK (5-ročne)",
    "nasledujuca_geometria": "Geometrické zameranie dráhy (10 rokov)",
}

# Odpovedajúce stĺpce "posledná vykonaná" pre každý stĺpec "nasledujúca" (generované).
ODPOVEDAJUCE_POSLEDNE: dict[str, str] = {
    k: "posledna_" + k[len("nasledujuca_"):] for k in KONTROLY
}

# Ľudské názvy pre stĺpce "posledná" (použijú sa pri zápise do ročnej histórie).
POSLEDNA_NAZVY: dict[str, str] = {
    "posledna_revizia": "Revízia",
    "posledna_revizna_skuska": "Revízna skúška",
    "posledna_uradna_skuska": "Úradná skúška",
    "posledna_odborna_prehliadka": "Odborná prehliadka",
    "posledna_odborna_skuska": "Odborná skúška",
    "posledna_podrobna_prehliadka_ok": "Podrobná prehliadka OK",
    "posledna_geometria": "Geometria dráhy",
}

# Dátové stĺpce periód v databáze (využia sa pri Excel exporte/importe).
PERIODA_STLPCE: dict[str, str] = {
    "perioda_reviznej_skusky": "Perióda Revíznej skúšky (roky)",
    "perioda_uradnej_skusky": "Perióda Úradnej skúšky (roky)",
    "interval_odborna_pr": "Interval Odborná prehliadka (roky)",
    "perioda_odbornej_skusky": "Perióda Odborná skúška (roky)",
}

# Slovenské názvy mesiacov a dní pre kalendáre.
MESIACE_SK = [
    "Január", "Február", "Marec", "Apríl", "Máj", "Jún",
    "Júl", "August", "September", "Október", "November", "December",
]

DNI_V_TYZDNU = ["Po", "Ut", "St", "Št", "Pi", "So", "Ne"]