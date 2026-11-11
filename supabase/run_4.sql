-- Dashboard read access (T-09). Run once in the Supabase SQL editor.
-- The "Automatically expose new tables" setting is off, so the `authenticated` role (logged-in
-- responders; also anonymous reporters, who are blocked by the RLS policies) needs explicit grants.
-- Only the tables the dashboard reads, SELECT only. Row access is still decided by the RLS
-- policies in 0004_rls.sql; all writes go through the backend (service role).

grant usage on schema public to authenticated;

grant select on
  public.organizations,
  public.hospital_details,
  public.profiles,
  public.incidents,
  public.reports,
  public.hospital_assignments,
  public.alert_targets,
  public.deliveries,
  public.community_responses,
  public.incident_events,
  public.agent_activity,
  public.ambulances,
  public.on_call_staff,
  public.patient_arrivals
to authenticated;

-- helper functions used inside the RLS policies
grant execute on function public.auth_role() to authenticated;
grant execute on function public.auth_org_id() to authenticated;
grant execute on function public.can_view_incident(uuid) to authenticated;

notify pgrst, 'reload schema';
