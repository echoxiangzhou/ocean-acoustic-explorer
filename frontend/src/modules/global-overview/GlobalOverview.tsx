import { CesiumGlobe } from '../../components/globe/CesiumGlobe'
import { LayerControls } from '../../components/controls/LayerControls'
import './GlobalOverview.css'

export function GlobalOverview() {
  return (
    <div className="module-layout">
      <LayerControls />
      <div className="globe-container">
        <CesiumGlobe />
      </div>
    </div>
  )
}
