import React, { useState, useEffect } from 'react'
import { LatheTool, OperationNode } from '../types'
import { Settings2, RefreshCw } from 'lucide-react'

interface OperationEditorProps {
  operation: OperationNode | null
  tools: LatheTool[]
  onUpdateOperation: (updated: OperationNode) => void
}

export const OperationEditor: React.FC<OperationEditorProps> = ({
  operation,
  tools,
  onUpdateOperation,
}) => {
  const [formData, setFormData] = useState<OperationNode | null>(operation)

  useEffect(() => {
    setFormData(operation)
  }, [operation])

  if (!formData) {
    return (
      <div className="p-4 text-xs text-slate-500 italic text-center h-full flex items-center justify-center">
        Select an operation from the Feature Manager to inspect and edit cutting parameters.
      </div>
    )
  }

  const handleChange = (field: keyof OperationNode, value: any) => {
    if (!formData) return
    const updated = { ...formData, [field]: value }
    setFormData(updated)
    onUpdateOperation(updated)
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200 select-none overflow-y-auto text-xs">
      <div className="p-3 border-b border-slate-800 font-semibold text-slate-300 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Settings2 className="w-4 h-4 text-sky-400" />
          <span>PROPERTIES INSPECTOR</span>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* Operation Name */}
        <div>
          <label className="text-[11px] text-slate-400 block mb-1">Operation Title</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none"
          />
        </div>

        {/* Tool Assignment */}
        <div>
          <label className="text-[11px] text-slate-400 block mb-1">Assigned Turret Tool</label>
          <select
            value={formData.tool_id}
            onChange={(e) => handleChange('tool_id', parseInt(e.target.value, 10))}
            className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            {tools.map((t) => (
              <option key={t.tool_id} value={t.tool_id}>
                T{t.tool_id}: {t.name} (R{t.nose_radius_mm}mm)
              </option>
            ))}
          </select>
        </div>

        {/* Depth of Cut & Allowance */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">DOC (mm)</label>
            <input
              type="number"
              step="0.1"
              value={formData.doc_mm}
              onChange={(e) => handleChange('doc_mm', parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Allowance (mm)</label>
            <input
              type="number"
              step="0.05"
              value={formData.finish_allowance_mm}
              onChange={(e) => handleChange('finish_allowance_mm', parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
        </div>

        {/* Feeds & Speeds */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">CSS (m/min)</label>
            <input
              type="number"
              value={formData.css_m_min}
              onChange={(e) => handleChange('css_m_min', parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Max RPM</label>
            <input
              type="number"
              value={formData.max_rpm}
              onChange={(e) => handleChange('max_rpm', parseInt(e.target.value, 10) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Feed (mm/r)</label>
            <input
              type="number"
              step="0.01"
              value={formData.feed_mm_rev}
              onChange={(e) => handleChange('feed_mm_rev', parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
        </div>

        {/* Retract & Compensation */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Retract (mm)</label>
            <input
              type="number"
              step="0.1"
              value={formData.retract_mm}
              onChange={(e) => handleChange('retract_mm', parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">TNRC Mode</label>
            <select
              value={formData.comp_mode}
              onChange={(e) => handleChange('comp_mode', e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="COMPUTER">Computer (Pre-offset)</option>
              <option value="CONTROLLER">Controller (G41/G42)</option>
              <option value="OFF">Off (Tool Center)</option>
            </select>
          </div>
        </div>

        {/* Specific Parametric Settings */}
        {formData.op_type.includes('Threading') && (
          <div className="p-2 bg-amber-950/30 rounded border border-amber-900/50 space-y-2">
            <span className="font-semibold text-amber-300 block">Threading Parameters</span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block">Pitch (mm)</label>
                <input
                  type="number"
                  step="0.25"
                  value={formData.pitch_mm}
                  onChange={(e) => handleChange('pitch_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block">Major Dia (mm)</label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.major_dia_mm}
                  onChange={(e) => handleChange('major_dia_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {formData.op_type.includes('Drilling') && (
          <div className="p-2 bg-sky-950/30 rounded border border-sky-900/50 space-y-2">
            <span className="font-semibold text-sky-300 block">Drilling Parameters</span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block">Depth Z (mm)</label>
                <input
                  type="number"
                  step="1.0"
                  value={formData.target_z_mm}
                  onChange={(e) => handleChange('target_z_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block">Peck Depth Q (mm)</label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.peck_depth_mm}
                  onChange={(e) => handleChange('peck_depth_mm', parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
