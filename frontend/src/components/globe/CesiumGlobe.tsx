import { useRef, useEffect } from 'react'
import {
  Viewer,
  WebMapServiceImageryProvider,
  UrlTemplateImageryProvider,
  Color,
  Cartographic,
  Math as CesiumMath,
  ScreenSpaceEventType,
  ScreenSpaceEventHandler,
  defined,
  ImageryLayer,
  Cartesian3,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useLayerStore } from '../../stores/layerStore'
import './CesiumGlobe.css'

const XPUBLISH_BASE = '/xpublish'

const LAYER_CONFIG: Record<string, { vmin: number; vmax: number; colormap: string; unit: string; label: string }> = {
  channel_axis_depth: { vmin: 0, vmax: 1500, colormap: 'viridis', unit: 'm', label: '声道轴深度' },
  surface_duct: { vmin: 0, vmax: 300, colormap: 'plasma', unit: 'm', label: '表面声道厚度' },
  thermocline_gradient: { vmin: 0, vmax: 0.5, colormap: 'inferno', unit: '1/s', label: '跃层梯度' },
  convergence_zone_km: { vmin: 20, vmax: 80, colormap: 'turbo', unit: 'km', label: '会聚区距离' },
  shadow_zone_km: { vmin: 0, vmax: 50, colormap: 'magma', unit: 'km', label: '声影区距离' },
  field_type: { vmin: 0, vmax: 4, colormap: 'tab10', unit: '', label: '声场类型' },
}

interface CesiumGlobeProps {
  onClick?: (lat: number, lon: number) => void
}

export function CesiumGlobe({ onClick }: CesiumGlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const wmsLayerRef = useRef<ImageryLayer | null>(null)
  const handlerRef = useRef<ScreenSpaceEventHandler | null>(null)
  const { activeLayer, month } = useLayerStore()

  // Initialize Cesium Viewer once
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return

    const viewer = new Viewer(containerRef.current, {
      animation: false,
      timeline: false,
      homeButton: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      infoBox: false,
      selectionIndicator: false,
      baseLayerPicker: false,
      imageryProvider: false as any,  // Disable default imagery
    })

    // Add satellite basemap as base layer
    const baseLayer = new UrlTemplateImageryProvider({
      url: 'http://10.16.202.44:8090/MapServer/tile/{z}/{x}/{y}.jpg',
      maximumLevel: 18,
    })
    viewer.imageryLayers.addImageryProvider(baseLayer)

    viewer.scene.globe.baseColor = Color.fromCssColorString('#0a1628')
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(120, 15, 15000000),
      duration: 0,
    })

    viewerRef.current = viewer

    return () => {
      if (handlerRef.current) {
        handlerRef.current.destroy()
        handlerRef.current = null
      }
      viewer.destroy()
      viewerRef.current = null
    }
  }, [])

  // Handle click events
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !onClick) return

    if (handlerRef.current) {
      handlerRef.current.destroy()
    }

    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
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

    handlerRef.current = handler
  }, [onClick])

  // Update WMS layer when activeLayer or month changes
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return

    if (wmsLayerRef.current) {
      viewer.imageryLayers.remove(wmsLayerRef.current)
      wmsLayerRef.current = null
    }

    const layerCfg = LAYER_CONFIG[activeLayer]
    if (!layerCfg) return

    try {
      const monthStr = String(month).padStart(2, '0')
      const datasetId = `${activeLayer}_m${monthStr}`

      const provider = new WebMapServiceImageryProvider({
        url: `${XPUBLISH_BASE}/datasets/${datasetId}/wms/`,
        layers: activeLayer,
        getFeatureInfoUrl: undefined as any,
        parameters: {
          format: 'image/png',
          transparent: 'true',
          colorscalerange: `${layerCfg.vmin},${layerCfg.vmax}`,
          styles: `raster/${layerCfg.colormap}`,
        },
      })
      provider.enablePickFeatures = false

      const layer = viewer.imageryLayers.addImageryProvider(provider)
      layer.alpha = 0.7
      wmsLayerRef.current = layer
    } catch (e) {
      console.warn('WMS layer failed to load:', e)
    }
  }, [activeLayer, month])

  const handleZoomIn = () => {
    const viewer = viewerRef.current
    if (viewer) viewer.camera.zoomIn(viewer.camera.positionCartographic.height * 0.4)
  }

  const handleZoomOut = () => {
    const viewer = viewerRef.current
    if (viewer) viewer.camera.zoomOut(viewer.camera.positionCartographic.height * 0.6)
  }

  return (
    <>
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      />
      <div className="zoom-controls">
        <button className="zoom-btn" onClick={handleZoomIn} title="放大">+</button>
        <button className="zoom-btn" onClick={handleZoomOut} title="缩小">−</button>
      </div>
    </>
  )
}

export { LAYER_CONFIG }
