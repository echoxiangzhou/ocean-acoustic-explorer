import './ColorBar.css'

interface ColorBarProps {
  label: string
  unit: string
  vmin: number
  vmax: number
  colormap: string
}

// CSS gradient approximations of common colormaps
const COLORMAP_GRADIENTS: Record<string, string> = {
  viridis: 'linear-gradient(to right, #440154, #482878, #3e4989, #31688e, #26828e, #1f9e89, #35b779, #6ece58, #b5de2b, #fde725)',
  plasma: 'linear-gradient(to right, #0d0887, #4b03a1, #7d03a8, #a82296, #cb4678, #e56b5d, #f89441, #fdc328, #f0f921)',
  inferno: 'linear-gradient(to right, #000004, #1b0c41, #4a0c6b, #781c6d, #a52c60, #cf4446, #ed6925, #fb9b06, #f7d13d, #fcffa4)',
  turbo: 'linear-gradient(to right, #30123b, #4145ab, #4675ed, #39a2fc, #1bcfd4, #24eca6, #61fc6c, #a4fc3b, #d1e834, #f0b31c, #fe7b09, #e8430a, #be0515)',
  magma: 'linear-gradient(to right, #000004, #180f3d, #440f76, #721f81, #9e2f7f, #cd4071, #f1605d, #fd9668, #feca8d, #fcfdbf)',
  Set1: 'linear-gradient(to right, #e41a1c, #377eb8, #4daf4a, #984ea3, #ff7f00)',
}

export function ColorBar({ label, unit, vmin, vmax, colormap }: ColorBarProps) {
  const gradient = COLORMAP_GRADIENTS[colormap] || COLORMAP_GRADIENTS.viridis
  const mid = ((vmin + vmax) / 2).toFixed(0)

  return (
    <div className="colorbar">
      <div className="colorbar-label">{label}</div>
      <div className="colorbar-gradient" style={{ background: gradient }} />
      <div className="colorbar-ticks">
        <span>{vmin}</span>
        <span>{mid}</span>
        <span>{vmax}{unit ? ` ${unit}` : ''}</span>
      </div>
    </div>
  )
}
