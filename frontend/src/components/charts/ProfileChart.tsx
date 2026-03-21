import Plot from 'react-plotly.js'

interface ProfileEntry {
  lat: number
  lon: number
  profile: { depth: number[]; sound_speed: number[]; features: any }
  color: string
}

export function ProfileChart({ profiles }: { profiles: ProfileEntry[] }) {
  if (profiles.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
        点击地图选择位置查看声速剖面
      </div>
    )
  }

  const traces = profiles.map((p) => ({
    x: p.profile.sound_speed,
    y: p.profile.depth,
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: `(${p.lat.toFixed(1)}°, ${p.lon.toFixed(1)}°)`,
    line: { color: p.color, width: 2 },
  }))

  // Add channel axis annotations
  const shapes = profiles.map((p) => ({
    type: 'line' as const,
    x0: 0,
    x1: 1,
    xref: 'paper' as const,
    y0: p.profile.features.channel_axis_depth,
    y1: p.profile.features.channel_axis_depth,
    line: { color: p.color, width: 1, dash: 'dash' as const },
  }))

  return (
    <Plot
      data={traces}
      layout={{
        autosize: true,
        margin: { l: 60, r: 20, t: 20, b: 50 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
        font: { color: '#8899aa', size: 11 },
        xaxis: {
          title: '声速 (m/s)',
          gridcolor: 'rgba(255,255,255,0.06)',
          zerolinecolor: 'rgba(255,255,255,0.06)',
        },
        yaxis: {
          title: '深度 (m)',
          autorange: 'reversed',
          gridcolor: 'rgba(255,255,255,0.06)',
          zerolinecolor: 'rgba(255,255,255,0.06)',
        },
        shapes,
        showlegend: true,
        legend: { x: 1, y: 1, xanchor: 'right', bgcolor: 'transparent', font: { size: 10 } },
      }}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: '100%', height: '350px' }}
    />
  )
}
