import React, { useState, useEffect } from 'react'
import { LatheTool } from '../types'
import { Wrench, X, Check, Eye } from 'lucide-react'

interface ToolLibraryModalProps {
  isOpen: boolean
  tools: LatheTool[]
  onClose: () => void
  onSaveTools: (tools: LatheTool[]) => void
}

export const ToolLibraryModal: React.FC<ToolLibraryModalProps> = ({
  isOpen,
  tools,
  onClose,
  onSaveTools,
}) => {
  const [turret, setTurret] = useState<LatheTool[]>(tools)
  const [selectedToolId, setSelectedToolId] = useState<number>(tools[0]?.tool_id || 1)
  const [presets, setPresets] = useState<Record<string, any>>({})
  const [shapes, setShapes] = useState<Record<string, string>>({})

  useEffect(() => {
    setTurret(tools)
    if (tools.length > 0 && !tools.find((t) => t.tool_id === selectedToolId)) {
      setSelectedToolId(tools[0].tool_id)
    }
  }, [tools])

  useEffect(() => {
    fetch('/api/tools/presets')
      .then((r) => r.json())
      .then((d) => setPresets(d))
      .catch(() => {})

    fetch('/api/tools/iso_shapes')
      .then((r) => r.json())
      .then((d) => setShapes(d))
      .catch(() => {})
  }, [])

  if (!isOpen) return null

  const activeTool = turret.find((t) => t.tool_id === selectedToolId) || turret[0]

  const handleUpdateActiveTool = (field: keyof LatheTool, value: any) => {
    setTurret((prev) =>
      prev.map((t) => (t.tool_id === activeTool.tool_id ? { ...t, [field]: value } : t))
    )
  }

  const handleApplyPreset = (presetKey: string) => {
    const p = presets[presetKey]
    if (!p) return
    setTurret((prev) =>
      prev.map((t) =>
        t.tool_id === activeTool.tool_id
          ? {
              ...t,
              name: p.name || presetKey,
              insert_shape: p.insert_shape,
              inscribed_circle_mm: p.inscribed_circle_mm,
              thickness_mm: p.thickness_mm,
              nose_radius_mm: p.nose_radius_mm,
              cutting_edge_length_mm: p.cutting_edge_length_mm,
              clearance_angle_deg: p.clearance_angle_deg,
              lead_angle_deg: p.lead_angle_deg,
              max_doc_mm: p.max_doc_mm,
              tip_width_mm: p.tip_width_mm || t.tip_width_mm,
            }
          : t
      )
    )
  }

  const handleSave = () => {
    onSaveTools(turret)
    onClose()
  }

  // Draw 2D SVG Blueprint
  const renderSVGBlueprint = () => {
    if (!activeTool) return null
    const shape = activeTool.insert_shape.toUpperCase()
    const ic = activeTool.inscribed_circle_mm
    const r = activeTool.nose_radius_mm

    // Normalized SVG path centered at (100, 100)
    let pathD = ''
    if (shape === 'C') {
      // 80 deg diamond
      pathD = 'M 100 40 L 155 100 L 100 160 L 45 100 Z'
    } else if (shape === 'D') {
      // 55 deg diamond
      pathD = 'M 100 30 L 140 100 L 100 170 L 60 100 Z'
    } else if (shape === 'V') {
      // 35 deg diamond
      pathD = 'M 100 20 L 130 100 L 100 180 L 70 100 Z'
    } else if (shape === 'W') {
      // 80 deg trigon
      pathD = 'M 100 40 L 150 90 L 125 150 L 75 150 L 50 90 Z'
    } else if (shape === 'T') {
      // 60 deg triangle
      pathD = 'M 100 35 L 160 150 L 40 150 Z'
    } else if (shape === 'S') {
      // 90 deg square
      pathD = 'M 50 50 L 150 50 L 150 150 L 50 150 Z'
    } else if (shape === 'R') {
      // Round insert
      pathD = 'M 100 50 A 50 50 0 1 0 100 150 A 50 50 0 1 0 100 50 Z'
    } else if (shape === 'PART') {
      // Parting blade
      pathD = 'M 85 30 L 115 30 L 115 170 L 85 170 Z'
    } else if (shape === 'DRILL') {
      // Drill point
      pathD = 'M 100 30 L 140 80 L 140 170 L 60 170 L 60 80 Z'
    } else {
      pathD = 'M 100 35 L 160 150 L 40 150 Z'
    }

    return (
      <svg viewBox="0 0 200 200" className="w-48 h-48 bg-slate-950 rounded-lg border border-slate-800">
        {/* Grid lines */}
        <line x1="100" y1="10" x2="100" y2="190" stroke="#334155" strokeDasharray="2,2" />
        <line x1="10" y1="100" x2="190" y2="100" stroke="#334155" strokeDasharray="2,2" />
        {/* Insert body */}
        <path d={pathD} fill="#f59e0b" fillOpacity="0.8" stroke="#d97706" strokeWidth="2" />
        {/* Center hole */}
        <circle cx="100" cy="100" r="16" fill="#0f172a" stroke="#cbd5e1" strokeWidth="1.5" />
        {/* Cutting tip nose radius indicator */}
        <circle cx="100" cy="35" r={Math.max(4, r * 4)} fill="none" stroke="#38bdf8" strokeWidth="1.5" />
        <text x="10" y="25" fill="#94a3b8" fontSize="10" fontFamily="monospace">
          IC {ic}mm | rε {r}mm
        </text>
      </svg>
    )
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-4xl flex flex-col overflow-hidden text-xs text-slate-200">
        {/* Header */}
        <div className="p-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-slate-100 text-sm">
            <Wrench className="w-5 h-5 text-sky-400" />
            <span>ISO Lathe Tool & Insert Library Editor</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-800 p-4 gap-4 flex-1 overflow-y-auto">
          {/* Turret Pocket List */}
          <div className="space-y-2">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[11px] block">
              Active Turret Pockets
            </span>
            <div className="space-y-1">
              {turret.map((t) => (
                <button
                  key={t.tool_id}
                  onClick={() => setSelectedToolId(t.tool_id)}
                  className={`w-full p-2 rounded-lg text-left border flex items-center justify-between transition ${
                    selectedToolId === t.tool_id
                      ? 'bg-sky-950 border-sky-500 text-white'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-[10px] text-sky-400">
                      T{t.tool_id}
                    </span>
                    <span className="font-medium truncate">{t.name}</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400">[{t.insert_shape}]</span>
                </button>
              ))}
            </div>

            {/* Standard Presets */}
            <div className="mt-4 pt-3 border-t border-slate-800">
              <span className="font-semibold text-slate-400 text-[11px] block mb-1.5">
                Load Standard ISO Preset
              </span>
              <select
                onChange={(e) => handleApplyPreset(e.target.value)}
                defaultValue=""
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 focus:outline-none"
              >
                <option value="" disabled>
                  -- Select ISO Preset --
                </option>
                {Object.keys(presets).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Tool Parameter Editor */}
          <div className="space-y-3">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[11px] block">
              Insert Dimensions & Angles
            </span>

            <div>
              <label className="text-slate-400 block mb-1">Tool Description</label>
              <input
                type="text"
                value={activeTool?.name || ''}
                onChange={(e) => handleUpdateActiveTool('name', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">ISO Shape Geometry</label>
              <select
                value={activeTool?.insert_shape || 'C'}
                onChange={(e) => handleUpdateActiveTool('insert_shape', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 focus:outline-none"
              >
                {Object.entries(shapes).map(([code, desc]) => (
                  <option key={code} value={code}>
                    {code} — {desc}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 block mb-1">Inscribed Circle IC (mm)</label>
                <input
                  type="number"
                  step="0.1"
                  value={activeTool?.inscribed_circle_mm || 12.7}
                  onChange={(e) => handleUpdateActiveTool('inscribed_circle_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Nose Radius rε (mm)</label>
                <input
                  type="number"
                  step="0.1"
                  value={activeTool?.nose_radius_mm || 0.8}
                  onChange={(e) => handleUpdateActiveTool('nose_radius_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 block mb-1">Thickness s (mm)</label>
                <input
                  type="number"
                  step="0.1"
                  value={activeTool?.thickness_mm || 4.76}
                  onChange={(e) => handleUpdateActiveTool('thickness_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Clearance Angle (°)</label>
                <input
                  type="number"
                  step="1"
                  value={activeTool?.clearance_angle_deg || 5}
                  onChange={(e) => handleUpdateActiveTool('clearance_angle_deg', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 block mb-1">Lead / Approach Angle (°)</label>
                <input
                  type="number"
                  step="1"
                  value={activeTool?.lead_angle_deg || 95}
                  onChange={(e) => handleUpdateActiveTool('lead_angle_deg', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Max DOC (mm)</label>
                <input
                  type="number"
                  step="0.5"
                  value={activeTool?.max_doc_mm || 2.5}
                  onChange={(e) => handleUpdateActiveTool('max_doc_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Live 2D Blueprint Preview */}
          <div className="flex flex-col items-center justify-center p-2 text-center space-y-3">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[11px] block">
              2D Insert Blueprint Preview
            </span>
            {renderSVGBlueprint()}
            <p className="text-[11px] text-slate-400 max-w-[200px]">
              Parametric geometry with cutting nose radius circle and inscribed circle indicator.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 hover:bg-slate-800 rounded text-slate-300 transition">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1 px-4 py-1.5 bg-sky-600 hover:bg-sky-500 rounded text-white font-medium transition"
          >
            <Check className="w-4 h-4" />
            <span>Save to Turret</span>
          </button>
        </div>
      </div>
    </div>
  )
}
