import React from 'react'
import { SimulationWaypoint } from '../types'
import { Play, Pause, Square, SkipBack, SkipForward, FastForward } from 'lucide-react'

interface SimulationControlsProps {
  waypoints: SimulationWaypoint[]
  currentIndex: number
  isPlaying: boolean
  speedMultiplier: number
  onPlayPause: () => void
  onReset: () => void
  onStepBack: () => void
  onStepForward: () => void
  onSeek: (index: number) => void
  onChangeSpeed: (speed: number) => void
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  waypoints,
  currentIndex,
  isPlaying,
  speedMultiplier,
  onPlayPause,
  onReset,
  onStepBack,
  onStepForward,
  onSeek,
  onChangeSpeed,
}) => {
  const currentWp = waypoints[currentIndex] || null
  const total = waypoints.length

  const getModeBadgeClass = (mode: string) => {
    switch (mode) {
      case 'G0':
        return 'bg-red-500/20 text-red-400 border-red-500/40'
      case 'G1':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
      case 'G2':
      case 'G3':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
      default:
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40'
    }
  }

  return (
    <div className="bg-slate-900 border-t border-slate-800 p-3 select-none flex flex-col md:flex-row items-center justify-between gap-3 text-slate-200">
      {/* Left: Transport Buttons */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={onReset}
          title="Reset Simulation (Start)"
          className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition"
        >
          <Square className="w-4 h-4" />
        </button>
        <button
          onClick={onStepBack}
          title="Step Backward"
          className="p-2 hover:bg-slate-800 rounded-lg text-slate-300 hover:text-white transition"
        >
          <SkipBack className="w-4 h-4" />
        </button>
        <button
          onClick={onPlayPause}
          title={isPlaying ? 'Pause' : 'Play Tool Simulation'}
          className={`px-4 py-2 rounded-lg font-medium flex items-center gap-1.5 transition ${
            isPlaying
              ? 'bg-amber-600 hover:bg-amber-500 text-white'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white'
          }`}
        >
          {isPlaying ? (
            <>
              <Pause className="w-4 h-4" />
              <span>Pause</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span>Play</span>
            </>
          )}
        </button>
        <button
          onClick={onStepForward}
          title="Step Forward"
          className="p-2 hover:bg-slate-800 rounded-lg text-slate-300 hover:text-white transition"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        {/* Speed multiplier selector */}
        <div className="flex items-center ml-2 bg-slate-950 px-1 py-0.5 rounded-lg border border-slate-800">
          <FastForward className="w-3.5 h-3.5 text-slate-400 ml-1 mr-1" />
          {[0.5, 1, 2, 5].map((spd) => (
            <button
              key={spd}
              onClick={() => onChangeSpeed(spd)}
              className={`px-1.5 py-0.5 text-xs rounded transition font-mono ${
                speedMultiplier === spd
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>

      {/* Middle: Scrub Slider & Step Counter */}
      <div className="flex-1 w-full max-w-xl flex items-center gap-3">
        <span className="text-xs font-mono text-slate-400 min-w-[50px] text-right">
          {total > 0 ? currentIndex + 1 : 0}/{total}
        </span>
        <input
          type="range"
          min={0}
          max={Math.max(0, total - 1)}
          value={currentIndex}
          onChange={(e) => onSeek(parseInt(e.target.value, 10))}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
        />
      </div>

      {/* Right: Digital Coordinate Readout (DRO) */}
      <div className="flex items-center gap-3 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 font-mono text-xs">
        {currentWp ? (
          <>
            <span
              className={`px-1.5 py-0.5 rounded text-[11px] font-bold border ${getModeBadgeClass(
                currentWp.mode
              )}`}
            >
              {currentWp.mode}
            </span>
            <div className="flex items-center gap-2 text-slate-300">
              <span>
                Z:{' '}
                <strong className="text-sky-400">
                  {currentWp.z.toFixed(2)}
                </strong>
              </span>
              <span>
                X (R):{' '}
                <strong className="text-emerald-400">
                  {currentWp.x.toFixed(2)}
                </strong>
              </span>
              <span>
                Ø:{' '}
                <strong className="text-indigo-400">
                  {currentWp.x_dia.toFixed(2)}
                </strong>
              </span>
              {currentWp.f !== undefined && currentWp.f !== null && (
                <span>
                  F: <strong className="text-amber-400">{currentWp.f}</strong>
                </span>
              )}
            </div>
            <span className="text-slate-500 text-[11px] truncate max-w-[140px]" title={currentWp.op_name}>
              {currentWp.op_name} (T{currentWp.tool_id})
            </span>
          </>
        ) : (
          <span className="text-slate-500">No trajectory active</span>
        )}
      </div>
    </div>
  )
}
