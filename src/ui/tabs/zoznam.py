"""Záložka 4: Zoznam strojov, filtre, export/import Excelu, úprava a mazanie."""

from datetime import date, timedelta

import streamlit as st

from src.db import supabase_client as db
from src.services import excel
from src.services.revizie import vypocitaj_nasledujuci
from src.ui.components import formatuj_datum_s_farbou


def _zisti_predvoleny_datum(stroj: dict, posledny_kluc: str, nasledujuci_kluc: str, minus_roky=1):
    """Vráti predvolený dátum pre edit formulár.

    Poradie:
      1. Ak je v DB zapísaná posledná revízia -> použijeme ju.
      2. Ak posledná chýba -> dopočítame ju z nasledujúcej presne inverzným
         vzorcom (roky*365 - 1), aby uloženie bez zmien neposunulo termín.
      3. Ak nemáme nič -> dnešok.
    """
    posledny = stroj.get(posledny_kluc)
    nasledujuci = stroj.get(nasledujuci_kluc)

    try:
        roky_cislo = float(minus_roky) if minus_roky is not None else 1.0
    except ValueError:
        roky_cislo = 1.0

    if posledny:
        try:
            return date.fromisoformat(str(posledny).strip())
        except ValueError:
            pass

    if nasledujuci:
        try:
            nasl_dt = date.fromisoformat(str(nasledujuci).strip())
            # INVERZNÝ vzorec ku vypocitaj_nasledujuci -> žiadný drift pri uložení
            return nasl_dt - timedelta(days=int(roky_cislo * 365 - 1))
        except ValueError:
            pass

    return date.today()


def render(supabase, vsetky_stroje: list[dict]) -> None:
    st.header("📋 Kompletný zoznam, export a import strojov")

    # ==================== FILTRE ====================
    vsetky_firmy = sorted({s.get("firma") for s in vsetky_stroje if s.get("firma")})
    vsetky_druhy = sorted({s.get("druh_systemu") for s in vsetky_stroje if s.get("druh_systemu")})
    vsetky_voje = sorted({s.get("voj") for s in vsetky_stroje if s.get("voj")})

    st.markdown("#### 🎛️ Filtre")
    f_c1, f_c2, f_c3 = st.columns(3)
    with f_c1:
        zvolene_firmy = st.multiselect("Firma:", vsetky_firmy, key="fil_firma")
    with f_c2:
        zvolene_druhy = st.multiselect("Druh systému (VTZ/UTZ):", vsetky_druhy, key="fil_druh")
    with f_c3:
        zvolene_voje = st.multiselect("VOJ:", vsetky_voje, key="fil_voj")

    filter_zapnuty = bool(zvolene_firmy or zvolene_druhy or zvolene_voje)

    def prefiltruj(stroje):
        """Vráti len tie stroje, ktoré pasujú do zapnutých filtrov."""
        if not filter_zapnuty:
            return stroje
        out = []
        for s in stroje:
            if zvolene_firmy and s.get("firma") not in zvolene_firmy:
                continue
            if zvolene_druhy and s.get("druh_systemu") not in zvolene_druhy:
                continue
            if zvolene_voje and s.get("voj") not in zvolene_voje:
                continue
            out.append(s)
        return out

    filtrovane_stroje = prefiltruj(vsetky_stroje)

    # ==================== EXPORT / IMPORT ====================
    col_exp, col_imp = st.columns(2)

    with col_exp:
        st.subheader("📤 Export dát")
        if not filtrovane_stroje:
            if not vsetky_stroje:
                st.caption("Nie sú dáta na export.")
            else:
                st.caption("Filter nevráti žiadne stroje.")
        else:
            if filter_zapnuty:
                st.warning(
                    f"⚠️ **Filter je zapnutý** — exportuje sa len {len(filtrovane_stroje)} "
                    f"z {len(vsetky_stroje)} strojov."
                )
            excel_data = excel.export_stroje_excel(filtrovane_stroje)
            st.download_button(
                label="🟢 Stiahnuť Excel (.xlsx)",
                data=excel_data,
                file_name=f"revizie_strojov_{date.today().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with col_imp:
        st.subheader("📥 Import dát")
        nahraty_subor = st.file_uploader("Nahrajte vyplnený Excel súbor (.xlsx):", type=["xlsx"])

        if nahraty_subor is not None:
            if st.button("🚀 Spustiť import do databázy", use_container_width=True):
                try:
                    riadky = excel.parse_import_subor(nahraty_subor)

                    uspesne_importovane = 0
                    for riadok in riadky:
                        nazov_st = riadok["nazov"]
                        stroj_data = riadok["data"]
                        if not stroj_data:
                            continue

                        # Kontrola duplicity podľa názvu stroja
                        existuje_id = None
                        for s in vsetky_stroje:
                            if s["nazov"].strip().lower() == nazov_st.lower():
                                existuje_id = s["id"]
                                break

                        if existuje_id:
                            db.update_stroj(supabase, existuje_id, stroj_data)
                        else:
                            db.insert_stroj(supabase, stroj_data)
                        uspesne_importovane += 1

                    st.success(f"🎉 Import dokončený! Čísla ošetrené, dátumy zapísané. Riadkov: {uspesne_importovane}")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Chyba pri spracovaní Excel súboru: {ex}")

    # ==================== ZOZNAM STROJOV ====================
    if "aktualne_upravovany_id" not in st.session_state:
        st.session_state["aktualne_upravovany_id"] = None

    if not vsetky_stroje:
        st.info("V databáze nie sú žiadne stroje.")
    else:
        if filter_zapnuty:
            st.caption(f"Zobrazuje sa {len(filtrovane_stroje)} z {len(vsetky_stroje)} strojov.")
        dnesny_den = date.today()

        for stroj in filtrovane_stroje:
            stroj_id = stroj["id"]

            with st.container():
                col_nazov, col_miesto, col_revizie, col_akcia = st.columns([2, 1.2, 2, 0.8])

                with col_nazov:
                    st.markdown(f"### {stroj['nazov']}")
                    druh_systemu = stroj.get("druh_systemu")
                    skupina = stroj.get("legislativna_skupina") or "-"
                    druh = stroj.get("legislativny_druh") or "-"

                    if druh_systemu in ["VTZ", "UTZ"]:
                        farba_stitku = "#1F4E78" if druh_systemu == "VTZ" else "#2E7D32"
                        st.markdown(
                            f"<div style='background-color: {farba_stitku}; color: white; padding: 5px 12px; "
                            f"border-radius: 4px; display: inline-block; font-size: 0.95em; font-weight: bold; "
                            f"margin-bottom: 10px;'>{druh_systemu} • {skupina} • {druh}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<div style='color: #777; font-size: 0.9em; font-style: italic; "
                            "margin-bottom: 10px;'>⚠️ Bez legislatívneho zatriedenia</div>",
                            unsafe_allow_html=True,
                        )

                    evidencne = stroj.get("evidencne_cislo") or "Nezadané"
                    vybavenie = stroj.get("cislo_vybavenia") or "Nezadané"
                    st.markdown(
                        f"<div style='font-size: 1.1em; line-height: 1.6; color: #31333F;'>🆔 <b>Evid. č.:</b> "
                        f"{evidencne}<br>🛠️ <b>Č. vybavenia:</b> {vybavenie}</div>",
                        unsafe_allow_html=True,
                    )

                with col_miesto:
                    firma = stroj.get("firma") or "Nezadaná"
                    voj = stroj.get("voj") or "Nezadané"
                    umiestnenie_text = stroj.get("umiestnenie") or "Nezadané"
                    st.markdown(
                        f"<div style='font-size: 1.1em; line-height: 1.6; color: #31333F;'>📍 <b>Umiestnenie:</b> "
                        f"{umiestnenie_text}<br>🏢 <b>Firma:</b> {firma}<br>🏭 <b>VOJ:</b> {voj}</div>",
                        unsafe_allow_html=True,
                    )

                with col_revizie:
                    st.markdown("**📅 Nasledujúce termíny kontrol:**")
                    f_rev = formatuj_datum_s_farbou(stroj.get("nasledujuca_revizia"), dnesny_den)
                    f_rev_sk = formatuj_datum_s_farbou(stroj.get("nasledujuca_revizna_skuska"), dnesny_den)
                    f_pod_ok = formatuj_datum_s_farbou(stroj.get("nasledujuca_podrobna_prehliadka_ok"), dnesny_den)
                    f_odb_pr = formatuj_datum_s_farbou(stroj.get("nasledujuca_odborna_prehliadka"), dnesny_den)
                    f_odb_sk = formatuj_datum_s_farbou(stroj.get("nasledujuca_odborna_skuska"), dnesny_den)
                    f_urad = formatuj_datum_s_farbou(stroj.get("nasledujuca_uradna_skuska"), dnesny_den)

                    st.markdown(
                        f"- **Revízia:** {f_rev}\n"
                        f"- **Revízna skúška:** {f_rev_sk}\n"
                        f"- **Podrobná prehliadka OK:** {f_pod_ok}\n"
                        f"- **Odborná prehliadka:** {f_odb_pr}\n"
                        f"- **Odborná skúška:** {f_odb_sk}\n"
                        f"- **Úradná skúška:** {f_urad}",
                        unsafe_allow_html=True,
                    )
                    if stroj.get("vykonava_sa_geometria"):
                        f_geom = formatuj_datum_s_farbou(stroj.get("nasledujuca_geometria"), dnesny_den)
                        st.markdown(f"- **Geometria žeriavovej dráhy:** {f_geom}", unsafe_allow_html=True)

                with col_akcia:
                    kliknute_upravit = st.button("✏️ Upraviť", key=f"edit_btn_{stroj_id}")
                    kliknute_zmazat = st.button("❌ Zmazať", key=f"zmaz_{stroj_id}")

                    if kliknute_zmazat:
                        try:
                            db.delete_stroj(supabase, stroj_id)
                            st.toast("Stroj úspešne vymazaný! 🗑️")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Chyba pri mazaní: {e}")

                    if kliknute_upravit:
                        if st.session_state["aktualne_upravovany_id"] == stroj_id:
                            st.session_state["aktualne_upravovany_id"] = None
                        else:
                            st.session_state["aktualne_upravovany_id"] = stroj_id
                        st.rerun()

            # ---- REŽIM ÚPRAVY ----
            if st.session_state["aktualne_upravovany_id"] == stroj_id:
                st.info(f"🛠️ Režim úpravy pre stroj: **{stroj['nazov']}**")

                # Bezpečné načítanie periód s náhradnou hodnotou
                stroj_p_rev = stroj.get("perioda_reviznej_skusky")
                if stroj_p_rev is None:
                    stroj_p_rev = 2

                stroj_p_urad = stroj.get("perioda_uradnej_skusky")
                if stroj_p_urad is None:
                    stroj_p_urad = 5

                stroj_p_odbpr = stroj.get("interval_odborna_pr")
                if stroj_p_odbpr is None:
                    stroj_p_odbpr = 1.0

                stroj_p_odbsk = stroj.get("perioda_odbornej_skusky")
                if stroj_p_odbsk is None:
                    stroj_p_odbsk = 1

                # Predvolené dátumy pre formulár
                db_rev = _zisti_predvoleny_datum(stroj, "posledna_revizia", "nasledujuca_revizia", minus_roky=1)
                db_rev_sk = _zisti_predvoleny_datum(stroj, "posledna_revizna_skuska", "nasledujuca_revizna_skuska", minus_roky=stroj_p_rev)
                db_pod_ok = _zisti_predvoleny_datum(stroj, "posledna_podrobna_prehliadka_ok", "nasledujuca_podrobna_prehliadka_ok", minus_roky=5)
                db_urad = _zisti_predvoleny_datum(stroj, "posledna_uradna_skuska", "nasledujuca_uradna_skuska", minus_roky=stroj_p_urad)
                db_odb_pr = _zisti_predvoleny_datum(stroj, "posledna_odborna_prehliadka", "nasledujuca_odborna_prehliadka", minus_roky=stroj_p_odbpr)
                db_odb_sk = _zisti_predvoleny_datum(stroj, "posledna_odborna_skuska", "nasledujuca_odborna_skuska", minus_roky=stroj_p_odbsk)
                db_geom = _zisti_predvoleny_datum(stroj, "posledna_geometria", "nasledujuca_geometria", minus_roky=10)

                with st.form(key=f"form_edit_{stroj_id}", clear_on_submit=False):
                    e_col1, e_col2 = st.columns(2)

                    with e_col1:
                        new_nazov = st.text_input("Nový názov stroja:", value=stroj["nazov"], key=f"inp_nazov_{stroj_id}")
                        new_umiestnenie = st.text_input("Nové umiestnenie:", value=stroj["umiestnenie"] or "", key=f"inp_umiest_{stroj_id}")

                        st.markdown("---")
                        st.markdown("**1. Revízia (ročne)**")
                        new_rev = st.date_input("Dátum poslednej revízie:", db_rev, key=f"inp_rev_{stroj_id}")
                        clear_rev = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_rev_{stroj_id}")

                        st.markdown("---")
                        st.markdown("**2. Revízna skúška**")
                        new_rev_sk = st.date_input("Dátum poslednej rev. skúšky:", db_rev_sk, key=f"inp_revsk_{stroj_id}")
                        clear_rev_sk = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_revsk_{stroj_id}")

                        list_p_rev = [3, 2, 1]
                        p_rev_idx = list_p_rev.index(stroj_p_rev) if stroj_p_rev in list_p_rev else 1
                        new_p_rev = st.selectbox("Perióda Revíznej skúšky (roky):", list_p_rev, index=p_rev_idx, key=f"sel_rev_{stroj_id}")

                        st.markdown("---")
                        st.markdown("**3. Podrobná prehliadka OK (5-ročne)**")
                        new_pod_ok = st.date_input("Dátum poslednej podrobnej pr.:", db_pod_ok, key=f"inp_pod_{stroj_id}")
                        clear_pod_ok = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_pod_{stroj_id}")

                    with e_col2:
                        st.markdown("---")
                        st.markdown("**4. Úradná skúška**")
                        new_urad = st.date_input("Dátum poslednej úradnej sk.:", db_urad, key=f"inp_urad_{stroj_id}")
                        clear_urad = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_urad_{stroj_id}")

                        list_p_urad = [10, 9, 6, 5, 4, 3]
                        p_urad_idx = list_p_urad.index(stroj_p_urad) if stroj_p_urad in list_p_urad else 3
                        new_p_urad = st.selectbox("Perióda Úradnej skúšky (roky):", list_p_urad, index=p_urad_idx, key=f"sel_urad_{stroj_id}")

                        st.markdown("---")
                        st.markdown("**5. Odborná prehliadka**")
                        new_odb_pr = st.date_input("Dátum poslednej odbornej pr.:", db_odb_pr, key=f"inp_odbpr_{stroj_id}")
                        clear_odb_pr = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_odbpr_{stroj_id}")

                        list_p_odbpr = [3.0, 2.0, 1.0, 0.5, 0.25]
                        p_odbpr_idx = list_p_odbpr.index(stroj_p_odbpr) if stroj_p_odbpr in list_p_odbpr else 2
                        new_p_odbpr = st.selectbox(
                            "Interval Odbornej prehliadky:",
                            list_p_odbpr,
                            index=p_odbpr_idx,
                            format_func=lambda x: "3 roky" if x == 3.0 else ("2 roky" if x == 2.0 else ("1 rok (ročne)" if x == 1.0 else ("6 mesiacov (polročne)" if x == 0.5 else "3 mesiace (štvrťročne)"))),
                            key=f"sel_odbpr_{stroj_id}",
                        )

                        st.markdown("---")
                        st.markdown("**6. Odborná skúška**")
                        new_odb_sk = st.date_input("Dátum poslednej odbornej sk.:", db_odb_sk, key=f"inp_odbsk_{stroj_id}")
                        clear_odb_sk = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_odbsk_{stroj_id}")

                        list_p_odbsk = [6, 4, 3, 2, 1]
                        p_odbsk_idx = list_p_odbsk.index(stroj_p_odbsk) if stroj_p_odbsk in list_p_odbsk else 4
                        new_p_odbsk = st.selectbox("Perióda Odbornej skúšky (roky):", list_p_odbsk, index=p_odbsk_idx, key=f"sel_odbsk_{stroj_id}")

                    st.markdown("---")
                    new_ma_geom = st.checkbox("Vykonáva sa Geometrické zameranie?", value=stroj.get("vykonava_sa_geometria", False), key=f"chk_geom_{stroj_id}")
                    new_geom = st.date_input("Posledná Geometria dráhy:", db_geom, key=f"inp_geom_{stroj_id}") if new_ma_geom else None
                    clear_geom = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_geom_{stroj_id}") if new_ma_geom else False

                    # === FINÁLNE UKLADANIE ZMIEN ===
                    if st.form_submit_button("💾 Uložiť zmeny stroja"):
                        final_rev = None if clear_rev else new_rev
                        n_rev = vypocitaj_nasledujuci(final_rev, 1)

                        final_rev_sk = None if clear_rev_sk else new_rev_sk
                        n_rev_sk = vypocitaj_nasledujuci(final_rev_sk, int(new_p_rev))

                        final_pod_ok = None if clear_pod_ok else new_pod_ok
                        n_pod_ok = vypocitaj_nasledujuci(final_pod_ok, 5)

                        final_urad = None if clear_urad else new_urad
                        n_urad = vypocitaj_nasledujuci(final_urad, int(new_p_urad))

                        final_odb_pr = None if clear_odb_pr else new_odb_pr
                        n_odb_pr = vypocitaj_nasledujuci(final_odb_pr, new_p_odbpr)

                        final_odb_sk = None if clear_odb_sk else new_odb_sk
                        n_odb_sk = vypocitaj_nasledujuci(final_odb_sk, int(new_p_odbsk))

                        final_geom = None if (clear_geom or not new_ma_geom) else new_geom
                        n_geom = vypocitaj_nasledujuci(final_geom, 10) if new_ma_geom else None

                        upravene_data = {
                            "nazov": new_nazov.strip(),
                            "umiestnenie": new_umiestnenie.strip() if new_umiestnenie else None,
                            "posledna_revizia": final_rev.isoformat() if final_rev else None,
                            "nasledujuca_revizia": n_rev.isoformat() if n_rev else None,
                            "posledna_revizna_skuska": final_rev_sk.isoformat() if final_rev_sk else None,
                            "perioda_reviznej_skusky": int(new_p_rev),
                            "nasledujuca_revizna_skuska": n_rev_sk.isoformat() if n_rev_sk else None,
                            "posledna_podrobna_prehliadka_ok": final_pod_ok.isoformat() if final_pod_ok else None,
                            "nasledujuca_podrobna_prehliadka_ok": n_pod_ok.isoformat() if n_pod_ok else None,
                            "posledna_uradna_skuska": final_urad.isoformat() if final_urad else None,
                            "perioda_uradnej_skusky": int(new_p_urad),
                            "nasledujuca_uradna_skuska": n_urad.isoformat() if n_urad else None,
                            "posledna_odborna_prehliadka": final_odb_pr.isoformat() if final_odb_pr else None,
                            "nasledujuca_odborna_prehliadka": n_odb_pr.isoformat() if n_odb_pr else None,
                            "posledna_odborna_skuska": final_odb_sk.isoformat() if final_odb_sk else None,
                            "nasledujuca_odborna_skuska": n_odb_sk.isoformat() if n_odb_sk else None,
                            "vykonava_sa_geometria": new_ma_geom,
                            "posledna_geometria": final_geom.isoformat() if final_geom else None,
                            "nasledujuca_geometria": n_geom.isoformat() if n_geom else None,
                        }

                        try:
                            db.update_stroj(supabase, stroj_id, upravene_data)
                            st.toast(f"Stroj '{new_nazov}' úspešne upravený! 💾")
                            st.session_state["aktualne_upravovany_id"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Chyba pri ukladaní zmien do databázy: {e}")