import { useState } from 'react'
import Plot from 'react-plotly.js'
import './ScenarioSim.css'

interface ScenarioResult {
  lat: number
  lon: number
  ocean_depth_m: number
  detection_range_km: number
  optimal_recv_depth_m: number
  cz_ranges_km: number[]
  channel_axis_depth_m: number
  surface_duct_m: number
  delta_c: number
  sediment: string
  recommendations: string[]
  profile: { depth: number[]; sound_speed: number[] }
}

const MONTH_LABELS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

export function ScenarioSim() {
  const [params, setParams] = useState({
    lat: 18.0, lon: 115.0,
    src_depth: 50, recv_depth: 100,
    frequency: 1000, month: 1,
  })
  const [result, setResult] = useState<ScenarioResult | null>(null)
  const [compareResult, setCompareResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleEvaluate = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/scenarios/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })
      if (res.ok) setResult(await res.json())
    } catch (e) {
      console.error('Scenario eval failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleCompare = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/scenarios/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: params.lat, lon: params.lon,
          src_depth: params.src_depth, frequency: params.frequency,
          month_a: 1, month_b: 7,
        }),
      })
      if (res.ok) setCompareResult(await res.json())
    } catch (e) {
      console.error('Compare failed:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="scenario-layout">
      <div className="scenario-sidebar">
        <h3 className="control-title">场景参数</h3>

        <div className="param-group">
          <label>位置</label>
          <div className="param-row">
            <input type="number" value={params.lat} step={0.5}
              onChange={(e) => setParams({...params, lat: +e.target.value})} />
            <span>°N</span>
            <input type="number" value={params.lon} step={0.5}
              onChange={(e) => setParams({...params, lon: +e.target.value})} />
            <span>°E</span>
          </div>
        </div>

        <div className="param-group">
          <label>声源深度 (m)</label>
          <input type="range" min={0} max={500} step={10} value={params.src_depth}
            onChange={(e) => setParams({...params, src_depth: +e.target.value})} />
          <span className="param-val">{params.src_depth}m</span>
        </div>

        <div className="param-group">
          <label>接收器深度 (m)</label>
          <input type="range" min={0} max={1000} step={10} value={params.recv_depth}
            onChange={(e) => setParams({...params, recv_depth: +e.target.value})} />
          <span className="param-val">{params.recv_depth}m</span>
        </div>

        <div className="param-group">
          <label>频率 (Hz)</label>
          <select value={params.frequency}
            onChange={(e) => setParams({...params, frequency: +e.target.value})}>
            {[50, 100, 500, 1000, 5000].map(f => (
              <option key={f} value={f}>{f >= 1000 ? `${f/1000}k` : f} Hz</option>
            ))}
          </select>
        </div>

        <div className="param-group">
          <label>月份</label>
          <select value={params.month}
            onChange={(e) => setParams({...params, month: +e.target.value})}>
            {MONTH_LABELS.map((m, i) => (
              <option key={i} value={i + 1}>{m}</option>
            ))}
          </select>
        </div>

        <div className="scenario-actions">
          <button className="eval-btn" onClick={handleEvaluate} disabled={loading}>
            {loading ? '计算中...' : '评估场景'}
          </button>
          <button className="compare-btn" onClick={handleCompare} disabled={loading}>
            冬/夏对比
          </button>
        </div>
      </div>

      <div className="scenario-main">
        {!result && !compareResult ? (
          <div className="scenario-hint">设置参数后点击"评估场景"</div>
        ) : result && !compareResult ? (
          <div className="result-panels">
            <div className="result-card">
              <h3>评估结果</h3>
              <div className="result-grid">
                <div className="result-item highlight">
                  <span className="r-label">探测距离</span>
                  <span className="r-value">{result.detection_range_km} km</span>
                </div>
                <div className="result-item highlight">
                  <span className="r-label">最优接收深度</span>
                  <span className="r-value">{result.optimal_recv_depth_m} m</span>
                </div>
                <div className="result-item">
                  <span className="r-label">海底深度</span>
                  <span className="r-value">{result.ocean_depth_m.toFixed(0)} m</span>
                </div>
                <div className="result-item">
                  <span className="r-label">声道轴</span>
                  <span className="r-value">{result.channel_axis_depth_m.toFixed(0)} m</span>
                </div>
                <div className="result-item">
                  <span className="r-label">表面声道</span>
                  <span className="r-value">{result.surface_duct_m > 0 ? `${result.surface_duct_m.toFixed(0)} m` : '无'}</span>
                </div>
                <div className="result-item">
                  <span className="r-label">底质</span>
                  <span className="r-value">{result.sediment}</span>
                </div>
                {result.cz_ranges_km.length > 0 && (
                  <div className="result-item full">
                    <span className="r-label">会聚区</span>
                    <span className="r-value">{result.cz_ranges_km.join(' / ')} km</span>
                  </div>
                )}
              </div>
              {result.recommendations.length > 0 && (
                <div className="recommendations">
                  <h4>建议</h4>
                  <ul>
                    {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
            </div>
            <div className="result-chart">
              <Plot
                data={[{
                  x: result.profile.sound_speed,
                  y: result.profile.depth,
                  type: 'scatter', mode: 'lines',
                  line: { color: '#00d4ff', width: 2 },
                }]}
                layout={{
                  autosize: true,
                  margin: { l: 55, r: 10, t: 30, b: 45 },
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'rgba(22,34,64,0.5)',
                  font: { color: '#8899aa', size: 10 },
                  title: { text: '声速剖面', font: { size: 12, color: '#8899aa' } },
                  xaxis: { title: 'm/s', gridcolor: 'rgba(255,255,255,0.06)' },
                  yaxis: { title: 'm', autorange: 'reversed', gridcolor: 'rgba(255,255,255,0.06)' },
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '400px' }}
              />
            </div>
          </div>
        ) : compareResult ? (
          <div className="compare-panels">
            <Plot
              data={[
                {
                  x: compareResult.scenario_a.sound_speed,
                  y: compareResult.scenario_a.depth,
                  type: 'scatter', mode: 'lines',
                  name: `${compareResult.scenario_a.month}月 (冬)`,
                  line: { color: '#00d4ff', width: 2 },
                },
                {
                  x: compareResult.scenario_b.sound_speed,
                  y: compareResult.scenario_b.depth,
                  type: 'scatter', mode: 'lines',
                  name: `${compareResult.scenario_b.month}月 (夏)`,
                  line: { color: '#ff6b35', width: 2 },
                },
              ]}
              layout={{
                autosize: true,
                margin: { l: 60, r: 20, t: 40, b: 50 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(22,34,64,0.5)',
                font: { color: '#8899aa', size: 11 },
                title: { text: '冬/夏声速剖面对比', font: { size: 14, color: '#8899aa' } },
                xaxis: { title: '声速 (m/s)', gridcolor: 'rgba(255,255,255,0.06)' },
                yaxis: { title: '深度 (m)', autorange: 'reversed', gridcolor: 'rgba(255,255,255,0.06)' },
                showlegend: true,
                legend: { x: 1, y: 1, xanchor: 'right', bgcolor: 'transparent' },
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%', height: '500px' }}
            />
            <button className="back-btn" onClick={() => setCompareResult(null)}>返回评估</button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
