import { useEffect, useMemo, useRef } from 'react'
import * as echarts from 'echarts'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { buildChartPlan, describeChart } from '../utils/chartPlan'
import type { ChartPlan, ResultRow } from '../utils/chartPlan'

// Vite serves Leaflet's default marker assets through its own bundler paths, which breaks the
// library's built-in icon URL resolution. Point it at the bundled asset URLs once, up front.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

// Tuned for white: same hues as the dark palette, lowered in lightness so every
// series stays distinguishable and readable against the panel.
const CHART_PALETTE = ['#0f8f6d', '#2563eb', '#b45309', '#be185d', '#6d28d9', '#0e7490', '#b91c1c', '#a16207']

const AXIS_TEXT = '#475569'
const AXIS_LINE = '#d3dbe6'
const SPLIT_LINE = '#eef2f7'
const PANEL_BG = '#ffffff'

const baseOption = (plan: ChartPlan) => ({
  color: CHART_PALETTE,
  textStyle: { color: AXIS_TEXT },
  tooltip: {
    backgroundColor: PANEL_BG,
    borderColor: AXIS_LINE,
    textStyle: { color: '#0f172a' },
    trigger: plan.kind === 'donut' ? ('item' as const) : ('axis' as const),
  },
})

const cartesianOption = (plan: ChartPlan) => ({
  ...baseOption(plan),
  grid: { left: 12, right: 18, top: 24, bottom: 8, containLabel: true },
  xAxis: {
    type: 'category' as const,
    data: plan.points.map((point) => point.name),
    axisLine: { lineStyle: { color: AXIS_LINE } },
    axisLabel: { color: AXIS_TEXT, fontSize: 11, hideOverlap: true },
  },
  yAxis: {
    type: 'value' as const,
    axisLabel: { color: AXIS_TEXT, fontSize: 11 },
    splitLine: { lineStyle: { color: SPLIT_LINE } },
  },
  series: [
    {
      type: plan.kind === 'line' ? ('line' as const) : ('bar' as const),
      data: plan.points.map((point) => point.value),
      smooth: plan.kind === 'line',
      showSymbol: plan.points.length <= 24,
      lineStyle: { width: 2.4, color: CHART_PALETTE[0] },
      itemStyle: { color: CHART_PALETTE[0], borderRadius: plan.kind === 'bar' ? [6, 6, 0, 0] : 0 },
      areaStyle:
        plan.kind === 'line'
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(15, 143, 109, 0.20)' },
                { offset: 1, color: 'rgba(15, 143, 109, 0)' },
              ]),
            }
          : undefined,
      barMaxWidth: 34,
    },
  ],
})

const donutOption = (plan: ChartPlan) => ({
  ...baseOption(plan),
  legend: {
    orient: 'vertical' as const,
    right: 8,
    top: 'center' as const,
    textStyle: { color: AXIS_TEXT, fontSize: 11 },
  },
  series: [
    {
      type: 'pie' as const,
      radius: ['46%', '72%'],
      center: ['38%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: PANEL_BG, borderWidth: 2 },
      label: { show: false },
      data: plan.points.map((point, index) => ({
        ...point,
        itemStyle: { color: CHART_PALETTE[index % CHART_PALETTE.length] },
      })),
    },
  ],
})

export function ResultChart({ rows }: { rows: ResultRow[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const plan = useMemo(() => buildChartPlan(rows), [rows])

  useEffect(() => {
    if (!containerRef.current || !plan) {
      return
    }

    const chart = echarts.init(containerRef.current)
    chart.setOption(plan.kind === 'donut' ? donutOption(plan) : cartesianOption(plan))

    // The card can resize without the window doing so (expanding rows, sidebar changes).
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.dispose()
    }
  }, [plan])

  if (!plan) {
    return <p className="chat-visual-empty">Not enough variation in this result set to chart.</p>
  }

  return <div ref={containerRef} className="chat-visual chat-chart" role="img" aria-label={describeChart(rows)} />
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
