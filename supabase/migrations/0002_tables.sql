-- ORGANIZATIONS: hospitals and stations (seeded from OpenStreetMap)
create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  type public.org_type not null,
  name text not null,
  osm_ref text unique,               -- 'node/123', 'way/456', 'relation/789'
  source text not null default 'seed' check (source in ('seed','osm_live','manual')),
  location extensions.geography(Point,4326) not null,
  lat double precision generated always as (extensions.st_y(location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(location::extensions.geometry)) stored,
  address text,
  public_phone text,                 -- public help-desk number, safe to show
  alert_phone_enc text,              -- Fernet-encrypted E.164, receives SMS/calls
  backup_phone_enc text,             -- escalation level 2
  email text,
  telegram_chat_id bigint,
  backup_telegram_chat_id bigint,
  lang text not null default 'en' check (lang in ('en','es','ur')),
  is_mock boolean not null default true,
  created_at timestamptz not null default now()
);
create index organizations_location_gix on public.organizations using gist (location);
create index organizations_type_idx on public.organizations (type);

create table public.hospital_details (
  org_id uuid primary key references public.organizations(id) on delete cascade,
  capabilities public.capability[] not null default '{general}',
  er_beds_total int not null default 10 check (er_beds_total >= 0),
  er_beds_available int not null default 5 check (er_beds_available >= 0),
  icu_available int not null default 2 check (icu_available >= 0),
  blood_stock jsonb not null default
    '{"A+":10,"A-":4,"B+":10,"B-":4,"AB+":5,"AB-":2,"O+":12,"O-":5}',
  accepting_patients boolean not null default true,
  capacity_known boolean not null default false,   -- true for seeded/mock or console-updated hospitals
  updated_at timestamptz not null default now(),
  updated_by uuid
);

-- PROFILES: one per auth user (responders and anonymous reporters)
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role public.user_role not null default 'reporter',
  display_name text,
  org_id uuid references public.organizations(id),
  telegram_chat_id bigint,
  phone_enc text,
  lang text not null default 'en' check (lang in ('en','es','ur')),
  created_at timestamptz not null default now()
);

-- INCIDENTS
create table public.incidents (
  id uuid primary key default gen_random_uuid(),
  short_code text not null unique,                  -- 'GM-7K3Q'
  country_code text,                                -- ISO 3166-1 alpha-2 of the incident location (F-35)
  incident_type public.incident_type not null default 'other',
  severity public.severity not null default 'medium',
  status public.incident_status not null default 'review',
  location extensions.geography(Point,4326),
  lat double precision generated always as (extensions.st_y(location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(location::extensions.geometry)) stored,
  best_accuracy_m real,
  location_label text,
  summary_en text,
  summary_local text,                -- summary in the main report language
  local_lang text,                   -- 'en' | 'es' | 'ur' | other ISO code
  est_casualties_min int not null default 0 check (est_casualties_min >= 0),
  est_casualties_max int not null default 0 check (est_casualties_max >= 0),
  injury_types public.injury_type[] not null default '{}',
  needs public.need_type[] not null default '{}',
  ongoing_danger boolean not null default false,
  confidence real not null default 0 check (confidence between 0 and 1),
  report_count int not null default 0,
  unique_reporters int not null default 0,
  silent boolean not null default false,
  verified_at timestamptz,
  verified_by uuid,
  dismissed_reason text,
  closed_at timestamptz,
  closed_by uuid,
  after_action_md text,
  first_alert_at timestamptz,          -- analytics
  first_ack_at timestamptz,            -- analytics
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index incidents_location_gix on public.incidents using gist (location);
create index incidents_status_created_idx on public.incidents (status, created_at desc);

-- REPORTS
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  client_report_id uuid not null unique,            -- idempotency key from client / webhook sid hash
  reporter_id uuid references auth.users(id),
  channel public.report_channel not null,
  input_type public.report_input not null,
  raw_text text,
  transcript text,
  transcript_lang text,
  audio_path text,                                   -- storage path in bucket report-media
  photo_path text,
  location extensions.geography(Point,4326),
  lat double precision generated always as (extensions.st_y(location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(location::extensions.geometry)) stored,
  accuracy_m real,
  location_hint text,
  country_code text,                                 -- detected from location (F-35)
  lang text check (lang in ('en','es','ur')),    -- reporter UI language
  silent boolean not null default false,
  phone_hash text,                                   -- HMAC of E.164, never plain
  phone_verified boolean not null default false,
  extraction jsonb,                                  -- IncidentExtraction as JSON
  ai_provider text check (ai_provider in ('gemini','groq','rules','sos_default')),
  ai_confidence real,
  followup_question text,
  followup_answer text,
  first_aid_keys text[] not null default '{}',
  incident_id uuid references public.incidents(id),
  status public.report_status not null default 'received',
  error text,
  ip_hash text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);
create index reports_incident_idx on public.reports (incident_id);
create index reports_reporter_idx on public.reports (reporter_id);
create index reports_location_gix on public.reports using gist (location);

-- HOSPITAL ASSIGNMENTS (casualty spreading result)
create table public.hospital_assignments (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  hospital_id uuid not null references public.organizations(id),
  assigned_casualties int not null check (assigned_casualties >= 0),
  critical int not null default 0 check (critical >= 0),
  eta_minutes real,
  over_capacity boolean not null default false,
  reason text,
  planned_by text not null default 'autopilot' check (planned_by in ('agent','autopilot')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (incident_id, hospital_id)
);

-- ON-CALL DOCTORS
create table public.on_call_staff (
  id uuid primary key default gen_random_uuid(),
  hospital_id uuid not null references public.organizations(id) on delete cascade,
  full_name text not null,
  specialty public.specialty not null,
  phone_enc text,
  email text,
  telegram_chat_id bigint,
  lang text not null default 'en' check (lang in ('en','es','ur')),
  priority int not null default 1,
  on_duty boolean not null default true,
  created_at timestamptz not null default now()
);
create index on_call_staff_hosp_spec_idx on public.on_call_staff (hospital_id, specialty, priority);

-- COMMUNITY (donors, volunteers, registered emergency profiles for SMS/missed call)
create table public.community_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users(id) on delete set null,
  display_name text,
  phone_enc text not null,
  phone_hash text not null unique,
  telegram_chat_id bigint,
  home_location extensions.geography(Point,4326),
  lat double precision generated always as (extensions.st_y(home_location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(home_location::extensions.geometry)) stored,
  is_donor boolean not null default false,
  blood_type public.blood_type,
  skills public.member_skill[] not null default '{}',
  lang text not null default 'ur' check (lang in ('en','es','ur')),
  consent_at timestamptz not null,
  last_donor_ping_at timestamptz,
  last_volunteer_ping_at timestamptz,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create index community_members_location_gix on public.community_members using gist (home_location);

-- ALERT TARGETS (one per recipient per incident; holds ack + escalation state)
create table public.alert_targets (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  recipient_kind public.recipient_kind not null,
  recipient_org_id uuid references public.organizations(id),
  recipient_staff_id uuid references public.on_call_staff(id),
  recipient_member_id uuid references public.community_members(id),
  recipient_profile_id uuid references public.profiles(id),
  recipient_label text not null,              -- e.g. 'Jinnah Hospital ER', 'Dr. A (burns)'
  is_standby boolean not null default false,  -- hospital standby for unverified incidents
  status public.target_status not null default 'queued',
  ack_due_at timestamptz,                     -- null = never escalate (donor/volunteer/public)
  acknowledged_at timestamptz,
  acknowledged_via public.delivery_channel,
  acknowledged_by text,
  escalation_level smallint not null default 0,
  ack_token_jti uuid unique,                  -- current valid ack token id
  ack_token_used_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index alert_targets_unique_recipient on public.alert_targets (
  incident_id, recipient_kind,
  coalesce(recipient_org_id,     '00000000-0000-0000-0000-000000000000'),
  coalesce(recipient_staff_id,   '00000000-0000-0000-0000-000000000000'),
  coalesce(recipient_member_id,  '00000000-0000-0000-0000-000000000000'),
  coalesce(recipient_profile_id, '00000000-0000-0000-0000-000000000000')
);
create index alert_targets_due_idx on public.alert_targets (ack_due_at)
  where status in ('sent','delivered','escalated') and ack_due_at is not null;

-- DELIVERIES (one per channel message)
create table public.deliveries (
  id uuid primary key default gen_random_uuid(),
  target_id uuid not null references public.alert_targets(id) on delete cascade,
  channel public.delivery_channel not null,
  to_masked text,                              -- '+1 *** *** 4567', 'chat ...891'
  push_subscription_id uuid,
  is_update boolean not null default false,
  provider_message_id text,                    -- Twilio SID / Telegram message_id / Resend id
  status public.delivery_status not null default 'queued',
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index deliveries_target_idx on public.deliveries (target_id);
create unique index deliveries_push_once on public.deliveries (target_id, push_subscription_id)
  where push_subscription_id is not null;

create table public.community_responses (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  member_id uuid not null references public.community_members(id) on delete cascade,
  role text not null check (role in ('donor','volunteer')),
  response public.community_response not null,
  created_at timestamptz not null default now(),
  unique (incident_id, member_id, role)
);

-- AMBULANCES (simulated)
create table public.ambulances (
  id uuid primary key default gen_random_uuid(),
  station_id uuid not null references public.organizations(id),
  call_sign text not null unique,                 -- 'EMS-HOU-07' (prefix from country profile)
  status public.ambulance_status not null default 'available',
  location extensions.geography(Point,4326) not null,
  lat double precision generated always as (extensions.st_y(location::extensions.geometry)) stored,
  lng double precision generated always as (extensions.st_x(location::extensions.geometry)) stored,
  incident_id uuid references public.incidents(id),
  destination_hospital_id uuid references public.organizations(id),
  route jsonb,                                    -- GeoJSON LineString coordinates [[lng,lat],...]
  route_progress_m real not null default 0,
  route_length_m real,
  stage_started_at timestamptz,
  updated_at timestamptz not null default now()
);

-- PATIENT ARRIVALS (family finder source)
create table public.patient_arrivals (
  id uuid primary key default gen_random_uuid(),
  hospital_id uuid not null references public.organizations(id),
  incident_id uuid references public.incidents(id),
  full_name text,
  name_normalized text,                 -- lower(unaccent-free trimmed name), set by backend
  approx_age smallint,
  sex public.sex not null default 'unknown',
  wristband_code text,
  created_by uuid,
  created_at timestamptz not null default now()
);
create index patient_arrivals_name_trgm on public.patient_arrivals
  using gin (name_normalized extensions.gin_trgm_ops);

create table public.family_queries (
  id uuid primary key default gen_random_uuid(),
  requester_user_id uuid not null,
  query_name text not null,
  incident_code text,
  result_count int not null,
  created_at timestamptz not null default now()
);

-- WEB PUSH
create table public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  coarse_location extensions.geography(Point,4326) not null,
  lang text not null default 'en' check (lang in ('en','es','ur')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index push_subscriptions_location_gix on public.push_subscriptions using gist (coarse_location);

-- TELEGRAM LINKING
create table public.telegram_link_codes (
  code text primary key,                -- 16 url-safe chars
  profile_id uuid references public.profiles(id) on delete cascade,
  member_id uuid references public.community_members(id) on delete cascade,
  staff_id uuid references public.on_call_staff(id) on delete cascade,
  org_id uuid references public.organizations(id) on delete cascade,  -- links org alert chat
  expires_at timestamptz not null,
  used_at timestamptz,
  check (num_nonnulls(profile_id, member_id, staff_id, org_id) = 1)
);

-- TIMELINE + AUDIT
create table public.incident_events (
  id bigserial primary key,
  incident_id uuid not null references public.incidents(id) on delete cascade,
  kind text not null,      -- 'created','report_merged','verified','dismissed','alert_sent','acknowledged',
                           -- 'escalated','no_response','assignment','doctor_called','donors_pinged',
                           -- 'volunteers_pinged','public_alert','ambulance_status','closed','update_sent'
  message text not null,   -- human-readable, English
  data jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index incident_events_incident_idx on public.incident_events (incident_id, created_at desc);

create table public.audit_log (
  id bigserial primary key,
  actor_kind text not null,     -- 'system','reporter','responder','webhook','job'
  actor_id text,
  action text not null,
  entity text not null,
  entity_id text,
  details jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- AGENT ACTIVITY FEED (F-33)
create table public.agent_activity (
  id bigserial primary key,
  incident_id uuid references public.incidents(id) on delete cascade,
  report_id uuid references public.reports(id) on delete cascade,
  agent public.agent_name not null,
  kind public.activity_kind not null,
  message text not null check (char_length(message) <= 200),  -- human-readable, English, no PII
  model text,                     -- model id used, null for rule/autopilot
  tool text,                      -- tool name for tool_call/tool_result
  latency_ms int,
  data jsonb not null default '{}', -- small structured details (no PII, no prompts)
  created_at timestamptz not null default now()
);
create index agent_activity_incident_idx on public.agent_activity (incident_id, created_at desc);
create index agent_activity_created_idx on public.agent_activity (created_at desc);

-- LOCATION CACHES (F-35)
create table public.geo_country_cache (
  tile_key text primary key,            -- 'lat1,lng1' rounded to 1 decimal, e.g. '29.8,-95.4'
  country_code text,                    -- null = lookup returned no country
  location_label text,
  fetched_at timestamptz not null default now()
);

create table public.osm_discovery_cache (
  tile_key text primary key,            -- same rounding as above
  fetched_at timestamptz not null default now(),
  hospitals_found int not null default 0,
  orgs_inserted int not null default 0,
  status text not null check (status in ('ok','failed'))
);

create table public.tts_cache (
  key text primary key,         -- sha256(lang + text)
  url text not null,
  created_at timestamptz not null default now()
);

-- updated_at trigger
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at = now(); return new; end $$;

create trigger t_incidents_upd before update on public.incidents
  for each row execute function public.touch_updated_at();
create trigger t_targets_upd before update on public.alert_targets
  for each row execute function public.touch_updated_at();
create trigger t_deliveries_upd before update on public.deliveries
  for each row execute function public.touch_updated_at();
create trigger t_assign_upd before update on public.hospital_assignments
  for each row execute function public.touch_updated_at();
create trigger t_amb_upd before update on public.ambulances
  for each row execute function public.touch_updated_at();
create trigger t_push_upd before update on public.push_subscriptions
  for each row execute function public.touch_updated_at();
