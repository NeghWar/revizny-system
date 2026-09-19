"""Záložka 3: Evidencia nového stroja + ochrana proti duplicitám."""

import streamlit as st

from src.db import supabase_client as db
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
        # --- ŠTANDARDNÝ FORMULÁR PRE EVIDENCIU ---
        with st.form(key="novy_stroj_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nazov = st.text_input("Názov stroja / zariadenia:", placeholder="Napr. Mostový žeriav 5t")
            with col2:
                umiestnenie = st.text_input("Umiestnenie (Hala / Stanovište):", placeholder="Napr. Hala A - expedícia")

            st.markdown("---")
            st.subheader("Zadajte dátumy posledných vykonaných kontrol a ich periódy:")

            c1, c2 = st.columns(2)
            with c1:
                p_revizia = st.date_input("Posledná Revízia (opakuje sa ročne):", None)

                st.markdown("**Revízna skúška**")
                p_revizna_sk = st.date_input("Posledná Revízna skúška:", None, key="add_d_revsk")
                perioda_reviznej = st.selectbox("Perióda Revíznej skúšky:", [3, 2, 1], format_func=lambda x: f"{x} rok(y)", key="add_p_revsk")

                st.markdown("**Podrobná prehliadka OK**")
                p_podrobna_ok = st.date_input("Posledná Podrobná prehliadka OK (opakuje sa 5-ročne):", None)

            with c2:
                st.markdown("**Úradná skúška**")
                p_uradna = st.date_input("Posledná Úradná skúška:", None, key="add_d_urad")
                napoveda_vtz_utz = "💡 Pomôcka pre lehoty úradných skúšok:\n\n• UTZ: platia termíny 9, 6, 5, 4, 3 rokov podľa typu zariadenia.\n• VTZ: platia termíny 10 alebo 6 rokov."
                perioda_uradnej = st.selectbox("Perióda Úradnej skúšky:", [10, 9, 6, 5, 4, 3], format_func=lambda x: f"{x} rokov", key="add_p_urad", help=napoveda_vtz_utz)

                st.markdown("**Odborná prehliadka**")
                p_odborna_pr = st.date_input("Posledná Odborná prehliadka:", None, key="add_d_odbpr")
                interval_odborna_pr = st.selectbox(
                    "Interval Odbornej prehliadky:",
                    [3.0, 2.0, 1.0, 0.5, 0.25],
                    format_func=lambda x: "3 roky" if x == 3.0 else ("2 roky" if x == 2.0 else ("1 rok (ročne)" if x == 1.0 else ("6 mesiacov (polročne)" if x == 0.5 else "3 mesiace (štvrťročne)"))),
                    key="add_p_odbpr",
                )

                st.markdown("**Odborná skúška**")
                p_odborna_sk = st.date_input("Posledná Odborná skúška:", None, key="add_d_odbsk")
                perioda_odbornej_sk = st.selectbox("Perióda Odbornej skúšky:", [6, 4, 3, 2, 1], format_func=lambda x: f"{x} rok(ov)", key="add_p_odbsk")

            st.markdown("---")
            ma_geometriu = st.checkbox("Vykonáva sa na tomto stroji Geometrické zameranie žeriavovej dráhy? (10 rokov)")
            p_geometria = None
            if ma_geometriu:
                p_geometria = st.date_input("Posledné Geometrické zameranie dráhy:", None)

            tlacidlo_ulozit = st.form_submit_button("Uložiť stroj a vypočítať revízie")

        # --- SPRACOVANIE FORMULÁRA PO STLAČENÍ ULOŽIŤ ---
        if tlacidlo_ulozit and nazov:
            n_rev = vypocitaj_nasledujuci(p_revizia, 1)
            n_rev_sk = vypocitaj_nasledujuci(p_revizna_sk, perioda_reviznej)
            n_pod_ok = vypocitaj_nasledujuci(p_podrobna_ok, 5)
            n_urad = vypocitaj_nasledujuci(p_uradna, perioda_uradnej)
            n_odb_pr = vypocitaj_nasledujuci(p_odborna_pr, interval_odborna_pr)
            n_odb_sk = vypocitaj_nasledujuci(p_odborna_sk, perioda_odbornej_sk)
            n_geometria = vypocitaj_nasledujuci(p_geometria, 10) if ma_geometriu else None

            pripravene_novy_stroj = {
                "nazov": nazov.strip(),
                "umiestnenie": umiestnenie.strip() if umiestnenie else None,
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