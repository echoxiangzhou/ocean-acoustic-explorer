import { useState, useCallback } from 'react'
import { CesiumGlobe, LAYER_CONFIG } from '../../components/globe/CesiumGlobe'
import { LayerControls } from '../../components/controls/LayerControls'
import { FeatureTooltip } from '../../components/common/FeatureTooltip'
import { ColorBar } from '../../components/common/ColorBar'
import { MonthSlider } from '../../components/controls/MonthSlider'
import { useLayerStore } from '../../stores/layerStore'
import './GlobalOverview.css'

export function GlobalOverview() {
  const { month, activeLayer } = useLayerStore()
  const [tooltip, setTooltip] = useState<{
    lat: number; lon: number; features: any
  } | null>(null)
  const [loading, setLoading] = useState(false)

  const layerCfg = LAYER_CONFIG[activeLayer]

  const handleClick = useCallback(async (lat: number, lon: number) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        lat: lat.toFixed(2),
        lon: lon.toFixed(2),
        month: month.toString(),
        src_depth: '50',
      })
      const res = await fetch(`/api/features?${params}`)
      if (res.ok) {
        const data = await res.json()
        setTooltip({ lat: data.lat, lon: data.lon, features: data.features })
      }
    } catch (e) {
      console.error('Failed to fetch features:', e)
    } finally {
      setLoading(false)
    }
  }, [month])

  return (
    <div className="module-layout">
      <LayerControls />
      <div className="globe-container">
        <CesiumGlobe onClick={handleClick} />
        {loading && <div className="loading-badge">Loading...</div>}
        {tooltip && (
          <FeatureTooltip
            lat={tooltip.lat}
            lon={tooltip.lon}
            features={tooltip.features}
            onClose={() => setTooltip(null)}
          />
        )}
        {layerCfg && (
          <ColorBar
            label={layerCfg.label}
            unit={layerCfg.unit}
            vmin={layerCfg.vmin}
            vmax={layerCfg.vmax}
            colormap={layerCfg.colormap}
          />
        )}
        <MonthSlider />
      </div>
    </div>
  )
}
