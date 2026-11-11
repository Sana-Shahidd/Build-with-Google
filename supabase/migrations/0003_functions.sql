-- Create a profile for every new auth user (anonymous reporters included)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, role) values (new.id, 'reporter')
  on conflict (id) do nothing;
  return new;
end $$;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- Role helpers (SECURITY DEFINER to avoid RLS recursion)
create or replace function public.auth_role() returns public.user_role
language sql stable security definer set search_path = public as $$
  select role from public.profiles where id = auth.uid()
$$;

create or replace function public.auth_org_id() returns uuid
language sql stable security definer set search_path = public as $$
  select org_id from public.profiles where id = auth.uid()
$$;

create or replace function public.can_view_incident(p_incident uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select
    public.auth_role() in ('dispatcher','admin')
    or exists (
      select 1 from public.alert_targets t
      where t.incident_id = p_incident
        and t.recipient_org_id is not null
        and t.recipient_org_id = public.auth_org_id()
    )
$$;

-- Nearest organizations of a type
create or replace function public.nearest_orgs(
  p_type public.org_type, p_lat double precision, p_lng double precision,
  p_radius_m double precision, p_limit int)
returns table (id uuid, name text, lat double precision, lng double precision, distance_m double precision)
language sql stable set search_path = public, extensions as $$
  select o.id, o.name, o.lat, o.lng,
         st_distance(o.location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography) as distance_m
  from public.organizations o
  where o.type = p_type
    and st_dwithin(o.location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography, p_radius_m)
  order by distance_m
  limit p_limit
$$;

-- Merge candidates
create or replace function public.incidents_near_for_merge(
  p_lat double precision, p_lng double precision, p_radius_m double precision, p_since timestamptz)
returns table (id uuid, incident_type public.incident_type, summary_en text,
               created_at timestamptz, distance_m double precision)
language sql stable set search_path = public, extensions as $$
  select i.id, i.incident_type, i.summary_en, i.created_at,
         st_distance(i.location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography) as distance_m
  from public.incidents i
  where i.status in ('review','unverified','verified')
    and i.created_at >= p_since
    and i.location is not null
    and st_dwithin(i.location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography, p_radius_m)
  order by distance_m
  limit 3
$$;

-- Community members near a point (donors/volunteers selection is finished in Python)
create or replace function public.members_near(
  p_lat double precision, p_lng double precision, p_radius_m double precision)
returns table (id uuid, is_donor boolean, blood_type public.blood_type, skills public.member_skill[],
               telegram_chat_id bigint, lang text, last_donor_ping_at timestamptz,
               last_volunteer_ping_at timestamptz, distance_m double precision)
language sql stable set search_path = public, extensions as $$
  select m.id, m.is_donor, m.blood_type, m.skills, m.telegram_chat_id, m.lang,
         m.last_donor_ping_at, m.last_volunteer_ping_at,
         st_distance(m.home_location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography)
  from public.community_members m
  where m.active and m.home_location is not null
    and st_dwithin(m.home_location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography, p_radius_m)
  order by 9
$$;

create or replace function public.push_subs_near(
  p_lat double precision, p_lng double precision, p_radius_m double precision)
returns setof public.push_subscriptions
language sql stable set search_path = public, extensions as $$
  select * from public.push_subscriptions s
  where st_dwithin(s.coarse_location, st_setsrid(st_makepoint(p_lng, p_lat),4326)::geography, p_radius_m)
$$;

-- Family finder (returns only safe fields)
create or replace function public.family_search(
  p_query text, p_since timestamptz, p_incident uuid, p_tz text)
returns table (hospital_name text, hospital_phone text, arrived_date date, score real)
language sql stable set search_path = public, extensions as $$
  select o.name, o.public_phone, (a.created_at at time zone p_tz)::date,
         similarity(a.name_normalized, lower(trim(p_query))) as score
  from public.patient_arrivals a
  join public.organizations o on o.id = a.hospital_id
  where a.name_normalized is not null
    and a.created_at >= p_since
    and (p_incident is null or a.incident_id = p_incident)
    and similarity(a.name_normalized, lower(trim(p_query))) >= 0.4
  order by score desc
  limit 3
$$;

-- Analytics helpers
create or replace view public.v_incident_timings with (security_invoker = true) as
select i.id, i.short_code, i.incident_type, i.severity, i.created_at,
       extract(epoch from (i.first_alert_at - i.created_at)) as secs_to_first_alert,
       extract(epoch from (i.first_ack_at - i.first_alert_at)) as secs_alert_to_ack
from public.incidents i;

create or replace view public.v_target_ack_times with (security_invoker = true) as
select t.recipient_org_id, o.name as org_name, t.recipient_kind,
       extract(epoch from (t.acknowledged_at - t.created_at)) as secs_to_ack,
       t.escalation_level, t.status
from public.alert_targets t
left join public.organizations o on o.id = t.recipient_org_id;
