"""Konfigurácia a konštanty aplikácie — jediný zdroj pravdy o sledovaných kontrolách."""

# Rozvrhnutie sledovaných kontrol.
# Klúč  = stĺpec "nasledujúci termín" v databáze
# Hodnota = zobrazované meno v aplikácii
KONTROLY: dict[str, str] = {
    "nasledujuca_revizia": "Revízia (ročne)",
    "nasledujuca_revizna_skuska": "Revízna skúška",
    "nasledujuca_podrobna_prehliadka_ok": "Podrobná prehliadka OK (5-ročne)",
    "nasledujuca_uradna_skuska": "Úradná skúška",
    "nasledujuca_odborna_prehliadka": "Odborná prehliadka",
    "nasledujuca_odborna_skuska": "Odborná skúška (ročne)",
    "nasledujuca_geometria": "Geometrické zameranie dráhy (10 rokov)",
}

# Odpovedajúce stĺpce "posledná vykonaná" pre každý stĺpec "nasledujúca" (generované).
ODPOVEDAJUCE_POSLEDNE: dict[str, str] = {
    k: "posledna_" + k[len("nasledujuca_"):] for k in KONTROLY
}

# Dátové stĺpce periód v databáze (využia sa pri Excel exporte/importe).
PERIODA_STLPCE: dict[str, str] = {
    "perioda_reviznej_skusky": "Perióda Revíznej skúšky (roky)",
    "perioda_uradnej_skusky": "Perióda Úradnej skúšky (roky)",
    "interval_odborna_pr": "Interval Odbornéj prehliadky (roky)",
    "perioda_odbornej_skusky": "Perióda Odbornéj skúšky (roky)",
}

# Slovenské názvy mesiacov a dní pre kalendáre.
MESIACE_SK = [
    "Január", "Február", "Marec", "Apríl", "Máj", "Jún",
    "Júl", "August", "September", "Október", "November", "December",
]

DNI_V_TYZDNU = ["Po", "Ut", "St", "Št", "Pi", "So", "Ne"]