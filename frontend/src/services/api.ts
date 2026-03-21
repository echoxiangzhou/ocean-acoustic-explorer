const API_BASE = '/api'

export interface SoundProfile {
  depth: number[]
  sound_speed: number[]
  features: {
    channel_axis_depth: number
    channel_axis_speed: number
    surface_speed: number
    delta_c: number
    surface_duct_thickness: number
  }
}

export interface AcousticResult {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  result?: {
    tl: number[][]        // TL(r,z) matrix
    rays?: number[][][]   // Ray paths
    range: number[]
    depth: number[]
    bathymetry: number[]
    sound_speed?: number[][]
  }
}

export async function fetchProfile(
  lat: number,
  lon: number,
  month: number,
  source: string = 'woa23',
  formula: string = 'teos10'
): Promise<SoundProfile> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    month: month.toString(),
    source,
    formula,
  })
  const res = await fetch(`${API_BASE}/profiles?${params}`)
  if (!res.ok) throw new Error(`Profile fetch failed: ${res.status}`)
  return res.json()
}

export async function submitAcousticCompute(params: {
  start_lat: number
  start_lon: number
  end_lat: number
  end_lon: number
  src_depth: number
  frequency: number
  model: string
  max_range?: number
}): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/acoustic/compute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error(`Compute submit failed: ${res.status}`)
  return res.json()
}

export async function fetchAcousticResult(taskId: string): Promise<AcousticResult> {
  const res = await fetch(`${API_BASE}/acoustic/result/${taskId}`)
  if (!res.ok) throw new Error(`Result fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchTrends(
  lat: number,
  lon: number
): Promise<{
  years: number[]
  channel_axis: number[]
  surface_duct_months: number[]
  cz_distance: number[]
  delta_c: number[]
}> {
  const params = new URLSearchParams({ lat: lat.toString(), lon: lon.toString() })
  const res = await fetch(`${API_BASE}/trends?${params}`)
  if (!res.ok) throw new Error(`Trends fetch failed: ${res.status}`)
  return res.json()
}

export function createProgressWebSocket(taskId: string, onProgress: (p: number) => void) {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/acoustic/progress/${taskId}`
  const ws = new WebSocket(wsUrl)
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data)
    onProgress(data.progress)
  }
  return ws
}
