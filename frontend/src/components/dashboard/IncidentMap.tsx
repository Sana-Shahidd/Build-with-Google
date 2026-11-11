import 'leaflet/dist/leaflet.css'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { SEVERITY_COLOR, SEVERITY_RADIUS } from '@/lib/severity'
import type { AssignmentRow, IncidentRow, OrgRow, TargetRow } from '@/lib/schemas'

const LAHORE: [number, number] = [31.5204, 74.3587]
const ORG_STYLE: Record<OrgRow['type'], { color: string; radius: number }> = {
  hospital: { color: '#FFFFFF', radius: 5 },
  police_station: { color: '#60A5FA', radius: 6 },
  rescue_station: { color: '#F472B6', radius: 6 },
  fire_station: { color: '#FB923C', radius: 6 },
}

const LABEL_ZOOM = 14 // hospital/station names appear when zoomed in far enough to read

function ZoomWatcher({ onZoom }: { onZoom: (z: number) => void }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) })
  return null
}

function Legend() {
  const { t } = useTranslation()
  const sev = [['critical', '#E11D2E'], ['high', '#F97316'], ['medium', '#EAB308'], ['low', '#22C55E']]
  const orgs = [['hospital', '#FFFFFF'], ['police', '#60A5FA'], ['rescue', '#F472B6'], ['fire', '#FB923C']]
  const dot = (c: string) => <span className="inline-block size-3 rounded-full border border-[#12324A]/60" style={{ background: c }} />
  return (
    <div className="pointer-events-none absolute bottom-2 start-2 z-[1000] space-y-1 rounded-xl bg-white/90 p-2 text-[11px] font-semibold text-[#12324A] shadow">
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {sev.map(([k, c]) => <span key={k} className="flex items-center gap-1">{dot(c)} {t(`severity.${k}`)}</span>)}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {orgs.map(([k, c]) => <span key={k} className="flex items-center gap-1">{dot(c)} {t(`dash.legend.${k}`)}</span>)}
      </div>
      <div className="flex items-center gap-1"><span className="inline-block size-3 rounded-full border-2 border-white bg-sos ring-1 ring-[#12324A]/60" /> {t('dash.legend.unacked')}</div>
    </div>
  )
}

function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo(target, Math.max(map.getZoom(), 14), { duration: 0.6 })
  }, [map, target])
  return null
}

/** Leaflet map: incidents (by severity), hospitals/stations, assigned hospitals, 500 m merge circle. */
export function IncidentMap({
  incidents,
  orgs,
  assignments,
  targets,
  selectedId,
  onSelect,
}: {
  incidents: IncidentRow[]
  orgs: OrgRow[]
  assignments: AssignmentRow[]
  targets: TargetRow[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const { t } = useTranslation()
  const [zoom, setZoom] = useState(12)
  const selected = incidents.find((i) => i.id === selectedId) ?? null
  const assignedHere = new Map(
    assignments.filter((a) => a.incident_id === selectedId).map((a) => [a.hospital_id, a]),
  )
  const flyTarget: [number, number] | null =
    selected?.lat != null && selected.lng != null ? [selected.lat, selected.lng] : null
  const unacked = new Set(targets.filter((x) => x.status !== 'acknowledged').map((x) => x.incident_id))

  return (
    <div className="relative size-full">
    <MapContainer center={LAHORE} zoom={12} className="size-full" scrollWheelZoom>
      <ZoomWatcher onZoom={setZoom} />
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FlyTo target={flyTarget} />

      {orgs.map((o) => {
        const assignment = assignedHere.get(o.id)
        const style = ORG_STYLE[o.type]
        return (
          <CircleMarker
            key={o.id}
            center={[o.lat, o.lng]}
            radius={assignment ? 9 : style.radius}
            pathOptions={{
              color: assignment ? "#2563EB" : "#12324A",
              weight: assignment ? 3 : 1,
              fillColor: style.color,
              fillOpacity: 0.95,
            }}
          >
            <Tooltip permanent={!!assignment || zoom >= LABEL_ZOOM} direction="top" offset={[0, -6]} className="gm-label">
              {o.name}
              {o.hospital_details && ` · ${t('dash.beds', { n: o.hospital_details.er_beds_available })}`}
              {assignment && ` · +${assignment.assigned_casualties} (${assignment.critical} ${t('dash.criticalCount')})`}
            </Tooltip>
          </CircleMarker>
        )
      })}

      {selected?.lat != null && selected.lng != null && (
        <Circle
          center={[selected.lat, selected.lng]}
          radius={500}
          pathOptions={{ color: '#E2E8F0', dashArray: '6 6', fillOpacity: 0.05, opacity: 0.3 }}
        />
      )}

      {incidents
        .filter((i) => i.lat != null && i.lng != null && i.status !== 'closed' && i.status !== 'dismissed')
        .map((i) => (
          <CircleMarker
            key={i.id}
            center={[i.lat as number, i.lng as number]}
            radius={SEVERITY_RADIUS[i.severity]}
            pathOptions={{
              color: unacked.has(i.id) ? '#FFFFFF' : SEVERITY_COLOR[i.severity],
              weight: unacked.has(i.id) ? 3 : 1,
              fillColor: SEVERITY_COLOR[i.severity],
              fillOpacity: 0.85,
            }}
            eventHandlers={{ click: () => onSelect(i.id) }}
          >
            <Tooltip permanent direction="top" offset={[0, -SEVERITY_RADIUS[i.severity]]} className="gm-label gm-label-incident">
              {i.short_code} · {t(`incidentType.${i.incident_type}`)}
            </Tooltip>
          </CircleMarker>
        ))}
    </MapContainer>
    <Legend />
    </div>
  )
}
