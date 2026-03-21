import './FeatureTooltip.css'

interface Props {
  lat: number
  lon: number
  features: Record<string, any>
  onClose: () => void
}

const FIELD_TYPE_LABELS: Record<number, string> = {
  1: '深海CZ型',
  2: '浅海波导型',
  3: '极地声道型',
  4: '混合型',
}

function fmt(val: any, decimals: number = 1, suffix: string = ''): string {
  if (val == null || (typeof val === 'number' && isNaN(val))) return '—'
  return Number(val).toFixed(decimals) + suffix
}

export function FeatureTooltip({ lat, lon, features, onClose }: Props) {
  const f = features || {}

  return (
    <div className="feature-tooltip">
      <div className="tooltip-header">
        <span className="tooltip-coord">
          {fmt(lat, 2)}°{lat >= 0 ? 'N' : 'S'}, {fmt(Math.abs(lon), 2)}°{lon >= 0 ? 'E' : 'W'}
        </span>
        <button className="tooltip-close" onClick={onClose}>×</button>
      </div>
      <div className="tooltip-grid">
        <div className="tooltip-item">
          <span className="tooltip-label">声道轴深度</span>
          <span className="tooltip-value">{fmt(f.channel_axis_depth, 0, ' m')}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">声道轴声速</span>
          <span className="tooltip-value">{fmt(f.channel_axis_speed, 1, ' m/s')}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">表面声道</span>
          <span className="tooltip-value">{f.surface_duct_thickness > 0 ? fmt(f.surface_duct_thickness, 0, ' m') : '无'}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">跃层梯度</span>
          <span className="tooltip-value">{fmt(f.thermocline_gradient, 3, ' /s')}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">会聚区距离</span>
          <span className="tooltip-value">{fmt(f.cz_distance_km, 1, ' km')}</span>
        </div>
        <div className="tooltip-item">
          <span className="tooltip-label">声影区距离</span>
          <span className="tooltip-value">{fmt(f.shadow_zone_km, 1, ' km')}</span>
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
