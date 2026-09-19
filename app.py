import streamlit as st
from datetime import date, timedelta
import pandas as pd
import io

# Skontrolujeme, či je nainštalované openpyxl pre Excel export
try:
    from openpyxl.styles import Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    st.error("Chýba knižnica 'openpyxl'. Pridajte ji do requirements.txt")

from supabase import create_client, Client

# --- AUTOMATICKÉ NAČÍTANIE ZO SECRETS ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MOJE_TAJNE_HESLO = st.secrets["MOJE_TAJNE_HESLO"]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

st.set_page_config(page_title="Revízny Systém Strojov", page_icon="⚙️", layout="wide")

# ==========================================
# 🔒 BEZPEČNOSTNÝ ZÁMOK
# ==========================================
if "overeny" not in st.session_state:
    st.session_state.overeny = False

if not st.session_state.overeny:
    st.title("🔒 Chránený revízny systém")
    st.subheader("Vstup len pre oprávnené osoby")
    
    zadane_heslo = st.text_input("Zadajte prístupové heslo:", type="password")
    tlacidlo_prihlasit = st.button("Prihlásiť sa")
    
    if tlacidlo_prihlasit:
        if zadane_heslo == MOJE_TAJNE_HESLO:
            st.session_state.overeny = True
            st.rerun()
        else:
            st.error("Nesprávne heslo! Prístup odmietnutý.")
            
    st.stop()

# ==========================================
# HLAVNÝ PROGRAM (Spustí sa len po správnom hesle)
# ==========================================
st.title("⚙️ Profesionálny Systém Revízií a Prehliadok")

# --- POMOCNÁ FUNKCIA NA VÝPOČET TERMÍNU ---
def vypocitaj_nasledujuci(posledny_datum, roky):
    if posledny_datum is None:
        return None
    dni = int((roky * 365) - 1)
    return posledny_datum + timedelta(days=dni)

# Tlačidlo na odhlásenie v bočnom menu
if st.sidebar.button("🔒 Odhlásiť sa"):
    st.session_state.overeny = False
    st.rerun()

# --- ROZDELENIE STRÁNKY NA ŠTYRI ZÁLOŽKY ---
tab_prehlad, tab_kalendar, tab_pridat, tab_zoznam = st.tabs([
    "🔔 Prehľad a Upozornenia", 
    "📅 Mesačný Kalendár", 
    "➕ Pridať / Evidovať Stroj",
    "📋 Zoznam strojov a úprava"
])

# NAČÍTANIE VŠETKÝCH DÁT PRE POTREBY STRÁNKY
try:
    odpoved = supabase.table("stroje").select("*").order("nazov").execute()
    vsetky_stroje = odpoved.data
except Exception as e:
    st.error(f"Chyba pri načítaní dát: {e}")
    vsetky_stroje = []

definicia_kontrol = {
    "nasledujuca_revizia": "Revízia (ročne)",
    "nasledujuca_revizna_skuska": "Revízna skúška",
    "nasledujuca_podrobna_prehliadka_ok": "Podrobná prehliadka OK (5-ročne)",
    "nasledujuca_uradna_skuska": "Úradná skúška",
    "nasledujuca_odborna_prehliadka": "Odborná prehliadka",
    "nasledujuca_odborna_skuska": "Odborná skúška (ročne)",
    "nasledujuca_geometria": "Geometrické zameranie dráhy (10 rokov)"
}

# ==========================================
# ZÁLOŽKA 1: PREHĽAD A UPOZORNENIA
# ==========================================
with tab_prehlad:
    st.header("🔔 Inteligentný prehľad a semafor revízií")
    
    dnes = date.today()
    akt_mesiac = dnes.month
    akt_rok = dnes.year
    
    if akt_mesiac == 12:
        nasl_mesiac = 1
        nasl_rok = akt_rok + 1
    else:
        nasl_mesiac = akt_mesiac + 1
        nasl_rok = akt_rok

    # Načítanie existujúcich poznámok z databázy
    try:
        odpoved_poznamky = supabase.table("poznamky_restov").select("*").execute()
        vsetky_poznamky = odpoved_poznamky.data
    except Exception:
        vsetky_poznamky = []

    # Pomocná funkcia na rýchle vyhľadanie poznámky
    def najdi_poznamku(s_id, t_kontroly):
        for p in vsetky_poznamky:
            if p["stroj_id"] == s_id and p["typ_kontroly"] == t_kontroly:
                return p["text_poznamky"]
        return None

    # --- 📅 SEKCIA 2 & 3: DUÁLNY KALENDÁROVÝ SYSTÉM 📅 ---
    import calendar
    mesiace_nazvy = ["Január", "Február", "Marec", "Apríl", "Máj", "Jún", "Júl", "August", "September", "Október", "November", "December"]
    
    odpovedajuce_posledne = {
        "nasledujuca_revizia": "posledna_revizia", "nasledujuca_revizna_skuska": "posledna_revizna_skuska",
        "nasledujuca_podrobna_prehliadka_ok": "posledna_podrobna_prehliadka_ok", "nasledujuca_uradna_skuska": "posledna_uradna_skuska",
        "nasledujuca_odborna_prehliadka": "posledna_odborna_prehliadka", "nasledujuca_odborna_skuska": "posledna_odborna_skuska",
        "nasledujuca_geometria": "posledna_geometria"
    }

    # Inicializácia úložísk pre oba mesiace
    udalosti_aktualny = {}
    udalosti_buduci = {}
    
    for stroj in vsetky_stroje:
        for stlpec_nasl, nazov_kontroly in definicia_kontrol.items():
            stlpec_posl = odpovedajuce_posledne.get(stlpec_nasl)
            iso_nasl = stroj.get(stlpec_nasl)
            iso_posl = stroj.get(stlpec_posl) if stlpec_posl else None
            
            # --- SPRACOVANIE PRE AKTUÁLNY MESIAC ---
            if iso_posl:
                posl_dt = date.fromisoformat(iso_posl)
                if posl_dt.year == akt_rok and posl_dt.month == akt_mesiac:
                    den = posl_dt.day
                    if den not in udalosti_aktualny: udalosti_aktualny[den] = []
                    udalosti_aktualny[den].append({"stroj": stroj["nazov"], "miesto": stroj["umiestnenie"] or "Nezadané", "kontrola": nazov_kontroly, "status": "zelena"})
                    continue
            if iso_nasl:
                nasl_dt = date.fromisoformat(iso_nasl)
                if nasl_dt.year == akt_rok and nasl_dt.month == akt_mesiac:
                    den = nasl_dt.day
                    if den not in udalosti_aktualny: udalosti_aktualny[den] = []
                    status = "cervena" if nasl_dt < dnes else "oranzova"
                    udalosti_aktualny[den].append({"stroj": stroj["nazov"], "miesto": stroj["umiestnenie"] or "Nezadané", "kontrola": nazov_kontroly, "status": status})

            # --- SPRACOVANIE PRE BUDÚCI MESIAC ---
            if iso_posl:
                posl_dt = date.fromisoformat(iso_posl)
                if posl_dt.year == nasl_rok and posl_dt.month == nasl_mesiac:
                    den = posl_dt.day
                    if den not in udalosti_buduci: udalosti_buduci[den] = []
                    udalosti_buduci[den].append({"stroj": stroj["nazov"], "miesto": stroj["umiestnenie"] or "Nezadané", "kontrola": nazov_kontroly, "status": "zelena"})
                    continue
            if iso_nasl:
                nasl_dt = date.fromisoformat(iso_nasl)
                if nasl_dt.year == nasl_rok and nasl_dt.month == nasl_mesiac:
                    den = nasl_dt.day
                    if den not in udalosti_buduci: udalosti_buduci[den] = []
                    status = "cervena" if nasl_dt < dnes else "oranzova"
                    udalosti_buduci[den].append({"stroj": stroj["nazov"], "miesto": stroj["umiestnenie"] or "Nezadané", "kontrola": nazov_kontroly, "status": status})

    if "zvoleny_den_duany" not in st.session_state: st.session_state["zvoleny_den_duany"] = None
    if "zvoleny_typ_mesiaca" not in st.session_state: st.session_state["zvoleny_typ_mesiaca"] = None

    # === 🛠️ SPOLOČNÁ DEFINÍCIA PRE KALENDÁRE ===
    col_kal1, col_kal2 = st.columns(2)
    dni_v_tyzdni = ["Po", "Ut", "St", "Št", "Pi", "So", "Ne"]
    cal = calendar.Calendar(firstweekday=0)

    zvoleny_den = st.session_state.get("zvoleny_den_duany")
    zvoleny_typ = st.session_state.get("zvoleny_typ_mesiaca")

    # === 🗓️ 1. STĹPEC: AKTUÁLNY MESIAC ===
    with col_kal1:
        with st.container(border=True):
            st.markdown(f"<h4 style='text-align:center; color:#1F4E78; margin-top:0;'>📅 Aktuálny mesiac: {mesiace_nazvy[akt_mesiac - 1]} {akt_rok}</h4>", unsafe_allow_html=True)

            st_cols_dni1 = st.columns(7)
            for i, d_nazov in enumerate(dni_v_tyzdni):
                st_cols_dni1[i].markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:5px; color:#555;'>{d_nazov}</p>", unsafe_allow_html=True)
                
            tyzdne1 = cal.monthdayscalendar(akt_rok, akt_mesiac)
            for tyzden in tyzdne1:
                st_cols = st.columns(7)
                for i, den in enumerate(tyzden):
                    if den == 0:
                        st_cols[i].write("")
                    else:
                        label_text = f"{den}"
                        if den in udalosti_aktualny:
                            statusy = [u["status"] for u in udalosti_aktualny[den]]
                            if "cervena" in statusy: label_text = f"{den} 🚨"
                            elif "oranzova" in statusy: label_text = f"{den} ⏳"
                            elif "zelena" in statusy: label_text = f"{den} ✅"
                        
                        if st_cols[i].button(label_text, key=f"cal_akt_{den}", use_container_width=True):
                            st.session_state["zvoleny_den_duany"] = den
                            st.session_state["zvoleny_typ_mesiaca"] = "aktualny"
                            st.rerun()

            # --- VÝPIS DETAILU PRE AKTUÁLNY MESIAC ---
            if zvoleny_den and zvoleny_typ == "aktualny":
                st.markdown("---")
                st.markdown(f"##### 🔍 Podrobnosti pre: **{zvoleny_den}. {mesiace_nazvy[akt_mesiac - 1]}**")
                
                if zvoleny_den in udalosti_aktualny:
                    for u in udalosti_aktualny[zvoleny_den]:
                        if u["status"] == "zelena":
                            st.success(f"✅ **{u['stroj']}** — *{u['kontrola']}*")
                        elif u["status"] == "cervena":
                            st.error(f"🚨 **{u['stroj']}** — *{u['kontrola']}*")
                        else:
                            st.info(f"⏳ **{u['stroj']}** — *{u['kontrola']}*")
                else:
                    st.success("Žiadne plánované revízie. 👍")
                
                if st.button("✖️ Zatvoriť", key="close_detail_akt", use_container_width=True):
                    st.session_state["zvoleny_den_duany"] = None
                    st.session_state["zvoleny_typ_mesiaca"] = None
                    st.rerun()

    # === 🗓️ 2. STĹPEC: BUDÚCI MESIAC ===
    with col_kal2:
        with st.container(border=True):
            st.markdown(f"<h4 style='text-align:center; color:#2E7D32; margin-top:0;'>⏭️ Nasledujúci mesiac: {mesiace_nazvy[nasl_mesiac - 1]} {nasl_rok}</h4>", unsafe_allow_html=True)
            
            st_cols_dni2 = st.columns(7)
            for i, d_nazov in enumerate(dni_v_tyzdni):
                st_cols_dni2[i].markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:5px; color:#555;'>{d_nazov}</p>", unsafe_allow_html=True)
                
            tyzdne2 = cal.monthdayscalendar(nasl_rok, nasl_mesiac)
            for tyzden in tyzdne2:
                st_cols = st.columns(7)
                for i, den in enumerate(tyzden):
                    if den == 0:
                        st_cols[i].write("")
                    else:
                        label_text = f"{den}"
                        if den in udalosti_buduci:
                            statusy = [u["status"] for u in udalosti_buduci[den]]
                            if "cervena" in statusy: label_text = f"{den} 🚨"
                            elif "oranzova" in statusy: label_text = f"{den} ⏳"
                            elif "zelena" in statusy: label_text = f"{den} ✅"
                        
                        if st_cols[i].button(label_text, key=f"cal_nasl_{den}", use_container_width=True):
                            st.session_state["zvoleny_den_duany"] = den
                            st.session_state["zvoleny_typ_mesiaca"] = "buduci"
                            st.rerun()

            # --- VÝPIS DETAILU PRE BUDÚCI MESIAC ---
            if zvoleny_den and zvoleny_typ == "buduci":
                st.markdown("---")
                st.markdown(f"##### 🔍 Podrobnosti pre: **{zvoleny_den}. {mesiace_nazvy[nasl_mesiac - 1]}**")
                
                if zvoleny_den in udalosti_buduci:
                    for u in udalosti_buduci[zvoleny_den]:
                        if u["status"] == "zelena":
                            st.success(f"✅ **{u['stroj']}** — *{u['kontrola']}*")
                        elif u["status"] == "cervena":
                            st.error(f"🚨 **{u['stroj']}** — *{u['kontrola']}*")
                        else:
                            st.info(f"⏳ **{u['stroj']}** — *{u['kontrola']}*")
                else:
                    st.success("Žiadne plánované revízie. 👍")
                
                if st.button("✖️ Zatvoriť", key="close_detail_nasl", use_container_width=True):
                    st.session_state["zvoleny_den_duany"] = None
                    st.session_state["zvoleny_typ_mesiaca"] = None
                    st.rerun()
   

    # --- 🚨 SEKCIA: KRITICKÉ UPOZORNENIA Z MINULOSTI (PRESUNUTÉ NA SPODOK) 🚨 ---
    st.markdown("<br><br>", unsafe_allow_html=True)  # Decentná medzera na oddelenie
    st.subheader("🚨 Kritické nedoplatky (Zameškané z minulých mesiacov)")
    nasli_sa_stare_resty = False
    
    for stroj in vsetky_stroje:
        for stlpec, nazov_kontroly in definicia_kontrol.items():
            if stroj.get(stlpec):
                termin = date.fromisoformat(stroj[stlpec])
                
                # Sledujeme len tie termíny, ktoré sú staršie ako začiatok aktuálneho mesiaca
                if termin < date(akt_rok, akt_mesiac, 1):
                    nasli_sa_stare_resty = True
                    dni_po = (dnes - termin).days
                    stroj_id = stroj["id"]
                    
                    st.error(f"❌ **{stroj['nazov']}** ({stroj['umiestnenie']}) -> **{nazov_kontroly}** mala byť hotová do **{termin.strftime('%d.%m.%Y')}** (Mešká už {dni_po} dní!)")
                    
                    existujuca_poznamka = najdi_poznamku(stroj_id, stlpec)
                    if existujuca_poznamka:
                        st.info(f"ℹ️ **Dôvod zameškania:** {existujuca_poznamka}")
                    
                    with st.expander(f"📝 Upraviť poznámku k zdôvodneniu meškania"):
                        with st.form(key=f"form_poznamka_{stroj_id}_{stlpec}"):
                            nova_poznamka = st.text_area(
                                "Dôvod (napr. Stroj v poruche, čaká sa na diel / dohodnutý termín):", 
                                value=existujuca_poznamka if existujuca_poznamka else "",
                                key=f"txt_{stroj_id}_{stlpec}"
                            )
                            tlacidlo_ulozit_p = st.form_submit_button("💾 Uložiť dôvod")
                            
                            if tlacidlo_ulozit_p:
                                try:
                                    upsert_data = {
                                        "stroj_id": stroj_id,
                                        "typ_kontroly": stlpec,
                                        "text_poznamky": nova_poznamka
                                    }
                                    if existujuca_poznamka:
                                        supabase.table("poznamky_restov").update({"text_poznamky": nova_poznamka}).eq("stroj_id", stroj_id).eq("typ_kontroly", stlpec).execute()
                                    else:
                                        supabase.table("poznamky_restov").insert(upsert_data).execute()
                                    st.toast("Poznámka bola úspešne uložená! 📝")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"Chyba pri ukladaní: {err}")
                    st.write("")
                    
    if not nasli_sa_stare_resty:
        st.success("Skvelé! Nemáte žiadne staré zameškané revízie z minulých mesiacov. 🎉")
 

# ==========================================
# ZÁLOŽKA 2: MESAČNÝ KALENDÁR
# ==========================================
with tab_kalendar:
    st.header("📅 Inteligentný archív a plánovač podľa mesiacov")
    st.caption("Vyberte si ľubovoľný mesiac a rok pre zobrazenie stavu revízií.")
    
    dnesny_dt = date.today()
    
    # Príprava selectboxov
    c_rok, c_mes = st.columns(2)
    with c_rok:
        # Vygenerujeme zoznam rokov od 2019 po 2099
        roky_na_vyber = list(range(2019, 2100))
        # Automaticky nastavíme ako predvolený aktuálny rok v systéme
        predvoleny_rok_idx = roky_na_vyber.index(dnesny_dt.year) if dnesny_dt.year in roky_na_vyber else 0
        izvoleny_rok = st.selectbox("Vyberte rok:", roky_na_vyber, index=predvoleny_rok_idx, key="arch_rok")
        
    with c_mes:
        mesiace_sk = ["Január", "Február", "Marec", "Apríl", "Máj", "Jún", "Júl", "August", "September", "Október", "November", "December"]
        izvoleny_mesiac_nazov = st.selectbox("Vyberte mesiac:", mesiace_sk, index=dnesny_dt.month - 1, key="arch_mes")
        izvoleny_mesiac_num = mesiace_sk.index(izvoleny_mesiac_nazov) + 1

    st.subheader(f"📊 Stav revízií pre obdobie: {izvoleny_mesiac_nazov} {izvoleny_rok}")
    nasli_sa_záznamy = False
    
    # Príprava prepojenia kvôli overovaniu zelenej farby
    odpovedajuce_posledne_z2 = {
        "nasledujuca_revizia": "posledna_revizia", "nasledujuca_revizna_skuska": "posledna_revizna_skuska",
        "nasledujuca_podrobna_prehliadka_ok": "posledna_podrobna_prehliadka_ok", "nasledujuca_uradna_skuska": "posledna_uradna_skuska",
        "nasledujuca_odborna_prehliadka": "posledna_odborna_prehliadka", "nasledujuca_odborna_skuska": "posledna_odborna_skuska",
        "nasledujuca_geometria": "posledna_geometria"
    }
    for stroj in vsetky_stroje:
        for stlpec_nasl, nazov_kontroly in definicia_kontrol.items():
            stlpec_posl = odpovedajuce_posledne_z2.get(stlpec_nasl)
            
            iso_nasl = stroj.get(stlpec_nasl)
            iso_posl = stroj.get(stlpec_posl) if stlpec_posl else None
            
            # 1. PRÍPAD: VYKONANÁ REVIZIA (ZELENÁ ✅)
            # Zobrazí sa v mesiaci, kedy bola reálne vykonaná
            if iso_posl:
                posl_dt = date.fromisoformat(iso_posl)
                if posl_dt.year == izvoleny_rok and posl_dt.month == izvoleny_mesiac_num:
                    nasli_sa_záznamy = True
                    pekny_d = posl_dt.strftime('%d.%m.%Y')
                    st.success(f"✅ **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) -> **{nazov_kontroly}** [VYKONANÉ]")
                    continue # Ak bola spravená, nebudeme ju pre tento mesiac vypisovať duplicitne ako plánovanú

            # 2. PRÍPAD: PLÁNOVANÁ REVIZIA (ČERVENÁ 🚨 alebo MODRÁ 🔵)
            if iso_nasl:
                nasl_dt = date.fromisoformat(iso_nasl)
                if nasl_dt.year == izvoleny_rok and nasl_dt.month == izvoleny_mesiac_num:
                    nasli_sa_záznamy = True
                    pekny_d = nasl_dt.strftime('%d.%m.%Y')
                    
                    # Logika pre priradenie správnej farby podľa času
                    # Ak je zvolený termín už v minulosti oproti dnešku a nebol zapísaný ako hotový -> ČERVENÁ
                    if nasl_dt < dnesny_dt:
                        st.error(f"🚨 **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) -> **{nazov_kontroly}** [TERMÍN UPLYNUL / NESPLNENÉ]")
                    # Ak je termín dnes alebo v budúcnosti -> MODRÁ (Streamlit .info)
                    else:
                        st.info(f"🔵 **{pekny_d}** — **{stroj['nazov']}** ({stroj['umiestnenie'] or 'Nezadané'}) -> **{nazov_kontroly}** [PLÁNOVANÉ / ČAKÁ NA VYKONANIE]")

    if not nasli_sa_záznamy:
        st.caption("Pre toto obdobie nie sú zaznamenané žiadne splnené ani plánované revízie.")


# ==========================================
# ZÁLOŽKA 3: PRIDANIE / EVIDENCIA STROJA
# ==========================================
with tab_pridat:
    st.header("Evidencia nového stroja do systému")

    # Inicializácia stavov pre kontrolu prepisu
    if "stroj_na_prepis_id" not in st.session_state:
        st.session_state["stroj_na_prepis_id"] = None
    if "stroj_na_prepis_data" not in st.session_state:
        st.session_state["stroj_na_prepis_data"] = None
    if "stroj_na_prepis_nazov" not in st.session_state:
        st.session_state["stroj_na_prepis_nazov"] = None

    # --- 🛡️ BLOK PRE POTVRDENIE (Ak sa zistila duplicita, zobrazí sa IBA toto) ---
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
                    supabase.table("stroje").update(dup_data).eq("id", dup_id).execute()
                    st.toast(f"Stroj '{dup_nazov}' bol úspešne prepísaný! 💾")
                    
                    # KOMPLETNÝ RESET A NÁVRAT K FORMULÁRU
                    st.session_state["stroj_na_prepis_id"] = None
                    st.session_state["stroj_na_prepis_data"] = None
                    st.session_state["stroj_na_prepis_nazov"] = None
                    st.rerun()
                except Exception as err:
                    st.error(f"Nepodarilo sa prepísať stroj: {err}")
                    
        with c_dup2:
            if st.button("❌ Nie, ponechať pôvodný", key=f"btn_overwrite_cancel_{dup_id}", use_container_width=True):
                # RESET BEZ ZÁPISU
                st.session_state["stroj_na_prepis_id"] = None
                st.session_state["stroj_na_prepis_data"] = None
                st.session_state["stroj_na_prepis_nazov"] = None
                st.info("Pôvodný stroj zostal v databáze nezmenený.")
                st.rerun()

    else:
        # --- 📋 ŠTANDARDNÝ FORMULÁR PRE EVIDENCIU (Zobrazí sa len, ak neriešime duplicitu) ---
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
                    key="add_p_odbpr"
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
                # Nastavíme session state a okamžite reštartujeme stránku, čím skryjeme formulár
                st.session_state["stroj_na_prepis_id"] = stroj_existuje["id"]
                st.session_state["stroj_na_prepis_nazov"] = stroj_existuje["nazov"]
                st.session_state["stroj_na_prepis_data"] = pripravene_novy_stroj
                st.rerun()
            else:
                try:
                    supabase.table("stroje").insert(pripravene_novy_stroj).execute()
                    st.success(f"✅ Nový stroj '{nazov}' bol úspešne zaevidovaný!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba pri ukladaní stroja: {e}")

# ==========================================
# ZÁLOŽKA 4: ZOZNAM STROJOV, ÚPRAVA A MAZANIE
# ==========================================
with tab_zoznam:
    st.header("📋 Kompletný zoznam, export a import strojov")

    # Príprava dvoch stĺpcov pre Export a Import vedľa seba
    col_exp, col_imp = st.columns(2)

    # === 🟢 SEKCIA 1: AKTUALIZOVANÝ EXPORT DO EXCELU (OPRAVENÝ) 🟢 ===
    with col_exp:
        st.subheader("📤 Export dát")
        if vsetky_stroje:
            df = pd.DataFrame(vsetky_stroje)
            
            # Kompletné mapovanie všetkých stĺpcov, ktoré CHCEME mať v Exceli
            stlpce_pre_excel = {
                "nazov": "Názov stroja", 
                "druh_systemu": "Druh systému (VTZ/UTZ)",
                "legislativna_skupina": "Legislatívna skupina",
                "legislativny_druh": "Legislatívny druh",
                "evidencne_cislo": "Evidenčné číslo",
                "cislo_vybavenia": "Číslo vybavenia",
                "umiestnenie": "Umiestnenie",
                "firma": "Firma",
                "voj": "VOJ",
                "nasledujuca_revizia": "Ďalšia Revízia", 
                "nasledujuca_revizna_skuska": "Ďalšia Revízna skúška",
                "nasledujuca_podrobna_prehliadka_ok": "Ďalšia Podrobná prehliadka OK",
                "nasledujuca_odborna_prehliadka": "Ďalšia Odborná prehliadka", 
                "nasledujuca_odborna_skuska": "Ďalšia Odborná skúška",
                "nasledujuca_uradna_skuska": "Ďalšia Úradná skúška", 
                "nasledujuca_geometria": "Ďalšia Geometria dráhy"
            }
            
            # POISTKA: Ak stĺpec v DataFrame chýba (lebo nie je v DB), vytvoríme ho ako prázdny
            for db_col in stlpce_pre_excel.keys():
                if db_col not in df.columns:
                    df[db_col] = None
            
            # Teraz môžeme bezpečne vybrať a premenovať všetky stĺpce v presnom poradí
            df_export = df[list(stlpce_pre_excel.keys())].rename(columns=stlpce_pre_excel)
            
            stlpce_s_datumami = [
                "Ďalšia Revízia", "Ďalšia Revízna skúška", "Ďalšia Podrobná prehliadka OK", 
                "Ďalšia Odborná prehliadka", "Ďalšia Odborná skúška", "Ďalšia Úradná skúška", 
                "Ďalšia Geometria dráhy"
            ]
            
            for col in df_export.columns:
                if col in stlpce_s_datumami:
                    df_export[col] = pd.to_datetime(df_export[col], errors='coerce').dt.strftime('%d.%m.%Y')
            
            # Vyplníme prázdne textové hodnoty zrozumiteľným textom
            df_export = df_export.fillna("Nezadané")

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Revízie Strojov')
                workbook = writer.book
                worksheet = writer.sheets['Revízie Strojov']
                hlavicka_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
                hlavicka_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
                tenka_ciara = Side(border_style="thin", color="D9D9D9")
                mriezka = Border(left=tenka_ciara, right=tenka_ciara, top=tenka_ciara, bottom=tenka_ciara)
                
                for row in worksheet.iter_rows(min_row=1, max_row=1, min_col=1, max_col=worksheet.max_column):
                    for cell in row:
                        cell.font = hlavicka_font
                        cell.fill = hlavicka_fill
                        cell.border = mriezka
                worksheet.freeze_panes = 'A2'

                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = get_column_letter(col[0].column) # Použitá oprava pre index prvej bunky
                    worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                    for cell in col:
                        if cell.row > 1:
                            cell.border = mriezka
            
            st.download_button(
                label="🟢 Stiahnuť Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"revizie_strojov_{date.today().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.caption("Nie sú dáta na export.")
    
    # === 🔵 SEKCIA 2: OPRAVENÝ IMPORT (1. ČASŤ: OŠETRENIE .0 A DÁTUMOV) 🔵 ===
    with col_imp:
        st.subheader("📥 Import dát")
        nahraty_subor = st.file_uploader("Nahrajte vyplnený Excel súbor (.xlsx):", type=["xlsx"])
        
        if nahraty_subor is not None:
            if st.button("🚀 Spustiť import do databázy", use_container_width=True):
                try:
                    # Načítame excel, pričom vynútime, aby textové stĺpce neboli skomolené na float
                    df_import = pd.read_excel(nahraty_subor)
                    
                    # Mapa z Excel názvov (z exportu) na presné stĺpce v databáze Supabase
                    mapovanie_na_db = {
                        "Názov stroja": "nazov",
                        "Druh systému (VTZ/UTZ)": "druh_systemu",
                        "Legislatívna skupina": "legislativna_skupina",
                        "Legislatívny druh": "legislativny_druh",
                        "Evidenčné číslo": "evidencne_cislo",
                        "Číslo vybavenia": "cislo_vybavenia",
                        "Umiestnenie": "umiestnenie",
                        "Firma": "firma",
                        "VOJ": "voj",
                        # Prepájame exportované termíny na databázové stĺpce nasledujúcich kontrol
                        "Ďalšia Revízia": "nasledujuca_revizia",
                        "Ďalšia Revízna skúška": "nasledujuca_revizna_skuska",
                        "Ďalšia Podrobná prehliadka OK": "nasledujuca_podrobna_prehliadka_ok",
                        "Ďalšia Odborná prehliadka": "nasledujuca_odborna_prehliadka",
                        "Ďalšia Odborná skúška": "nasledujuca_odborna_skuska",
                        "Ďalšia Úradná skúška": "nasledujuca_uradna_skuska",
                        "Ďalšia Geometria dráhy": "nasledujuca_geometria"
                    }

                    def ocisti_float_cislo(hodnota):
                        """Odstráni otravné .0 z konca čísel vybavenia a evidencie"""
                        if pd.isna(hodnota):
                            return None
                        hodnota_str = str(hodnota).strip()
                        if hodnota_str.endswith('.0'):
                            return hodnota_str[:-2]
                        return hodnota_str

                    def konvertuj_na_iso_datum(hodnota):
                        """Prevedie slovenský dátum z Excelu na formát YYYY-MM-DD pre Supabase"""
                        if pd.isna(hodnota):
                            return None
                        h_str = str(hodnota).strip()
                        if h_str in ["nevykonáva sa", "Nezadané", "Nezadaná", ""]:
                            return None
                        try:
                            # Pandas inteligentne rozpozná formáty (napr. 17.09.2026 alebo 2026-09-17)
                            parsed_dt = pd.to_datetime(hodnota, dayfirst=True, errors='raise')
                            return parsed_dt.strftime('%Y-%m-%d')
                        except Exception:
                            return None

                    # Zistenie existujúcich stĺpcov v DB
                    if vsetky_stroje and len(vsetky_stroje) > 0:
                        existujuce_db_stlpce = set(vsetky_stroje[0].keys())
                    else:
                        existujuce_db_stlpce = {"id", "nazov", "umiestnenie"}
                    
                    uspesne_importovane = 0

                    # === 🔵 SEKCIA 2: OPRAVENÝ IMPORT (2. ČASŤ: CYKLUS A ZÁPIS DO DB) ===
                    for _, row in df_import.iterrows():
                        nazov_st = row.get("Názov stroja")
                        if pd.isna(nazov_st) or str(nazov_st).strip() == "":
                            continue
                            
                        stroj_data = {}
                        for excel_col, db_col in mapovanie_na_db.items():
                            if excel_col in df_import.columns:
                                val = row[excel_col]
                                
                                # 1. Ak ide o dátumový stĺpec, konvertujeme na ISO formát
                                if db_col.startswith("nasledujuca_"):
                                    stroj_data[db_col] = konvertuj_na_iso_datum(val)
                                
                                # 2. Ak ide o čísla (vybavenie, evidencia), očistíme ich od .0
                                elif db_col in ["cislo_vybavenia", "evidencne_cislo"]:
                                    stroj_data[db_col] = ocisti_float_cislo(val)
                                
                                # 3. Ostatné textové stĺpce
                                else:
                                    stroj_data[db_col] = None if pd.isna(val) or str(val).strip() in ["nevykonáva sa", "Nezadané", "Nezadaná"] else str(val).strip()

                        # Zapnutie prepínača pre geometriu podľa dátumu
                        if "nasledujuca_geometria" in stroj_data and stroj_data["nasledujuca_geometria"] is not None:
                            stroj_data["vykonava_sa_geometria"] = True

                        # Kontrola duplicity podľa názvu stroja
                        existuje_id = None
                        for s in vsetky_stroje:
                            if s["nazov"].strip().lower() == str(nazov_st).strip().lower():
                                existuje_id = s["id"]
                                break
                        
                        # Zápis do databázy (Update / Insert)
                        if existuje_id:
                            supabase.table("stroje").update(stroj_data).eq("id", existuje_id).execute()
                        else:
                            supabase.table("stroje").insert(stroj_data).execute()
                            
                        uspesne_importovane += 1
                    
                    st.success(f"🎉 Import dokončený! Čísla ošetrené, dátumy zapísané. Riadkov: {uspesne_importovane}")
                    st.rerun()
                    
                except Exception as ex:
                    st.error(f"Chyba pri spracovaní Excel súboru: {ex}")

                    
                    for _, row in df_import.iterrows():
                        nazov_st = row.get("Názov stroja")
                        if pd.isna(nazov_st) or str(nazov_st).strip() == "":
                            continue
                            
                        stroj_data = {}
                        for excel_col, db_col in mapovanie_na_db.items():
                            if excel_col in df_import.columns:
                                # Posielame do DB iba to, čo v nej reálne existuje
                                if db_col in existujuce_db_stlpce:
                                    val = row[excel_col]
                                    stroj_data[db_col] = None if pd.isna(val) or str(val).strip() in ["nevykonáva sa", "Nezadané", "Nezadaná"] else str(val).strip()
                        
                        # Kontrola duplicity podľa názvu
                        existuje_id = None
                        for s in vsetky_stroje:
                            if s["nazov"].strip().lower() == str(nazov_st).strip().lower():
                                existuje_id = s["id"]
                                break
                        
                        if existuje_id:
                            # Aktualizácia základných stĺpcov, ktoré sú v DB
                            if stroj_data:
                                supabase.table("stroje").update(stroj_data).eq("id", existuje_id).execute()
                        else:
                            # Zápis nového stroja
                            if stroj_data:
                                supabase.table("stroje").insert(stroj_data).execute()
                            
                        uspesne_importovane += 1
                    
                    st.success(f"🎉 Import prebehol úspešne! Spracovaných riadkov: {uspesne_importovane}")
                    st.rerun()
                    
                except Exception as ex:
                    st.error(f"Chyba pri spracovaní Excel súboru: {ex}")
   
    # === 📋 ZOBRAZENIE STROJOV V APLIKÁCII (1. ČASŤ Z 2) 📋 ===
    if "aktualne_upravovany_id" not in st.session_state:
        st.session_state["aktualne_upravovany_id"] = None

    # === 📋 ZOBRAZENIE STROJOV V APLIKÁCII (1. POLOVICA) 📋 ===
    if "aktualne_upravovany_id" not in st.session_state:
        st.session_state["aktualne_upravovany_id"] = None

    if not vsetky_stroje:
        st.info("V databáze nie sú žiadne stroje.")
    else:
        dnesny_den = date.today()
        
        for stroj in vsetky_stroje:
            stroj_id = stroj['id']

            with st.container():
                col_nazov, col_miesto, col_revizie, col_akcia = st.columns([2, 1.2, 2, 0.8])
                
                with col_nazov:
                    st.markdown(f"### {stroj['nazov']}")
                    druh_systemu = stroj.get('druh_systemu')
                    skupina = stroj.get('legislativna_skupina') or "-"
                    druh = stroj.get('legislativny_druh') or "-"
                    
                    if druh_systemu in ["VTZ", "UTZ"]:
                        farba_stitku = "#1F4E78" if druh_systemu == "VTZ" else "#2E7D32"
                        st.markdown(f"<div style='background-color: {farba_stitku}; color: white; padding: 5px 12px; border-radius: 4px; display: inline-block; font-size: 0.95em; font-weight: bold; margin-bottom: 10px;'>{druh_systemu} • {skupina} • {druh}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color: #777; font-size: 0.9em; font-style: italic; margin-bottom: 10px;'>⚠️ Bez legislatívneho zatriedenia</div>", unsafe_allow_html=True)
                    
                    evidencne = stroj.get('evidencne_cislo') or "Nezadané"
                    vybavenie = stroj.get('cislo_vybavenia') or "Nezadané"
                    st.markdown(f"<div style='font-size: 1.1em; line-height: 1.6; color: #31333F;'>🆔 <b>Evid. č.:</b> {evidencne}<br>🛠️ <b>Č. vybavenia:</b> {vybavenie}</div>", unsafe_allow_html=True)

                with col_miesto:
                    firma = stroj.get('firma') or "Nezadaná"
                    voj = stroj.get('voj') or "Nezadané"
                    umiestnenie_text = stroj.get('umiestnenie') or "Nezadané"
                    st.markdown(f"<div style='font-size: 1.1em; line-height: 1.6; color: #31333F;'>📍 <b>Umiestnenie:</b> {umiestnenie_text}<br>🏢 <b>Firma:</b> {firma}<br>🏭 <b>VOJ:</b> {voj}</div>", unsafe_allow_html=True)
               
                with col_revizie:
                    st.markdown("**📅 Nasledujúce termíny kontrol:**")
                    def formatuj_s_farbou(iso_datum):
                        if iso_datum:
                            try:
                                termin_date = date.fromisoformat(str(iso_datum).strip())
                                r, m, d = iso_datum.split('-')
                                pekny_format = f"{d}.{m}.{r}"
                                if termin_date < dnesny_den:
                                    return f"<span style='color:#ff4b4b; font-weight:bold;'>{pekny_format} (PO TERMÍNE! 🚨)</span>"
                                else:
                                    return f"<span style='color:#09ab3b; font-weight:bold;'>{pekny_format} (Platná ✅)</span>"
                            except Exception:
                                return "<span style='color:#777777;'>*nevykonáva sa*</span>"
                        return "<span style='color:#777777;'>*nevykonáva sa*</span>"

                    f_rev = formatuj_s_farbou(stroj.get('nasledujuca_revizia'))
                    f_rev_sk = formatuj_s_farbou(stroj.get('nasledujuca_revizna_skuska'))
                    f_pod_ok = formatuj_s_farbou(stroj.get('nasledujuca_podrobna_prehliadka_ok'))
                    f_odb_pr = formatuj_s_farbou(stroj.get('nasledujuca_odborna_prehliadka'))
                    f_odb_sk = formatuj_s_farbou(stroj.get('nasledujuca_odborna_skuska'))
                    f_urad = formatuj_s_farbou(stroj.get('nasledujuca_uradna_skuska'))
                    
                    st.markdown(f"- **Revízia:** {f_rev}\n- **Revízna skúška:** {f_rev_sk}\n- **Podrobná prehliadka OK:** {f_pod_ok}\n- **Odborná prehliadka:** {f_odb_pr}\n- **Odborná skúška:** {f_odb_sk}\n- **Úradná skúška:** {f_urad}", unsafe_allow_html=True)
                    if stroj.get('vykonava_sa_geometria'):
                        f_geom = formatuj_s_farbou(stroj.get('nasledujuca_geometria'))
                        st.markdown(f"- **Geometria žeriavovej dráhy:** {f_geom}", unsafe_allow_html=True)
                
                with col_akcia:
                    kliknute_upravit = st.button("✏️ Upraviť", key=f"edit_btn_{stroj_id}")
                    kliknute_zmazat = st.button("❌ Zmazať", key=f"zmaz_{stroj_id}")
                    
                    if kliknute_zmazat:
                        try:
                            supabase.table("stroje").delete().eq("id", stroj_id).execute()
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
   
            # === 🛠️ REŽIM ÚPRAVY PRE STROJ (OPRAVENÉ S POISTKOU PROTI NONE) 🛠️ ===
            if st.session_state["aktualne_upravovany_id"] == stroj_id:
                st.info(f"🛠️ Režim úpravy pre stroj: **{stroj['nazov']}**")
                
                # Ošetrená funkcia, ktorá nespadne pri None hodnotách periód
                def zisti_predvoleny_datum(posledny_kluc, nasledujuci_kluc, minus_roky=1):
                    posledny = stroj.get(posledny_kluc)
                    nasledujuci = stroj.get(nasledujuci_kluc)
                    
                    # Poistka: Ak je lehota None alebo text, premeníme ju bezpečne na číslo (float/int)
                    try:
                        roky_cislo = float(minus_roky) if minus_roky is not None else 1.0
                    except ValueError:
                        roky_cislo = 1.0

                    # 1. Ak máme v DB zapísanú poslednú revíziu, použijeme ju
                    if posledny:
                        try: return date.fromisoformat(str(posledny).strip())
                        except ValueError: pass
                    
                    # 2. Ak posledná chýba, dopočítame ju z nasledujúcej pomocou bezpečného čísla
                    if nasledujuci:
                        try:
                            nasl_dt = date.fromisoformat(str(nasledujuci).strip())
                            return nasl_dt - timedelta(days=int(roky_cislo * 365))
                        except ValueError: pass
                        
                    # 3. Ak nemáme vôbec nič, vrátime dnešok
                    return date.today()

                # Bezpečné načítanie periód s náhradnou hodnotou, ak sú v DB prázdne (None)
                stroj_p_rev = stroj.get('perioda_reviznej_skusky')
                if stroj_p_rev is None: stroj_p_rev = 2
                
                stroj_p_urad = stroj.get('perioda_uradnej_skusky')
                if stroj_p_urad is None: stroj_p_urad = 5
                
                stroj_p_odbpr = stroj.get('interval_odborna_pr')
                if stroj_p_odbpr is None: stroj_p_odbpr = 1.0
                
                stroj_p_odbsk = stroj.get('perioda_odbornej_skusky')
                if stroj_p_odbsk is None: stroj_p_odbsk = 1

                # Samotné priradenie hodnôt do formulára
                db_rev = zisti_predvoleny_datum('posledna_revizia', 'nasledujuca_revizia', minus_roky=1)
                db_rev_sk = zisti_predvoleny_datum('posledna_revizna_skuska', 'nasledujuca_revizna_skuska', minus_roky=stroj_p_rev)
                db_pod_ok = zisti_predvoleny_datum('posledna_podrobna_prehliadka_ok', 'nasledujuca_podrobna_prehliadka_ok', minus_roky=5)
                db_urad = zisti_predvoleny_datum('posledna_uradna_skuska', 'nasledujuca_uradna_skuska', minus_roky=stroj_p_urad)
                db_odb_pr = zisti_predvoleny_datum('posledna_odborna_prehliadka', 'nasledujuca_odborna_prehliadka', minus_roky=stroj_p_odbpr)
                db_odb_sk = zisti_predvoleny_datum('posledna_odborna_skuska', 'nasledujuca_odborna_skuska', minus_roky=stroj_p_odbsk)
                db_geom = zisti_predvoleny_datum('posledna_geometria', 'nasledujuca_geometria', minus_roky=10)

            

                with st.form(key=f"form_edit_{stroj_id}", clear_on_submit=False):
                    e_col1, e_col2 = st.columns(2)
                    
                    with e_col1:
                        new_nazov = st.text_input("Nový názov stroja:", value=stroj['nazov'], key=f"inp_nazov_{stroj_id}")
                        new_umiestnenie = st.text_input("Nové umiestnenie:", value=stroj['umiestnenie'] or "", key=f"inp_umiest_{stroj_id}")
                        
                        st.markdown("---")
                        st.markdown("**1. Revízia (ročne)**")
                        new_rev = st.date_input("Dátum poslednej revízie:", db_rev, key=f"inp_rev_{stroj_id}")
                        clear_rev = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_rev_{stroj_id}")

                        st.markdown("---")
                        st.markdown("**2. Revízna skúška**")
                        new_rev_sk = st.date_input("Dátum poslednej rev. skúšky:", db_rev_sk, key=f"inp_revsk_{stroj_id}")
                        clear_rev_sk = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_revsk_{stroj_id}")
                        
                        list_p_rev = [3, 2, 1]
                        stroj_p_rev = stroj.get('perioda_reviznej_skusky', 2)
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
                        stroj_p_urad = stroj.get('perioda_uradnej_skusky', 5)
                        p_urad_idx = list_p_urad.index(stroj_p_urad) if stroj_p_urad in list_p_urad else 3
                        new_p_urad = st.selectbox("Perióda Úradnej skúšky (roky):", list_p_urad, index=p_urad_idx, key=f"sel_urad_{stroj_id}")
                        
                        st.markdown("---")
                        st.markdown("**5. Odborná prehliadka**")
                        new_odb_pr = st.date_input("Dátum poslednej odbornej pr.:", db_odb_pr, key=f"inp_odbpr_{stroj_id}")
                        clear_odb_pr = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_odbpr_{stroj_id}")
                        
                        list_p_odbpr = [3.0, 2.0, 1.0, 0.5, 0.25]
                        stroj_p_odbpr = stroj.get('interval_odborna_pr', 1.0)
                        p_odbpr_idx = list_p_odbpr.index(stroj_p_odbpr) if stroj_p_odbpr in list_p_odbpr else 2
                        interval_odborna_pr = st.selectbox(
                            "Interval Odbornej prehliadky:", 
                            list_p_odbpr, index=p_odbpr_idx,
                            format_func=lambda x: "3 roky" if x == 3.0 else ("2 roky" if x == 2.0 else ("1 rok (ročne)" if x == 1.0 else ("6 mesiacov (polročne)" if x == 0.5 else "3 mesiace (štvrťročne)"))),
                            key=f"sel_odbpr_{stroj_id}"
                        )
                        
                        st.markdown("---")
                        st.markdown("**6. Odborná skúška**")
                        new_odb_sk = st.date_input("Dátum poslednej odbornej sk.:", db_odb_sk, key=f"inp_odbsk_{stroj_id}")
                        clear_odb_sk = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_odbsk_{stroj_id}")
                        
                        list_p_odbsk = [6, 4, 3, 2, 1]
                        stroj_p_odbsk = stroj.get('perioda_odbornej_skusky', 1)
                        p_odbsk_idx = list_p_odbsk.index(stroj_p_odbsk) if stroj_p_odbsk in list_p_odbsk else 4
                        new_p_odbsk = st.selectbox("Perióda Odbornej skúšky (roky):", list_p_odbsk, index=p_odbsk_idx, key=f"sel_odbsk_{stroj_id}")
                    
                    st.markdown("---")
                    new_ma_geom = st.checkbox("Vykonáva sa Geometrické zameranie?", value=stroj.get('vykonava_sa_geometria', False), key=f"chk_geom_{stroj_id}")
                    new_geom = st.date_input("Posledná Geometria dráhy:", db_geom, key=f"inp_geom_{stroj_id}") if new_ma_geom else None
                    clear_geom = st.checkbox("🗑️ Vymazať / Nechať nezaevidované", value=False, key=f"clear_geom_{stroj_id}") if new_ma_geom else False

                    # === FINÁLNE UKLADANIE ZMIEN (ZROVNANÉ ODSADENIE) ===
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
                        n_odb_pr = vypocitaj_nasledujuci(final_odb_pr, interval_odborna_pr)
                        
                        final_odb_sk = None if clear_odb_sk else new_odb_sk
                        n_odb_sk = vypocitaj_nasledujuci(final_odb_sk, int(new_p_odbsk))

                        final_geom = None if (clear_geom or not new_ma_geom) else new_geom
                        n_geom = vypocitaj_nasledujuci(final_geom, 10) if new_ma_geom else None

                        # Zadefinovanie premennej
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

                        # Blok ukladania presne v rovnakej úrovni odsadenia ako upravene_data
                        try:
                            supabase.table("stroje").update(upravene_data).eq("id", stroj_id).execute()
                            st.toast(f"Stroj '{new_nazov}' úspešne upravený! 💾")
                            st.session_state["aktualne_upravovany_id"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Chyba pri ukladaní zmien do databázy: {e}")
                   