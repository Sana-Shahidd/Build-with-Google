-- EMERGENCY CARDS (F-36) — backend-only table (no RLS policies)
create table public.emergency_cards (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  token text not null unique,                       -- secrets.token_urlsafe(18), in the QR URL
  full_name text not null check (char_length(full_name) between 2 and 80),
  blood_type public.blood_type,                     -- nullable: owner may not know it
  allergies text check (char_length(allergies) <= 120),
  lang text not null default 'ur' check (lang in ('en','es','ur')),
  show_phone boolean not null default false,        -- owner consents to show contact #1's number to scanners
  preferred_hospital_id uuid references public.organizations(id),
  consent_at timestamptz not null,                  -- consent box ticked (text read aloud)
  active boolean not null default true,
  scan_count int not null default 0,
  last_scanned_at timestamptz,
  created_at timestamptz not null default now()
);
create index emergency_cards_owner_idx on public.emergency_cards (owner_user_id);

create table public.card_contacts (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references public.emergency_cards(id) on delete cascade,
  position smallint not null check (position between 1 and 3),
  name text not null check (char_length(name) between 1 and 60),
  relation text check (char_length(relation) <= 30),
  phone_enc text not null,                          -- crypto.encrypt_phone
  phone_hash text not null,                         -- crypto.phone_hash
  telegram_chat_id bigint,                          -- set when the contact links Telegram (F-41)
  unique (card_id, position)
);

create table public.card_scans (
  id bigserial primary key,
  card_id uuid not null references public.emergency_cards(id) on delete cascade,
  report_id uuid references public.reports(id) on delete set null,   -- set when "Get help" is pressed
  ip_hash text,                                     -- HMAC of IP, never plain
  scanned_at timestamptz not null default now()
);
create index card_scans_card_idx on public.card_scans (card_id, scanned_at desc);

-- PLACE PLANS (F-37) — backend-only table
create table public.place_plans (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  token text not null unique,
  name text not null check (char_length(name) between 2 and 80),
  place_type text not null check (place_type in ('home','shop','school','mosque','factory','office','other')),
  location extensions.geography(Point,4326) not null,
  lat double precision generated always as (extensions.st_y(location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(location::extensions.geometry)) stored,
  location_label text,
  landmark_text text,                               -- English line from F-38 at creation
  landmark_local text,                              -- local-language line
  nearest jsonb not null default '[]',              -- [{org_id,name,type,distance_m,eta_min,phone}] snapshot, max 3
  lang text not null default 'ur' check (lang in ('en','es','ur')),
  consent_at timestamptz not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create index place_plans_owner_idx on public.place_plans (owner_user_id);

-- COLUMNS ON EXISTING TABLES
alter table public.reports   add column if not exists card_id  uuid references public.emergency_cards(id) on delete set null;
alter table public.reports   add column if not exists place_id uuid references public.place_plans(id)     on delete set null;
alter table public.incidents add column if not exists landmark_text  text;      -- F-38, English
alter table public.incidents add column if not exists landmark_local text;      -- F-38, local language
alter table public.incidents add column if not exists landmark_at    timestamptz;
alter table public.incidents add column if not exists card_id uuid references public.emergency_cards(id) on delete set null;  -- first card scanned for this incident

-- TELEGRAM LINK CODES can now link a card contact (F-41)
alter table public.telegram_link_codes add column if not exists contact_id uuid references public.card_contacts(id) on delete cascade;
alter table public.telegram_link_codes drop constraint if exists telegram_link_codes_check;
alter table public.telegram_link_codes add check (num_nonnulls(profile_id, member_id, staff_id, org_id, contact_id) = 1);

-- (If the old check has a different name, find it first:
--  select conname from pg_constraint where conrelid = 'public.telegram_link_codes'::regclass and contype = 'c';)

-- RLS: backend only (no policies) for all new tables
alter table public.emergency_cards enable row level security;
alter table public.card_contacts   enable row level security;
alter table public.card_scans      enable row level security;
alter table public.place_plans     enable row level security;

-- BLACK SPOTS (F-45, Tier L): ~200 m grid (0.002 degrees)
create or replace function public.blackspots(p_days int default 90, p_limit int default 10)
returns table (lat double precision, lng double precision, incident_count bigint)
language sql stable as $$
  select extensions.st_y(c)::double precision, extensions.st_x(c)::double precision, count(*)
  from (
    select extensions.st_snaptogrid(location::extensions.geometry, 0.002) as c
    from public.incidents
    where incident_type = 'road_accident' and location is not null and status <> 'dismissed'
      and created_at > now() - make_interval(days => p_days)
  ) g
  group by c order by count(*) desc limit p_limit;
$$;
revoke all on function public.blackspots(int,int) from public, anon, authenticated;
