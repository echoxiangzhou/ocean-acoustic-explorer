import { useLayerStore } from '../../stores/layerStore'
import './LayerControls.css'

const LAYERS = [
  { id: 'channel_axis', label: '声道轴深度' },
  { id: 'surface_duct', label: '表面声道厚度' },
  { id: 'thermocline_grad', label: '跃层梯度' },
  { id: 'convergence_zone', label: '会聚区距离' },
  { id: 'shadow_zone', label: '声影区距离' },
  { id: 'field_type', label: '声场类型' },
]

const FREQUENCIES = [50, 100, 500, 1000, 5000]

export function LayerControls() {
  const { activeLayer, setActiveLayer, month, setMonth, srcDepth, setSrcDepth, frequency, setFrequency } =
    useLayerStore()

  return (
    <div className="layer-controls">
      <div className="control-section">
        <h3 className="control-title">图层选择</h3>
        <div className="layer-buttons">
          {LAYERS.map((l) => (
            <button
              key={l.id}
              className={`layer-btn ${activeLayer === l.id ? 'active' : ''}`}
              onClick={() => setActiveLayer(l.id)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      <div className="control-section">
        <h3 className="control-title">
          月份 <span className="control-value">{month}月</span>
        </h3>
        <input
          type="range"
          min={1}
          max={12}
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="slider"
        />
        <div className="slider-labels">
          <span>1月</span>
          <span>6月</span>
          <span>12月</span>
        </div>
      </div>

      <div className="control-section">
        <h3 className="control-title">
          声源深度 <span className="control-value">{srcDepth}m</span>
        </h3>
        <input
          type="range"
          min={0}
          max={500}
          step={10}
          value={srcDepth}
          onChange={(e) => setSrcDepth(Number(e.target.value))}
          className="slider"
        />
        <div className="slider-labels">
          <span>0m</span>
          <span>250m</span>
          <span>500m</span>
        </div>
      </div>

      <div className="control-section">
        <h3 className="control-title">频率</h3>
        <div className="freq-buttons">
          {FREQUENCIES.map((f) => (
            <button
              key={f}
              className={`freq-btn ${frequency === f ? 'active' : ''}`}
              onClick={() => setFrequency(f)}
            >
              {f >= 1000 ? `${f / 1000}k` : f} Hz
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
