import './FeatureTooltip.css'

interface Props {
  lat: number
  lon: number
  features: {
    channel_axis_depth: number
    channel_axis_speed: number
    surface_duct_thickness: number
    thermocline_gradient: number
    cz_distance_km: number
    shadow_zone_km: number
    field_type: number
  }
  onClose: () => void
}

const FIELD_TYPE_LABELS: Record<number, string> = {
  1: '深海CZ型',
  2: '浅海波导型',
  3: '极地声道型',
  4: '混合型',
}

export function FeatureTooltip({ lat, lon, features, onClose }: Props) {
  const f = features

  return (
    <div className="feature-tooltip">
      <div className="tooltip-header">
        <span className="tooltip-coord">
          {lat.toFixed(2)}°{lat >= 0 ? 'N' : 'S'}, {Math.abs(lon).toFixed(2)}°{lon >= 0 ? 'E' : 'W'}
        </span>
        <button className="tooltip-close" onClick={onClose}>×</button>
      </div>
      <div className="tooltip-grid">
        <div className="tooltip-item">
          <span className="tooltip-label">声道轴深度</span>
          <span className="tooltip-value">{isNaN(f.channel_axis_depth) ? '—' : `${f.channel_axis_depth.toFixed(0)} m`}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">声道轴声速</span>
          <span className="tooltip-value">{isNaN(f.channel_axis_speed) ? '—' : `${f.channel_axis_speed.toFixed(1)} m/s`}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">表面声道</span>
          <span className="tooltip-value">{f.surface_duct_thickness > 0 ? `${f.surface_duct_thickness.toFixed(0)} m` : '无'}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">跃层梯度</span>
          <span className="tooltip-value">{f.thermocline_gradient > 0 ? `${f.thermocline_gradient.toFixed(3)} /s` : '—'}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">会聚区距离</span>
          <span className="tooltip-value">{isNaN(f.cz_distance_km) ? '—' : `${f.cz_distance_km.toFixed(1)} km`}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">声影区距离</span>
          <span className="tooltip-value">{isNaN(f.shadow_zone_km) ? '—' : `${f.shadow_zone_km.toFixed(1)} km`}</span>
        </div>
        <div className="tooltip-item full">
          <span className="tooltip-label">声场类型</span>
          <span className="tooltip-value type-badge">
            {FIELD_TYPE_LABELS[f.field_type] || '未知'}
          </span>
        </div>
      </div>
    </div>
  )
}
