import { useState, useCallback } from 'react'
import { CesiumGlobe } from '../../components/globe/CesiumGlobe'
import Plot from 'react-plotly.js'
import './TrendAnalysis.css'

interface TrendData {
  lat: number
  lon: number
  months: number[]
  channel_axis_depth: number[]
  surface_duct_thickness: number[]
  delta_c: number[]
  surface_speed: number[]
}

const MONTH_LABELS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

export function TrendAnalysis() {
  const [data, setData] = useState<TrendData | null>(null)
  const [loading, setLoading] = useState(false)

  const handleClick = useCallback(async (lat: number, lon: number) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        lat: lat.toFixed(2),
        lon: lon.toFixed(2),
      })
      const res = await fetch(`/api/trends?${params}`)
      if (res.ok) {
        setData(await res.json())
      }
    } catch (e) {
      console.error('Trends fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="trend-layout">
      <div className="trend-map">
        <CesiumGlobe onClick={handleClick} />
        {loading && <div className="loading-badge">加载中...</div>}
      </div>
      <div className="trend-panel">
        {!data ? (
          <div className="trend-hint">点击地图选择位置，查看声场特征季节变化</div>
        ) : (
          <>
            <div className="trend-header">
              {data.lat.toFixed(2)}°{data.lat >= 0 ? 'N' : 'S'},{' '}
              {Math.abs(data.lon).toFixed(2)}°{data.lon >= 0 ? 'E' : 'W'}
              <span className="trend-subtitle">WOA23 月平均气候态</span>
            </div>
            <div className="trend-charts">
              <Plot
                data={[{
                  x: MONTH_LABELS,
                  y: data.surface_speed,
                  type: 'scatter',
                  mode: 'lines+markers',
                  line: { color: '#00d4ff', width: 2 },
                  marker: { size: 6 },
                }]}
                layout={chartLayout('表层声速 (m/s)')}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '180px' }}
              />
              <Plot
                data={[{
                  x: MONTH_LABELS,
                  y: data.channel_axis_depth,
                  type: 'scatter',
                  mode: 'lines+markers',
                  line: { color: '#ff6b35', width: 2 },
                  marker: { size: 6 },
                }]}
                layout={chartLayout('声道轴深度 (m)')}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '180px' }}
              />
              <Plot
                data={[{
                  x: MONTH_LABELS,
                  y: data.delta_c,
                  type: 'scatter',
                  mode: 'lines+markers',
                  line: { color: '#44ff88', width: 2 },
                  marker: { size: 6 },
                }]}
                layout={chartLayout('Δc 表层-声道轴 (m/s)')}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '180px' }}
              />
              <Plot
                data={[{
                  x: MONTH_LABELS,
                  y: data.surface_duct_thickness,
                  type: 'bar',
                  marker: { color: '#ff44aa' },
                }]}
                layout={chartLayout('表面声道厚度 (m)')}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '180px' }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function chartLayout(title: string): any {
  return {
    autosize: true,
    margin: { l: 50, r: 10, t: 30, b: 30 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
    font: { color: '#8899aa', size: 10 },
    title: { text: title, font: { size: 12, color: '#8899aa' }, x: 0.02 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { gridcolor: 'rgba(255,255,255,0.06)' },
  }
}
