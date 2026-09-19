# ⚙️ Profesionálny Systém Revízií a Prehliadok — GEMINI.md

Welcome to the **Profesionálny Systém Revízií a Prehliadok** (Machine Revision and Inspection System) codebase. This document serves as the guide and instructional context for developers and AI assistants working in this repository.

---

## 📌 Project Overview
This application is a professional tracking and management system for statutory safety inspections, periodic revisions, and tests of machines and equipment (specifically focused on lifting appliances, cranes, and VTZ/UTZ classifications). It calculates future deadlines, displays statuses in dual-month and monthly archive calendars, manages delayed inspections with reasons, and supports data exports/imports via Excel.

### 🛠️ Key Technologies
- **Frontend & UI:** [Streamlit](https://streamlit.io/) (Python-based interactive web framework)
- **Database / Backend:** [Supabase](https://supabase.com/) (PostgreSQL-as-a-service, accessed via the Python SDK)
- **Data processing:** [Pandas](https://pandas.pydata.org/)
- **Excel manipulation & styling:** [openpyxl](https://openpyxl.readthedocs.io/)
- **Calendar & Datetime:** Standard Python `calendar`, `datetime`

### 🏗️ Architecture & Database Schema
The project is structured as a two-tier application: a Streamlit client connecting directly to Supabase via secrets credentials.

The system interacts with two main tables in Supabase:

#### 1. Table: `stroje` (Machines)
Holds information about machines, the dates of their last inspections, periodicities, and calculated upcoming dates.
- `id` (Primary Key, integer / uuid)
- `nazov` (text, unique machine name)
- `umiestnenie` (text, location/hall)
- `druh_systemu` (text: e.g., `"VTZ"`, `"UTZ"`)
- `legislativna_skupina` (text)
- `legislativny_druh` (text)
- `evidencne_cislo` (text)
- `cislo_vybavenia` (text)
- `firma` (text)
- `voj` (text)
- **Revision Dates (Last vs. Next calculated):**
  - `posledna_revizia` / `nasledujuca_revizia` (ISO dates, yearly)
  - `posledna_revizna_skuska` / `nasledujuca_revizna_skuska` (ISO dates, periodicity: 1, 2, or 3 years stored in `perioda_reviznej_skusky`)
  - `posledna_podrobna_prehliadka_ok` / `nasledujuca_podrobna_prehliadka_ok` (ISO dates, 5-yearly)
  - `posledna_uradna_skuska` / `nasledujuca_uradna_skuska` (ISO dates, periodicity: 3, 4, 5, 6, 9, or 10 years stored in `perioda_uradnej_skusky`)
  - `posledna_odborna_prehliadka` / `nasledujuca_odborna_prehliadka` (ISO dates, interval: 0.25, 0.5, 1.0, 2.0, 3.0 years)
  - `posledna_odborna_skuska` / `nasledujuca_odborna_skuska` (ISO dates, periodicity: 1, 2, 3, 4, or 6 years stored in `perioda_odbornej_skusky`)
  - `vykonava_sa_geometria` (boolean, indicates if geometry is required)
  - `posledna_geometria` / `nasledujuca_geometria` (ISO dates, 10-yearly)

#### 2. Table: `poznamky_restov` (Overdue Notes)
Stores explanation notes for overdue/late inspections.
- `stroj_id` (foreign key to `stroje.id`)
- `typ_kontroly` (text, name of the inspection column e.g. `"nasledujuca_revizia"`)
- `text_poznamky` (text, explanation for the delay)

---

## 🚀 Building and Running

### 📦 Prerequisites & Installation
Ensure you have Python 3.9+ installed. Install the required dependencies:

```bash
pip install streamlit pandas openpyxl supabase
```

*(Note: There is no existing `requirements.txt` in this workspace, so install these packages directly or create one with these requirements).*

### 🔑 Configuration (Supabase Connection)
The application expects Supabase and application secrets in Streamlit's secrets configuration.

⚠️ **Important Note on Secrets File Typo:**
In this project directory, the configuration file is currently named:
`.streamlit/seacrets.toml` (with an extra **'a'**)

For Streamlit to automatically load these secrets, the file **must** be renamed to:
`.streamlit/secrets.toml`

Its structure is as follows:
```toml
MOJE_TAJNE_HESLO = "IWannaBeLikeAKevin"
SUPABASE_URL = "https://fdfsifvklwsdgeskgadc.supabase.co"
SUPABASE_KEY = "sb_publishable_rJ815qf4quLjznGgEPT7Tw_UeP3lITQ"
```

### 🏃 Running the Application
To run the web interface locally, execute:

```bash
streamlit run app.py
```

---

## 🎨 Application Modules (Tabs)
The UI is divided into four main tabs:
1. **🔔 Prehľad a Upozornenia (Overview & Alerts):** Dual-month calendar highlighting today's, upcoming, and completed revisions. Overdue tasks are displayed below with notes explaining delays (saved in `poznamky_restov`).
2. **📅 Mesačný Kalendár (Monthly Calendar):** Interactive planner allowing the user to view inspection statuses for any month/year.
3. **➕ Pridať / Evidovať Stroj (Add Machine):** Registration form with auto-calculation of future inspection terms. Duplication check runs in real-time.
4. **📋 Zoznam strojov a úprava (Machine List, Edit, Export & Import):**
   - **Excel Export:** Creates highly formatted Excel files with custom headers and styled borders.
   - **Excel Import:** Allows bulk upload, formats dates properly, and cleans float-to-string conversion artifacts (such as trailing `.0`).
   - **Edit & Delete:** Inline editors for individual machine records with protective defaults for null values.

---

## 🛠️ Development Conventions & Guidelines

- **Language:** The user interface, text outputs, and database comments are in Slovak (SK), whereas variable names, database keys, and logical constructs are in English/mixed (e.g., `vypocitaj_nasledujuci`, `vsetky_stroje`, but column keys like `nasledujuca_revizia`). Maintain this convention.
- **Date Handling:**
  - Standardized date formatting for the Slovak audience is `DD.MM.YYYY` in display.
  - Internal database representation is standard `YYYY-MM-DD` string format.
  - Python calculation utilizes `datetime.date` and `datetime.timedelta`.
- **Typing & Validation:**
  - When importing or reading from Supabase, always expect `None` values and provide fallback defaults (such as default periods for calculations) to avoid `TypeError` or `ValueError` crashes.
  - Use `try/except` blocks around Supabase API queries to gracefully report errors to the user via `st.error(...)`.
