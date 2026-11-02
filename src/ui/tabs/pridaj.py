"""Záložka 3: Evidencia nového stroja + ochrana proti duplicitám."""

import streamlit as st

from src.db import supabase_client as db
from src.services import legislativa
from src.services.revizie import vypocitaj_nasledujuci


def render(supabase, vsetky_stroje: list[dict]) -> None:
    st.header("Evidencia nového stroja do systému")

    # Inicializácia stavov pre kontrolu prepisu
    if "stroj_na_prepis_id" not in st.session_state:
        st.session_state["stroj_na_prepis_id"] = None
    if "stroj_na_prepis_data" not in st.session_state:
        st.session_state["stroj_na_prepis_data"] = None
    if "stroj_na_prepis_nazov" not in st.session_state:
        st.session_state["stroj_na_prepis_nazov"] = None

    # --- BLOK PRE POTVRDENIE (Ak sa zistila duplicita, zobrazí sa IBA toto) ---
    if st.session_state["stroj_na_prepis_id"] is not None:
        dup_id = st.session_state["stroj_na_prepis_id"]
        dup_nazov = st.session_state["stroj_na_prepis_nazov"]
        dup_data = st.session_state["stroj_na_prepis_data"]

        st.warning(f"⚠️ **Upozornenie:** Zariadenie s názvom **'{dup_nazov}'** sa už v systéme nachádza.")
        st.write("Chcete pôvodný stroj nahradiť týmito novými údajmi a nanovo prepočítať termíny?")

        c_dup1, c_dup2 = st.columns(2)
        with c_dup1:
            if st.button("🔄 Áno, prepísať starý záznam", key=f"btn_overwrite_confirm_{dup_id}", use_container_width=True):
                try:
                    db.update_stroj(supabase, dup_id, dup_data)
                    st.toast(f"Stroj '{dup_nazov}' bol úspešne prepísaný! 💾")

                    # Kompletný reset a návrat k formuláru
                    st.session_state["stroj_na_prepis_id"] = None
                    st.session_state["stroj_na_prepis_data"] = None
                    st.session_state["stroj_na_prepis_nazov"] = None
                    st.rerun()
                except Exception as err:
                    st.error(f"Nepodarilo sa prepísať stroj: {err}")

        with c_dup2:
            if st.button("❌ Nie, ponechať pôvodný", key=f"btn_overwrite_cancel_{dup_id}", use_container_width=True):
                # Reset bez zápisu
                st.session_state["stroj_na_prepis_id"] = None
                st.session_state["stroj_na_prepis_data"] = None
                st.session_state["stroj_na_prepis_nazov"] = None
                st.info("Pôvodný stroj zostal v databáze nezmenený.")
                st.rerun()

    else:
        # --- VOĽBA KATEGÓRIE (mimo formulára, aby vedela ovplyvniť periódy) ---
        st.markdown("**1) Kategória zariadenia** — podľa nej sa doplnia periódy z vyhlášky:")
        c_k1, c_k2, c_k3 = st.columns(3)
        with c_k1:
            druh_systemu = st.selectbox("Druh systému:", ["-", "VTZ", "UTZ"], key="add_druh_systemu")
        with c_k2:
            legislativna_skupina = st.text_input(
                "Legislatívna skupina:", key="add_leg_skupina", placeholder="Napr. Z1.7 / B"
            )
        with c_k3:
            legislativny_druh = st.text_input(
                "Legislatívny druh (pri VTZ):", key="add_leg_druh", placeholder="Napr. i / b"
            )

        pravidla = legislativa.najdi_pravidla(
            druh_systemu if druh_systemu != "-" else None, legislativna_skupina, legislativny_druh
        )
        if pravidla:
            st.success("✅ Kategória rozpoznaná — periódy a „nevykonáva sa\" sa doplnia podľa vyhlášky.")
        elif druh_systemu != "-" and (legislativna_skupina or "").strip():
            st.warning("⚠️ Pre túto kategóriu pravidlá nemám — periódy nastav ručne.")

        def _idx(kontrola: str, ponuka: list, fallback):
            """Index do 'ponuka' podľa legislatívneho pravidla (inak 'fallback')."""
            if pravidla and kontrola in pravidla:
                hodnota = pravidla[kontrola]
                if hodnota is None:  # nevykonáva sa
                    if 0 in ponuka:
                        return ponuka.index(0)
                elif isinstance(hodnota, (int, float)):
                    for i, v in enumerate(ponuka):
                        if float(v) == float(hodnota):
                            return i
            return ponuka.index(fallback)

        st.markdown("---")

        # --- ŠTANDARDNÝ FORMULÁR PRE EVIDENCIU ---
        with st.form(key="novy_stroj_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nazov = st.text_input("Názov stroja / zariadenia:", placeholder="Napr. Mostový žeriav 5t")
            with col2:
                umiestnenie = st.text_input("Umiestnenie (Hala / Stanovište):", placeholder="Napr. Hala A - expedícia")

            col_id1, col_id2 = st.columns(2)
            with col_id1:
                evidencne_cislo = st.text_input("Evidenčné číslo:", placeholder="Napr. 1042")
            with col_id2:
                cislo_vybavenia = st.text_input("Číslo vybavenia:", placeholder="Napr. 17")

            col_z1, col_z2 = st.columns(2)
            with col_z1:
                firma_st = st.text_input("Firma:", placeholder="Napr. Žeriavy s.r.o.")
            with col_z2:
                voj = st.text_input("VOJ:", placeholder="Napr. 12345")

            st.markdown("---")
            st.subheader("2) Zadajte dátumy posledných vykonaných kontrol (periódy sa doplnia):")

            c1, c2 = st.columns(2)
            with c1:
                p_revizia = st.date_input("Posledná Revízia (opakuje sa ročne):", None)

                st.markdown("**Revízna skúška**")
                p_revizna_sk = st.date_input("Posledná Revízna skúška:", None, key="add_d_revsk")
                _ponuka_revsk = [0, 3, 2, 1]
                perioda_reviznej = st.selectbox(
                    "Perióda Revíznej skúšky:",
                    _ponuka_revsk,
                    index=_idx("nasledujuca_revizna_skuska", _ponuka_revsk, 2),
                    format_func=lambda x: "neopakuje sa" if x == 0 else f"{x} rok(y)",
                    key="add_p_revsk",
                )

                st.markdown("**Podrobná prehliadka OK**")
                p_podrobna_ok = st.date_input("Posledná Podrobná prehliadka OK (opakuje sa 5-ročne):", None)

            with c2:
                st.markdown("**Úradná skúška**")
                p_uradna = st.date_input("Posledná Úradná skúška:", None, key="add_d_urad")
                napoveda_vtz_utz = "Periódy sa doplnia podľa kategórie. UTZ: 9, 6, 5, 4, 3 r.; VTZ: 10 alebo 6 r."
                _ponuka_urad = [0, 10, 9, 6, 5, 4, 3]
                perioda_uradnej = st.selectbox(
                    "Perióda Úradnej skúšky:",
                    _ponuka_urad,
                    index=_idx("nasledujuca_uradna_skuska", _ponuka_urad, 5),
                    format_func=lambda x: "neopakuje sa" if x == 0 else f"{x} rokov",
                    key="add_p_urad", help=napoveda_vtz_utz,
                )

                st.markdown("**Odborná prehliadka**")
                p_odborna_pr = st.date_input("Posledná Odborná prehliadka:", None, key="add_d_odbpr")
                _ponuka_odbpr = [0, 3.0, 2.0, 1.0, 0.5, 0.25]
                interval_odborna_pr = st.selectbox(
                    "Interval Odbornej prehliadky:",
                    _ponuka_odbpr,
                    index=_idx("nasledujuca_odborna_prehliadka", _ponuka_odbpr, 1.0),
                    format_func=lambda x: "neopakuje sa" if x == 0 else ("3 roky" if x == 3.0 else ("2 roky" if x == 2.0 else ("1 rok (ročne)" if x == 1.0 else ("6 mesiacov (polročne)" if x == 0.5 else "3 mesiace (štvrťročne)")))),
                    key="add_p_odbpr",
                )

                st.markdown("**Odborná skúška**")
                p_odborna_sk = st.date_input("Posledná Odborná skúška:", None, key="add_d_odbsk")
                _ponuka_odbsk = [0, 6, 4, 3, 2, 1]
                perioda_odbornej_sk = st.selectbox(
                    "Perióda Odbornej skúšky:",
                    _ponuka_odbsk,
                    index=_idx("nasledujuca_odborna_skuska", _ponuka_odbsk, 1),
                    format_func=lambda x: "neopakuje sa" if x == 0 else f"{x} rok(ov)",
                    key="add_p_odbsk",
                )

            st.markdown("---")
            ma_geometriu = st.checkbox("Vykonáva sa na tomto stroji Geometrické zameranie žeriavovej dráhy? (10 rokov)")
            p_geometria = None
            if ma_geometriu:
                p_geometria = st.date_input("Posledné Geometrické zameranie dráhy:", None)

            st.markdown("---")
            st.markdown("**Poznámka k stroju**")
            poznamka = st.text_area(
                "Poznámka (napr. stroj v poruche, dôvod nevykonania kontroly):",
                placeholder="Napr. Stroj v poruche od 12.05.2026 - čaká sa na náhradný diel.",
            )
            datum_poznamky = st.date_input("Dátum poznámky:", None)

            tlacidlo_ulozit = st.form_submit_button("Uložiť stroj a vypočítať revízie")

        # --- SPRACOVANIE FORMULÁRA PO STLAČENÍ ULOŽIŤ ---
        if tlacidlo_ulozit and nazov:
            def _nasled(kontrola: str, posledny, perioda):
                """Dopočíta termín; ak sa kontrola podľa kategórie nevykonáva, vráti None."""
                if pravidla and kontrola in pravidla and pravidla[kontrola] is None:
                    return None
                return vypocitaj_nasledujuci(posledny, perioda)

            n_rev = _nasled("nasledujuca_revizia", p_revizia, 1)
            n_rev_sk = vypocitaj_nasledujuci(p_revizna_sk, perioda_reviznej)
            n_pod_ok = _nasled("nasledujuca_podrobna_prehliadka_ok", p_podrobna_ok, 5)
            n_urad = vypocitaj_nasledujuci(p_uradna, perioda_uradnej)
            n_odb_pr = vypocitaj_nasledujuci(p_odborna_pr, interval_odborna_pr)
            n_odb_sk = vypocitaj_nasledujuci(p_odborna_sk, perioda_odbornej_sk)
            n_geometria = vypocitaj_nasledujuci(p_geometria, 10) if ma_geometriu else None

            pripravene_novy_stroj = {
                "nazov": nazov.strip(),
                "umiestnenie": umiestnenie.strip() if umiestnenie else None,
                "evidencne_cislo": evidencne_cislo.strip() if evidencne_cislo else None,
                "cislo_vybavenia": cislo_vybavenia.strip() if cislo_vybavenia else None,
                "firma": firma_st.strip() if firma_st else None,
                "voj": voj.strip() if voj else None,
                "druh_systemu": druh_systemu if druh_systemu != "-" else None,
                "legislativna_skupina": legislativna_skupina.strip() if legislativna_skupina else None,
                "legislativny_druh": legislativny_druh.strip() if legislativny_druh else None,
                "posledna_revizia": p_revizia.isoformat() if p_revizia else None,
                "nasledujuca_revizia": n_rev.isoformat() if n_rev else None,
                "posledna_revizna_skuska": p_revizna_sk.isoformat() if p_revizna_sk else None,
                "perioda_reviznej_skusky": int(perioda_reviznej),
                "nasledujuca_revizna_skuska": n_rev_sk.isoformat() if n_rev_sk else None,
                "posledna_podrobna_prehliadka_ok": p_podrobna_ok.isoformat() if p_podrobna_ok else None,
                "nasledujuca_podrobna_prehliadka_ok": n_pod_ok.isoformat() if n_pod_ok else None,
                "posledna_uradna_skuska": p_uradna.isoformat() if p_uradna else None,
                "perioda_uradnej_skusky": int(perioda_uradnej),
                "nasledujuca_uradna_skuska": n_urad.isoformat() if n_urad else None,
                "posledna_odborna_prehliadka": p_odborna_pr.isoformat() if p_odborna_pr else None,
                "nasledujuca_odborna_prehliadka": n_odb_pr.isoformat() if n_odb_pr else None,
                "posledna_odborna_skuska": p_odborna_sk.isoformat() if p_odborna_sk else None,
                "nasledujuca_odborna_skuska": n_odb_sk.isoformat() if n_odb_sk else None,
                "vykonava_sa_geometria": ma_geometriu,
                "posledna_geometria": p_geometria.isoformat() if p_geometria else None,
                "nasledujuca_geometria": n_geometria.isoformat() if n_geometria else None,
                "poznamka": poznamka.strip() if poznamka else None,
                "datum_poznamky": datum_poznamky.isoformat() if datum_poznamky else None,
            }

            stroj_existuje = None
            for s in vsetky_stroje:
                if s["nazov"].strip().lower() == nazov.strip().lower():
                    stroj_existuje = s
                    break

            if stroj_existuje:
                # Nastavíme session state a reštartujeme stránku, čím skryjeme formulár
                st.session_state["stroj_na_prepis_id"] = stroj_existuje["id"]
                st.session_state["stroj_na_prepis_nazov"] = stroj_existuje["nazov"]
                st.session_state["stroj_na_prepis_data"] = pripravene_novy_stroj
                st.rerun()
            else:
                try:
                    db.insert_stroj(supabase, pripravene_novy_stroj)
                    st.success(f"✅ Nový stroj '{nazov}' bol úspešne zaevidovaný!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba pri ukladaní stroja: {e}")