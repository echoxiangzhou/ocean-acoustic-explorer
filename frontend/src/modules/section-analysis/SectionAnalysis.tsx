import { useState } from 'react'
import { CesiumGlobe } from '../../components/globe/CesiumGlobe'
import Plot from 'react-plotly.js'
import { useLayerStore } from '../../stores/layerStore'
import './SectionAnalysis.css'

const PRESET_SECTIONS = [
  { name: '南海 18°N', start: [18, 108], end: [18, 122] },
  { name: '吕宋海峡', start: [18, 119], end: [22, 122] },
  { name: '西太 130°E', start: [0, 130], end: [40, 130] },
  { name: '台湾海峡', start: [23, 117], end: [26, 121] },
  { name: '黄海断面', start: [34, 120], end: [38, 124] },
]

interface SectionResult {
  range_km: number[]
  depth: number[]
  sound_speed: number[][]
  bathymetry: number[]
  section_length_km: number
}

export function SectionAnalysis() {
  const { month } = useLayerStore()
  const [points, setPoints] = useState<[number, number][]>([])
  const [result, setResult] = useState<SectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'sound_speed' | 'tl'>('sound_speed')

  const handleMapClick = (lat: number, lon: number) => {
    if (points.length < 2) {
      setPoints((prev) => [...prev, [lat, lon]])
    }
  }

  const handlePreset = (section: typeof PRESET_SECTIONS[0]) => {
    setPoints([section.start as [number, number], section.end as [number, number]])
  }

  const handleCompute = async () => {
    if (points.length < 2) return
    setLoading(true)
    try {
      const params = new URLSearchParams({
        start_lat: points[0][0].toFixed(2),
        start_lon: points[0][1].toFixed(2),
        end_lat: points[1][0].toFixed(2),
        end_lon: points[1][1].toFixed(2),
        month: month.toString(),
        num_points: '200',
      })
      const res = await fetch(`/api/acoustic/section?${params}`)
      if (res.ok) {
        setResult(await res.json())
      }
    } catch (e) {
      console.error('Section compute failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setPoints([])
    setResult(null)
  }

  return (
    <div className="section-layout">
      <div className="section-sidebar">
        <div className="control-section">
          <h3 className="control-title">预置断面</h3>
          <div className="preset-list">
            {PRESET_SECTIONS.map((s) => (
              <button key={s.name} className="preset-btn" onClick={() => handlePreset(s)}>
                {s.name}
              </button>
            ))}
          </div>
        </div>

        <div className="control-section">
          <h3 className="control-title">自定义断面</h3>
          <p className="hint">在地图上点击两个端点</p>
          {points.map((p, i) => (
            <div key={i} className="point-display">
              端点{i + 1}: {p[0].toFixed(2)}°, {p[1].toFixed(2)}°
            </div>
          ))}
        </div>

        <div className="section-actions">
          <button
            className="compute-btn"
            onClick={handleCompute}
            disabled={points.length < 2 || loading}
          >
            {loading ? '计算中...' : '计算断面声速场'}
          </button>
          <button className="clear-btn" onClick={handleClear}>清除</button>
        </div>

        {result && (
          <div className="control-section">
            <h3 className="control-title">断面信息</h3>
            <div className="point-display">长度: {result.section_length_km.toFixed(1)} km</div>
            <div className="point-display">深度范围: 0-{Math.max(...result.bathymetry).toFixed(0)} m</div>
          </div>
        )}
      </div>

      <div className="section-main">
        {!result ? (
          <div className="section-map">
            <CesiumGlobe onClick={handleMapClick} />
          </div>
        ) : (
          <div className="section-results">
            <div className="result-tabs">
              <button
                className={`tab ${activeTab === 'sound_speed' ? 'active' : ''}`}
                onClick={() => setActiveTab('sound_speed')}
              >
                断面声速场
              </button>
              <button
                className={`tab ${activeTab === 'tl' ? 'active' : ''}`}
                onClick={() => setActiveTab('tl')}
              >
                传播损失 (TL)
              </button>
            </div>

            <div className="result-content">
              {activeTab === 'sound_speed' && (
                <Plot
                  data={[
                    {
                      z: result.sound_speed,
                      x: result.range_km,
                      y: result.depth,
                      type: 'heatmap',
                      colorscale: 'RdYlBu',
                      reversescale: true,
                      colorbar: {
                        title: { text: 'c (m/s)', font: { color: '#8899aa' } },
                        tickfont: { color: '#8899aa' },
                      },
                    },
                    {
                      x: result.range_km,
                      y: result.bathymetry,
                      type: 'scatter',
                      mode: 'lines',
                      fill: 'tomaxy',
                      fillcolor: 'rgba(60, 60, 60, 0.7)',
                      line: { color: '#666', width: 2 },
                      showlegend: false,
                    },
                  ]}
                  layout={{
                    autosize: true,
                    margin: { l: 65, r: 20, t: 30, b: 50 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
                    font: { color: '#8899aa', size: 11 },
                    xaxis: {
                      title: '距离 (km)',
                      gridcolor: 'rgba(255,255,255,0.06)',
                    },
                    yaxis: {
                      title: '深度 (m)',
                      autorange: 'reversed',
                      gridcolor: 'rgba(255,255,255,0.06)',
                    },
                    title: {
                      text: `断面声速场 (${month}月)`,
                      font: { color: '#8899aa', size: 14 },
                    },
                  }}
                  config={{ responsive: true }}
                  style={{ width: '100%', height: '100%' }}
                />
              )}

              {activeTab === 'tl' && (
                <div className="tl-placeholder">
                  传播损失计算需要 Bellhop/RAM 声学模型引擎（开发中）
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
