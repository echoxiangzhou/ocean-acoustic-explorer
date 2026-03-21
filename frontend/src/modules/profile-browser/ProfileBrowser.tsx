import { useState, useCallback } from 'react'
import { CesiumGlobe } from '../../components/globe/CesiumGlobe'
import { ProfileChart } from '../../components/charts/ProfileChart'
import { useLayerStore } from '../../stores/layerStore'
import { fetchProfile, SoundProfile } from '../../services/api'
import './ProfileBrowser.css'

interface ProfileEntry {
  lat: number
  lon: number
  profile: SoundProfile
  color: string
}

const COLORS = ['#00d4ff', '#ff6b35', '#44ff88', '#ff44aa', '#ffdd44']

export function ProfileBrowser() {
  const { month } = useLayerStore()
  const [profiles, setProfiles] = useState<ProfileEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [source, setSource] = useState('woa23')
  const [formula, setFormula] = useState('teos10')

  const handleMapClick = useCallback(
    async (lat: number, lon: number) => {
      if (profiles.length >= 5) return
      setLoading(true)
      try {
        const profile = await fetchProfile(lat, lon, month, source, formula)
        setProfiles((prev) => [
          ...prev,
          { lat, lon, profile, color: COLORS[prev.length % COLORS.length] },
        ])
      } catch (e) {
        console.error('Failed to fetch profile:', e)
      } finally {
        setLoading(false)
      }
    },
    [month, source, formula, profiles.length]
  )

  return (
    <div className="profile-layout">
      <div className="profile-map">
        <CesiumGlobe onClick={handleMapClick} />
        {loading && <div className="loading-indicator">Loading...</div>}
      </div>
      <div className="profile-panel">
        <div className="profile-controls">
          <div className="control-row">
            <label>数据源</label>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="woa23">WOA23 气候态</option>
              <option value="hycom">HYCOM 实时</option>
            </select>
          </div>
          <div className="control-row">
            <label>声速公式</label>
            <select value={formula} onChange={(e) => setFormula(e.target.value)}>
              <option value="teos10">TEOS-10 (gsw)</option>
              <option value="mackenzie">Mackenzie 1981</option>
              <option value="chen_millero">Chen-Millero</option>
            </select>
          </div>
          <button
            className="clear-btn"
            onClick={() => setProfiles([])}
            disabled={profiles.length === 0}
          >
            清除全部 ({profiles.length}/5)
          </button>
        </div>
        <ProfileChart profiles={profiles} />
        {profiles.length > 0 && (
          <div className="feature-cards">
            {profiles.map((p, i) => (
              <div key={i} className="feature-card" style={{ borderColor: p.color }}>
                <div className="card-header">
                  <span style={{ color: p.color }}>
                    ({p.lat.toFixed(1)}°, {p.lon.toFixed(1)}°)
                  </span>
                </div>
                <div className="card-stats">
                  <div>声道轴: {p.profile.features.channel_axis_depth.toFixed(0)}m</div>
                  <div>表层声速: {p.profile.features.surface_speed.toFixed(1)} m/s</div>
                  <div>Δc: {p.profile.features.delta_c.toFixed(1)} m/s</div>
                  <div>表面声道: {p.profile.features.surface_duct_thickness.toFixed(0)}m</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
