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

interface TLResult {
  tl: number[][]
  rays: { range_km: number[]; depth: number[] }[]
  range_km: number[]
  depth: number[]
  sound_speed: number[][]
  bathymetry: number[]
  section_length_km: number
  model: string
  src_depth: number
  frequency: number
}

export function SectionAnalysis() {
  const { month } = useLayerStore()
  const [points, setPoints] = useState<[number, number][]>([])
  const [sectionResult, setSectionResult] = useState<SectionResult | null>(null)
  const [tlResult, setTlResult] = useState<TLResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'sound_speed' | 'tl' | 'rays'>('sound_speed')
  const [model, setModel] = useState('ray')
  const [srcDepth, setSrcDepth] = useState(50)
  const [freq, setFreq] = useState(1000)

  const handleMapClick = (lat: number, lon: number) => {
    if (points.length < 2) {
      setPoints((prev) => [...prev, [lat, lon]])
    }
  }

  const handlePreset = (section: typeof PRESET_SECTIONS[0]) => {
    setPoints([section.start as [number, number], section.end as [number, number]])
    setSectionResult(null)
    setTlResult(null)
  }

  const handleComputeSection = async () => {
    if (points.length < 2) return
    setLoading(true)
    try {
      const params = new URLSearchParams({
        start_lat: points[0][0].toFixed(2),
        start_lon: points[0][1].toFixed(2),
        end_lat: points[1][0].toFixed(2),
        end_lon: points[1][1].toFixed(2),
        month: month.toString(),
        num_points: '100',
      })
      const res = await fetch(`/api/acoustic/section?${params}`)
      if (res.ok) {
        setSectionResult(await res.json())
        setActiveTab('sound_speed')
      }
    } catch (e) {
      console.error('Section compute failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleComputeTL = async () => {
    if (points.length < 2) return
    setLoading(true)
    try {
      const res = await fetch('/api/acoustic/compute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_lat: points[0][0],
          start_lon: points[0][1],
          end_lat: points[1][0],
          end_lon: points[1][1],
          src_depth: srcDepth,
          frequency: freq,
          model: model,
          month: month,
          num_points: 100,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setTlResult(data)
        setSectionResult({
          range_km: data.range_km,
          depth: data.depth,
          sound_speed: data.sound_speed,
          bathymetry: data.bathymetry,
          section_length_km: data.section_length_km,
        })
        setActiveTab('tl')
      } else {
        const err = await res.json()
        console.error('TL compute failed:', err.detail)
      }
    } catch (e) {
      console.error('TL compute failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setPoints([])
    setSectionResult(null)
    setTlResult(null)
  }

  const result = sectionResult || (tlResult ? {
    range_km: tlResult.range_km,
    depth: tlResult.depth,
    sound_speed: tlResult.sound_speed,
    bathymetry: tlResult.bathymetry,
    section_length_km: tlResult.section_length_km,
  } : null)

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
          <h3 className="control-title">断面端点</h3>
          <p className="hint">在地图上点击两个端点，或选择预置断面</p>
          {points.map((p, i) => (
            <div key={i} className="point-display">
              端点{i + 1}: {p[0].toFixed(2)}°, {p[1].toFixed(2)}°
            </div>
          ))}
        </div>

        <div className="control-section">
          <h3 className="control-title">声学参数</h3>
          <div className="param-group">
            <label>声源深度</label>
            <div className="param-row">
              <input type="range" min={0} max={500} step={10} value={srcDepth}
                onChange={(e) => setSrcDepth(+e.target.value)} />
              <span className="param-val">{srcDepth}m</span>
            </div>
          </div>
          <div className="param-group">
            <label>频率</label>
            <select value={freq} onChange={(e) => setFreq(+e.target.value)}>
              {[50, 100, 500, 1000, 5000].map(f => (
                <option key={f} value={f}>{f >= 1000 ? `${f/1000}k` : f} Hz</option>
              ))}
            </select>
          </div>
          <div className="param-group">
            <label>计算模型</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="ray">射线追踪 (快速)</option>
              <option value="pe">抛物方程 PE (精确)</option>
            </select>
          </div>
        </div>

        <div className="section-actions">
          <button className="compute-btn"
            onClick={handleComputeSection}
            disabled={points.length < 2 || loading}>
            声速场
          </button>
          <button className="compute-btn highlight"
            onClick={handleComputeTL}
            disabled={points.length < 2 || loading}>
            {loading ? '计算中...' : '传播损失 TL'}
          </button>
          <button className="clear-btn" onClick={handleClear}>清除</button>
        </div>

        {result && (
          <div className="control-section">
            <div className="point-display">断面长度: {result.section_length_km.toFixed(1)} km</div>
            <div className="point-display">最大深度: {Math.max(...result.bathymetry).toFixed(0)} m</div>
            {tlResult && <div className="point-display">模型: {tlResult.model === 'ray' ? '射线追踪' : '抛物方程'}</div>}
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
              <button className={`tab ${activeTab === 'sound_speed' ? 'active' : ''}`}
                onClick={() => setActiveTab('sound_speed')}>
                声速场
              </button>
              <button className={`tab ${activeTab === 'tl' ? 'active' : ''}`}
                onClick={() => setActiveTab('tl')}
                disabled={!tlResult}>
                传播损失
              </button>
              {tlResult?.rays && tlResult.rays.length > 0 && (
                <button className={`tab ${activeTab === 'rays' ? 'active' : ''}`}
                  onClick={() => setActiveTab('rays')}>
                  声线图
                </button>
              )}
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
                      colorbar: { title: { text: 'c (m/s)', font: { color: '#8899aa' } }, tickfont: { color: '#8899aa' } },
                    },
                    {
                      x: result.range_km, y: result.bathymetry,
                      type: 'scatter', mode: 'lines',
                      fill: 'tomaxy', fillcolor: 'rgba(60,60,60,0.7)',
                      line: { color: '#666', width: 2 }, showlegend: false,
                    },
                  ]}
                  layout={plotLayout('断面声速场 (%d月)'.replace('%d', month.toString()))}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              )}

              {activeTab === 'tl' && tlResult && (
                <Plot
                  data={[
                    {
                      z: tlResult.tl,
                      x: tlResult.range_km,
                      y: tlResult.depth,
                      type: 'heatmap',
                      colorscale: 'Jet',
                      reversescale: true,
                      zmin: 40, zmax: 120,
                      colorbar: { title: { text: 'TL (dB)', font: { color: '#8899aa' } }, tickfont: { color: '#8899aa' } },
                    },
                    {
                      x: tlResult.range_km, y: tlResult.bathymetry,
                      type: 'scatter', mode: 'lines',
                      fill: 'tomaxy', fillcolor: 'rgba(60,60,60,0.7)',
                      line: { color: '#666', width: 2 }, showlegend: false,
                    },
                    // Source marker
                    {
                      x: [0], y: [tlResult.src_depth],
                      type: 'scatter', mode: 'markers',
                      marker: { size: 10, color: '#ff0000', symbol: 'star' },
                      name: '声源',
                    },
                  ]}
                  layout={plotLayout('传播损失 TL (%s, %dHz, 源深%dm)'
                    .replace('%s', tlResult.model === 'ray' ? '射线' : 'PE')
                    .replace('%d', tlResult.frequency.toString())
                    .replace('%d', tlResult.src_depth.toString())
                  )}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              )}

              {activeTab === 'rays' && tlResult?.rays && (
                <Plot
                  data={[
                    ...tlResult.rays.map((ray, i) => ({
                      x: ray.range_km,
                      y: ray.depth,
                      type: 'scatter' as const,
                      mode: 'lines' as const,
                      line: { width: 0.8, color: `hsl(${i * 18}, 80%, 60%)` },
                      showlegend: false,
                    })),
                    {
                      x: tlResult.range_km, y: tlResult.bathymetry,
                      type: 'scatter', mode: 'lines',
                      fill: 'tomaxy', fillcolor: 'rgba(60,60,60,0.7)',
                      line: { color: '#666', width: 2 }, showlegend: false,
                    },
                    {
                      x: [0], y: [tlResult.src_depth],
                      type: 'scatter', mode: 'markers',
                      marker: { size: 10, color: '#ff0000', symbol: 'star' },
                      name: '声源',
                    },
                  ]}
                  layout={plotLayout('声线追踪 (源深 %dm, %dHz)'
                    .replace('%d', tlResult.src_depth.toString())
                    .replace('%d', tlResult.frequency.toString())
                  )}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function plotLayout(title: string): any {
  return {
    autosize: true,
    margin: { l: 65, r: 20, t: 40, b: 50 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
    font: { color: '#8899aa', size: 11 },
    xaxis: { title: '距离 (km)', gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { title: '深度 (m)', autorange: 'reversed', gridcolor: 'rgba(255,255,255,0.06)' },
    title: { text: title, font: { size: 14, color: '#8899aa' } },
    showlegend: false,
  }
}
