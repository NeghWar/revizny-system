-- ============================================================
-- ZABEZPEČENIE DATABÁZY (Row-Level Security)
-- Reakcia na upozornenie Supabase:
--   "Anyone with your project URL can read, edit, and delete all data
--    in this table because Row-Level Security is not enabled."
--
-- Spusti v Supabase: Dashboard -> SQL Editor -> New query -> vlož -> RUN
-- ============================================================
--
-- PREČO TAKTO:
--   Aplikácia beží na serveri (Streamlit) a používa SERVEROVÝ "secret" kľúč
--   (SUPABASE_SECRET_KEY = sb_secret_...). Ten RLS OBCHÁDZA, takže verejné API
--   môžeme úplne zavrieť: zapneme RLS a NEPRIDÁME žiadne verejné policies.
--
-- VÝSLEDOK:
--   * cez verejné API (project URL + publishable kľúč) sa nedá čítať/meniť/mazať
--   * aplikácia funguje ďalej, lebo server komunikuje secret kľúčom
-- ============================================================

-- 1) Zapni RLS na všetkých tabuľkách, ktoré aplikácia používa
alter table public.stroje           enable row level security;
alter table public.poznamky_restov  enable row level security;
alter table public.historia_poruch  enable row level security;
alter table public.historia_rokov   enable row level security;
alter table public.ulohy            enable row level security;

-- 2) Odstráň nebezpečnú policy, ktorá otvárala tabuľku "stroje" úplne všetkým
--    (aj anonymným používateľom)
drop policy if exists "Umožniť všetko pre anonymných používateľov" on public.stroje;

-- 3) Kontrola č. 1: stav RLS (očakávame pri všetkých rowsecurity = true)
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
order by tablename;

-- 4) Kontrola č. 2: zoznam existujúcich policies (nemá tu ostať nič verejné)
select tablename, policyname, roles, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
