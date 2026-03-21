import Plot from 'react-plotly.js'

interface TLChartProps {
  tl: number[][]       // TL(range, depth) matrix
  range: number[]      // range values (km)
  depth: number[]      // depth values (m)
  bathymetry: number[] // bottom depth along range (m)
  title?: string
}

export function TLChart({ tl, range, depth, bathymetry, title = 'Transmission Loss' }: TLChartProps) {
  return (
    <Plot
      data={[
        {
          z: tl,
          x: range,
          y: depth,
          type: 'heatmap',
          colorscale: 'Viridis',
          reversescale: true,
          zmin: 40,
          zmax: 120,
          colorbar: { title: 'TL (dB)', titlefont: { color: '#8899aa' } },
        },
        // Bathymetry line overlay
        {
          x: range,
          y: bathymetry,
          type: 'scatter',
          mode: 'lines',
          fill: 'tomaxy',
          fillcolor: 'rgba(80, 80, 80, 0.6)',
          line: { color: '#888', width: 2 },
          showlegend: false,
        },
      ]}
      layout={{
        title: { text: title, font: { color: '#8899aa', size: 14 } },
        autosize: true,
        margin: { l: 60, r: 20, t: 40, b: 50 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'rgba(22, 34, 64, 0.5)',
        font: { color: '#8899aa', size: 11 },
        xaxis: {
          title: '距离 (km)',
          gridcolor: 'rgba(255,255,255,0.06)',
        },
        yaxis: {
          title: '深度 (m)',
          autorange: 'reversed',
          gridcolor: 'rgba(255,255,255,0.06)',
        },
      }}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: '100%', height: '400px' }}
    />
  )
}
