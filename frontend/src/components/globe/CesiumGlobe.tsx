import { useRef, useCallback } from 'react'
import { Viewer as ResiumViewer, ImageryLayer, CameraFlyTo } from 'resium'
import {
  Ion,
  WebMapServiceImageryProvider,
  Cartesian3,
  Color,
  SceneMode,
  Cartographic,
  Math as CesiumMath,
  Viewer,
  ScreenSpaceEventType,
  defined,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useLayerStore } from '../../stores/layerStore'

Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_TOKEN || ''

const WMS_BASE = '/wms'

const LAYER_CONFIG: Record<string, { vmin: number; vmax: number; colormap: string; unit: string; label: string }> = {
  channel_axis_depth: { vmin: 0, vmax: 1500, colormap: 'viridis', unit: 'm', label: '声道轴深度' },
  surface_duct: { vmin: 0, vmax: 300, colormap: 'plasma', unit: 'm', label: '表面声道厚度' },
  thermocline_gradient: { vmin: 0, vmax: 0.5, colormap: 'inferno', unit: '1/s', label: '跃层梯度' },
  convergence_zone_km: { vmin: 30, vmax: 70, colormap: 'turbo', unit: 'km', label: '会聚区距离' },
  shadow_zone_km: { vmin: 0, vmax: 50, colormap: 'magma', unit: 'km', label: '声影区距离' },
  field_type: { vmin: 0, vmax: 4, colormap: 'Set1', unit: '', label: '声场类型' },
}

interface CesiumGlobeProps {
  onClick?: (lat: number, lon: number) => void
  sceneMode?: SceneMode
}

export function CesiumGlobe({ onClick, sceneMode = SceneMode.SCENE3D }: CesiumGlobeProps) {
  const viewerRef = useRef<{ cesiumElement?: Viewer }>(null)
  const { activeLayer, month } = useLayerStore()

  const layerCfg = LAYER_CONFIG[activeLayer]

  // Build WMS provider for active feature layer
  const wmsProvider = layerCfg
    ? new WebMapServiceImageryProvider({
        url: WMS_BASE,
        layers: `features_month${String(month).padStart(2, '0')}_src50m/${activeLayer}`,
        parameters: {
          format: 'image/png',
          transparent: 'true',
          colormap: layerCfg.colormap,
          vmin: layerCfg.vmin,
          vmax: layerCfg.vmax,
        },
      })
    : undefined

  // Handle click -> get lat/lon from globe
  const handleClick = useCallback(() => {
    const viewer = viewerRef.current?.cesiumElement
    if (!viewer || !onClick) return

    const handler = viewer.screenSpaceEventHandler
    handler.setInputAction((movement: { position: { x: number; y: number } }) => {
      const cartesian = viewer.camera.pickEllipsoid(
        movement.position,
        viewer.scene.globe.ellipsoid
      )
      if (defined(cartesian)) {
        const carto = Cartographic.fromCartesian(cartesian!)
        const lat = CesiumMath.toDegrees(carto.latitude)
        const lon = CesiumMath.toDegrees(carto.longitude)
        onClick(lat, lon)
      }
    }, ScreenSpaceEventType.LEFT_CLICK)
  }, [onClick])

  return (
    <ResiumViewer
      ref={viewerRef as any}
      full
      sceneMode={sceneMode}
      baseColor={Color.fromCssColorString('#0a1628')}
      animation={false}
      timeline={false}
      homeButton={false}
      navigationHelpButton={false}
      sceneModePicker={false}
      baseLayerPicker={false}
      fullscreenButton={false}
      geocoder={false}
      infoBox={false}
      selectionIndicator={false}
      onUpdate={handleClick}
    >
      {wmsProvider && (
        <ImageryLayer imageryProvider={wmsProvider} alpha={0.7} />
      )}
      <CameraFlyTo
        destination={Cartesian3.fromDegrees(120, 15, 15000000)}
        duration={0}
      />
    </ResiumViewer>
  )
}

export { LAYER_CONFIG }
