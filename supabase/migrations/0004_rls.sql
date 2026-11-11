alter table public.organizations        enable row level security;
alter table public.hospital_details     enable row level security;
alter table public.profiles             enable row level security;
alter table public.incidents            enable row level security;
alter table public.reports              enable row level security;
alter table public.hospital_assignments enable row level security;
alter table public.on_call_staff        enable row level security;
alter table public.community_members    enable row level security;
alter table public.alert_targets        enable row level security;
alter table public.deliveries           enable row level security;
alter table public.community_responses  enable row level security;
alter table public.ambulances           enable row level security;
alter table public.patient_arrivals     enable row level security;
alter table public.family_queries       enable row level security;
alter table public.push_subscriptions   enable row level security;
alter table public.telegram_link_codes  enable row level security;
alter table public.incident_events      enable row level security;
alter table public.audit_log            enable row level security;
alter table public.tts_cache            enable row level security;
alter table public.geo_country_cache    enable row level security;
alter table public.osm_discovery_cache  enable row level security;
alter table public.agent_activity       enable row level security;

-- SELECT policies only. No INSERT/UPDATE/DELETE policies exist: all writes go through the backend.

create policy orgs_read on public.organizations for select to authenticated
  using (public.auth_role() <> 'reporter');
create policy hosp_details_read on public.hospital_details for select to authenticated
  using (public.auth_role() <> 'reporter');

create policy profiles_self on public.profiles for select to authenticated
  using (id = auth.uid() or public.auth_role() in ('dispatcher','admin'));

create policy incidents_read on public.incidents for select to authenticated
  using (public.can_view_incident(id));

create policy reports_read on public.reports for select to authenticated
  using (reporter_id = auth.uid()
         or (incident_id is not null and public.can_view_incident(incident_id)));

create policy assignments_read on public.hospital_assignments for select to authenticated
  using (public.can_view_incident(incident_id));

create policy targets_read on public.alert_targets for select to authenticated
  using (public.can_view_incident(incident_id));

create policy deliveries_read on public.deliveries for select to authenticated
  using (public.auth_role() in ('dispatcher','admin'));

create policy responses_read on public.community_responses for select to authenticated
  using (public.can_view_incident(incident_id));

create policy events_read on public.incident_events for select to authenticated
  using (public.can_view_incident(incident_id));

create policy activity_read on public.agent_activity for select to authenticated
  using (public.auth_role() in ('dispatcher','admin')
         or (incident_id is not null and public.can_view_incident(incident_id)));

create policy ambulances_read on public.ambulances for select to authenticated
  using (public.auth_role() <> 'reporter');

create policy staff_read on public.on_call_staff for select to authenticated
  using (public.auth_role() in ('dispatcher','admin')
         or (public.auth_role() = 'hospital_staff' and hospital_id = public.auth_org_id()));

create policy arrivals_read on public.patient_arrivals for select to authenticated
  using (public.auth_role() in ('dispatcher','admin')
         or (public.auth_role() = 'hospital_staff' and hospital_id = public.auth_org_id()));

-- geo_country_cache, osm_discovery_cache, community_members, family_queries, push_subscriptions, telegram_link_codes, audit_log,
-- tts_cache: NO policies → invisible to the frontend (backend service role only).
