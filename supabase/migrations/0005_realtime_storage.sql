alter publication supabase_realtime add table
  public.incidents, public.alert_targets, public.hospital_assignments,
  public.ambulances, public.incident_events, public.hospital_details,
  public.community_responses, public.agent_activity;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('report-media', 'report-media', false, 10485760,
   array['audio/webm','audio/ogg','audio/mp4','audio/mpeg','audio/wav','image/jpeg']),
  ('tts', 'tts', true, 2097152, array['audio/mpeg'])
on conflict (id) do nothing;
-- No storage policies for report-media: only the backend (service role) uploads and creates
-- signed URLs (10 min). tts is public-read so Twilio can fetch <Play> URLs.
