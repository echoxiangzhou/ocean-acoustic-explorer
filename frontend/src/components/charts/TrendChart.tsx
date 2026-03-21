import Plot from 'react-plotly.js'

interface TrendData {
  years: number[]
  channel_axis: number[]
  surface_duct_months: number[]
  cz_distance: number[]
  delta_c: number[]
}

export function TrendChart({ data }: { data: TrendData }) {
  const subplots = [
    { y: data.channel_axis, title: '声道轴深度 (m)', color: '#00d4ff' },
    { y: data.surface_duct_months, title: '表面声道月数', color: '#ff6b35' },
    { y: data.cz_distance, title: '会聚区距离 (km)', color: '#44ff88' },
    { y: data.delta_c, title: 'Δc (m/s)', color: '#ff44aa' },
  ]

  const traces = subplots.map((sp, i) => ({
    x: data.years,
    y: sp.y,
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: sp.title,
    line: { color: sp.color, width: 1.5 },
    marker: { size: 3 },
    xaxis: 'x',
    yaxis: `y${i + 1}` as any,
  }))

  return (
    <Plot
      data={traces}
      layout={{
        autosize: true,
        height: 600,
        margin: { l: 60, r: 20, t: 30, b: 40 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
        font: { color: '#8899aa', size: 11 },
        grid: { rows: 4, columns: 1, pattern: 'independent' },
        showlegend: false,
        xaxis: { gridcolor: 'rgba(255,255,255,0.06)' },
        yaxis: { title: subplots[0].title, gridcolor: 'rgba(255,255,255,0.06)' },
        yaxis2: { title: subplots[1].title, gridcolor: 'rgba(255,255,255,0.06)' },
        yaxis3: { title: subplots[2].title, gridcolor: 'rgba(255,255,255,0.06)' },
        yaxis4: { title: subplots[3].title, gridcolor: 'rgba(255,255,255,0.06)' },
      }}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: '100%' }}
    />
  )
}
