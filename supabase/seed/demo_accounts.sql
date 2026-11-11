update public.profiles p set role = 'dispatcher', display_name = 'Control Room'
from auth.users u where u.id = p.id and u.email = 'dispatcher@goldenminute.demo';

update public.profiles p set role = 'hospital_staff', display_name = 'ER In-charge',
  org_id = (select id from public.organizations where type='hospital' order by name limit 1)
from auth.users u where u.id = p.id and u.email = 'hospital@goldenminute.demo';

update public.profiles p set role = 'police', display_name = 'Duty Officer',
  org_id = (select id from public.organizations where type='police_station' order by name limit 1)
from auth.users u where u.id = p.id and u.email = 'police@goldenminute.demo';

update public.profiles p set role = 'rescue', display_name = 'Rescue Control',
  org_id = (select id from public.organizations where type='rescue_station' order by name limit 1)
from auth.users u where u.id = p.id and u.email = 'rescue@goldenminute.demo';

update public.profiles p set role = 'fire', display_name = 'Fire Control',
  org_id = (select id from public.organizations where type='fire_station' order by name limit 1)
from auth.users u where u.id = p.id and u.email = 'fire@goldenminute.demo';
