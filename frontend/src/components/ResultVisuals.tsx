import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Vite serves Leaflet's default marker assets through its own bundler paths, which breaks the
// library's built-in icon URL resolution. Point it at the bundled asset URLs once, up front.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const CHART_PALETTE = ['#34d399', '#3b82f6', '#f59e0b', '#f472b6', '#a78bfa', '#22d3ee', '#fb7185', '#facc15']

type ResultRow = Record<string, unknown>

function pickCategoryAndValueKeys(row: ResultRow): { categoryKey: string | null; valueKey: string | null } {
  const keys = Object.keys(row)
  const categoryKey = keys.find((key) => typeof row[key] === 'string') ?? keys[0] ?? null
  const valueKey = keys.find((key) => typeof row[key] === 'number' && key !== categoryKey) ?? null
  return { categoryKey, valueKey }
}

export function ResultChart({ rows }: { rows: ResultRow[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current || rows.length === 0) {
      return
    }

    const { categoryKey, valueKey } = pickCategoryAndValueKeys(rows[0])
    if (!categoryKey) {
      return
    }

    const sample = rows.slice(0, 8)
    const chartData = sample.map((row, index) => ({
      name: String(row[categoryKey] ?? `Item ${index + 1}`),
      value: valueKey ? Number(row[valueKey]) || 0 : 1,
      itemStyle: { color: CHART_PALETTE[index % CHART_PALETTE.length] },
    }))

    const chart = echarts.init(containerRef.current)
    chart.setOption({
      color: CHART_PALETTE,
      tooltip: { trigger: 'item' },
      legend: {
        orient: 'vertical',
        right: 8,
        top: 'center',
        textStyle: { color: '#334155', fontSize: 11 },
      },
      series: [
        {
          name: valueKey ? valueKey.replaceAll('_', ' ') : 'Records',
          type: 'pie',
          radius: ['42%', '70%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: chartData,
        },
      ],
    })

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [rows])

  if (rows.length === 0) {
    return null
  }

  return <div ref={containerRef} className="chat-visual chat-chart" role="img" aria-label="Result data chart" />
}

export function ResultMap({ rows }: { rows: ResultRow[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    const points = rows
      .map((row) => {
        const lat = Number(row.latitude)
        const lng = Number(row.longitude)
        const label = String(row.destination ?? row.region ?? row.depot ?? row.route ?? row.customer ?? 'Location')
        return { lat, lng, label }
      })
      .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng))

    if (points.length === 0) {
      return
    }

    const map = L.map(containerRef.current, { scrollWheelZoom: false }).setView([points[0].lat, points[0].lng], 6)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map)

    points.forEach((point) => {
      L.marker([point.lat, point.lng]).addTo(map).bindPopup(point.label)
    })

    if (points.length > 1) {
      const bounds = L.latLngBounds(points.map((point) => [point.lat, point.lng]))
      map.fitBounds(bounds, { padding: [24, 24] })
    }

    return () => {
      map.remove()
    }
  }, [rows])

  const hasCoordinates = rows.some((row) => Number.isFinite(Number(row.latitude)) && Number.isFinite(Number(row.longitude)))
  if (!hasCoordinates) {
    return <p className="chat-visual-empty">No location data available for this result set.</p>
  }

  return <div ref={containerRef} className="chat-visual chat-map" aria-label="Result location map" />
}
