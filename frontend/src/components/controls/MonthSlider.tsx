import { useState, useRef, useEffect } from 'react'
import { useLayerStore } from '../../stores/layerStore'
import './MonthSlider.css'

const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

export function MonthSlider() {
  const { month, setMonth } = useLayerStore()
  const [playing, setPlaying] = useState(false)
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (playing) {
      intervalRef.current = window.setInterval(() => {
        setMonth((prev: number) => (prev % 12) + 1)
      }, 1500)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [playing, setMonth])

  return (
    <div className="month-slider-bar">
      <button
        className="play-btn"
        onClick={() => setPlaying(!playing)}
        title={playing ? '暂停' : '播放季节动画'}
      >
        {playing ? '⏸' : '▶'}
      </button>
      <div className="month-track">
        {MONTH_NAMES.map((name, i) => (
          <button
            key={i}
            className={`month-dot ${month === i + 1 ? 'active' : ''}`}
            onClick={() => { setPlaying(false); setMonth(i + 1) }}
            title={name}
          >
            <span className="dot" />
            <span className="month-label">{name}</span>
          </button>
        ))}
      </div>
      <span className="current-month">{MONTH_NAMES[month - 1]}</span>
    </div>
  )
}
