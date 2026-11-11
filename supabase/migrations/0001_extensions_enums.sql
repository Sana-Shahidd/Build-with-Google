create extension if not exists postgis with schema extensions;
create extension if not exists pg_trgm with schema extensions;

create type public.user_role as enum
  ('reporter','dispatcher','hospital_staff','police','rescue','fire','admin');

create type public.org_type as enum
  ('hospital','police_station','rescue_station','fire_station');

create type public.report_channel as enum ('app','sms','missed_call');
create type public.report_input   as enum ('sos','voice','photo','text');
create type public.report_status  as enum ('received','processing','processed','failed');

create type public.incident_type as enum
  ('attack_shooting','explosion','fire','road_accident','building_collapse',
   'medical','riot_crowd','flood','other');

create type public.severity as enum ('low','medium','high','critical');

create type public.incident_status as enum
  ('review','unverified','verified','closed','dismissed');

create type public.injury_type as enum
  ('gunshot','blast_shrapnel','burns','fracture','head_injury','bleeding','crush',
   'smoke_inhalation','drowning','cardiac','unconscious','breathing_difficulty','unknown');

create type public.need_type as enum ('ambulance','police','fire','rescue');

create type public.capability as enum
  ('trauma','burns','neuro','orthopedic','cardiac','pediatric','general');

create type public.specialty as enum
  ('trauma_surgeon','burn_specialist','neurosurgeon','orthopedic_surgeon','cardiologist',
   'anesthetist','emergency_physician','general_surgeon','pediatrician');

create type public.recipient_kind as enum
  ('hospital','police','rescue','fire','doctor','donor','volunteer','public','dispatcher');

create type public.target_status as enum
  ('queued','sent','delivered','acknowledged','escalated','no_response','failed');

create type public.delivery_channel as enum
  ('telegram','sms','voice','email','push','dashboard');

create type public.delivery_status as enum ('queued','sent','delivered','failed');

create type public.ambulance_status as enum
  ('available','en_route_scene','at_scene','en_route_hospital','at_hospital');

create type public.blood_type as enum ('A+','A-','B+','B-','AB+','AB-','O+','O-');

create type public.member_skill as enum ('cpr','first_aid','nurse','doctor');

create type public.community_response as enum ('coming','cannot');

create type public.sex as enum ('male','female','other','unknown');

create type public.agent_name as enum
  ('orchestrator','intake','verification','triage','dispatch','hospital_prep','debrief');

create type public.activity_kind as enum
  ('started','tool_call','tool_result','decision','guardrail_block','fallback','rule','error','finished');
