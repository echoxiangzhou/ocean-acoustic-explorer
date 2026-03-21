import { create } from 'zustand'

interface LayerState {
  activeLayer: string
  month: number
  srcDepth: number
  frequency: number
  setActiveLayer: (layer: string) => void
  setMonth: (month: number) => void
  setSrcDepth: (depth: number) => void
  setFrequency: (freq: number) => void
}

export const useLayerStore = create<LayerState>((set) => ({
  activeLayer: 'channel_axis',
  month: 1,
  srcDepth: 50,
  frequency: 1000,
  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setMonth: (month) => set({ month }),
  setSrcDepth: (srcDepth) => set({ srcDepth }),
  setFrequency: (frequency) => set({ frequency }),
}))
