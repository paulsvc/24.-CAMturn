import React, { useState } from 'react'
import { OperationNode, Stock, TurnedFace } from '../types'
import {
  Layers,
  ChevronRight,
  ChevronDown,
  Box,
  Trash2,
  ArrowUp,
  ArrowDown,
  PlusCircle,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react'

interface FeatureTreeProps {
  stock: Stock
  faces: TurnedFace[]
  operations: OperationNode[]
  selectedOpId: string | null
  onSelectOp: (opId: string) => void
  onToggleOp: (opId: string) => void
  onDeleteOp: (opId: string) => void
  onMoveOp: (opId: string, direction: 'up' | 'down') => void
  onAddFaceOp: (faceId: string, opType: string) => void
}

export const FeatureTree: React.FC<FeatureTreeProps> = ({
  stock,
  faces,
  operations,
  selectedOpId,
  onSelectOp,
  onToggleOp,
  onDeleteOp,
  onMoveOp,
  onAddFaceOp,
}) => {
  const [facesOpen, setFacesOpen] = useState(true)
  const [opsOpen, setOpsOpen] = useState(true)

  const getFaceTypeColor = (type: string) => {
    switch (type) {
      case 'Cylinder':
        return 'text-sky-400 bg-sky-950/50 border-sky-800'
      case 'Shoulder':
        return 'text-emerald-400 bg-emerald-950/50 border-emerald-800'
      case 'Taper / Chamfer':
        return 'text-amber-400 bg-amber-950/50 border-amber-800'
      case 'Fillet / Radius':
        return 'text-purple-400 bg-purple-950/50 border-purple-800'
      default:
        return 'text-slate-400 bg-slate-900 border-slate-700'
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 text-slate-200 select-none overflow-y-auto text-xs">
      <div className="p-3 border-b border-slate-800 font-semibold text-slate-300 flex items-center justify-between">
        <span className="tracking-wide">FEATURE MANAGER</span>
        <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono">
          {operations.length} OPS
        </span>
      </div>

      {/* Stock Cylinder Node */}
      <div className="p-2 border-b border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-1.5 font-medium text-slate-300 mb-1">
          <Box className="w-4 h-4 text-indigo-400" />
          <span>Workpiece Stock Envelope</span>
        </div>
        <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-400 pl-5 font-mono">
          <div>OD: <strong className="text-slate-200">{stock.od_mm} mm</strong></div>
          <div>ID: <strong className="text-slate-200">{stock.id_mm} mm</strong></div>
          <div>Z0: <strong className="text-slate-200">+{stock.z_start_mm} mm</strong></div>
          <div>Z End: <strong className="text-slate-200">{stock.z_end_mm} mm</strong></div>
        </div>
      </div>

      {/* CAD Turned Faces Section */}
      <div className="border-b border-slate-800">
        <button
          onClick={() => setFacesOpen(!facesOpen)}
          className="w-full p-2 flex items-center justify-between font-semibold text-slate-300 hover:bg-slate-800/50 transition"
        >
          <div className="flex items-center gap-1.5">
            {facesOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <Layers className="w-4 h-4 text-sky-400" />
            <span>Turned Faces ({faces.length})</span>
          </div>
        </button>

        {facesOpen && (
          <div className="pl-3 pr-2 pb-2 space-y-1">
            {faces.map((face) => (
              <div
                key={face.face_id}
                className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${getFaceTypeColor(face.face_type)}`}>
                    F{face.index}: {face.face_type}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">
                    Ø{face.dia_max_mm} mm
                  </span>
                </div>

                <div className="text-[10px] text-slate-400 mt-1 font-mono flex justify-between">
                  <span>Z: [{face.z_max} → {face.z_min}]</span>
                  <span>L: {face.length_mm} mm</span>
                </div>

                {/* Quick 1-click operation buttons */}
                <div className="flex items-center gap-1 mt-1.5 pt-1 border-t border-slate-800/60 text-[10px]">
                  <button
                    onClick={() => onAddFaceOp(face.face_id, 'OD Roughing')}
                    title="Generate OD Roughing for this face"
                    className="px-1.5 py-0.5 bg-sky-950 hover:bg-sky-900 text-sky-300 rounded border border-sky-800 transition"
                  >
                    + Rough
                  </button>
                  <button
                    onClick={() => onAddFaceOp(face.face_id, 'OD Profile Finishing')}
                    title="Generate OD Finishing for this face"
                    className="px-1.5 py-0.5 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 rounded border border-emerald-800 transition"
                  >
                    + Finish
                  </button>
                  {face.face_type === 'Cylinder' && (
                    <button
                      onClick={() => onAddFaceOp(face.face_id, 'OD Threading (G76)')}
                      title="Generate Threading for this cylinder"
                      className="px-1.5 py-0.5 bg-amber-950 hover:bg-amber-900 text-amber-300 rounded border border-amber-800 transition"
                    >
                      + Thread
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* CAM Operations Section */}
      <div className="flex-1">
        <button
          onClick={() => setOpsOpen(!opsOpen)}
          className="w-full p-2 flex items-center justify-between font-semibold text-slate-300 hover:bg-slate-800/50 transition"
        >
          <div className="flex items-center gap-1.5">
            {opsOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <PlusCircle className="w-4 h-4 text-emerald-400" />
            <span>CAM Operations ({operations.length})</span>
          </div>
        </button>

        {opsOpen && (
          <div className="p-2 space-y-1.5">
            {operations.map((op, idx) => {
              const isSelected = selectedOpId === op.op_id
              return (
                <div
                  key={op.op_id}
                  onClick={() => onSelectOp(op.op_id)}
                  className={`p-2 rounded-lg border cursor-pointer transition ${
                    isSelected
                      ? 'bg-sky-950/60 border-sky-500 shadow-sm'
                      : op.enabled
                      ? 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
                      : 'bg-slate-950/20 border-slate-900 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <div className="flex items-center gap-1.5 truncate">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onToggleOp(op.op_id)
                        }}
                        title={op.enabled ? 'Disable Operation' : 'Enable Operation'}
                        className="text-slate-400 hover:text-white"
                      >
                        {op.enabled ? (
                          <Eye className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <EyeOff className="w-3.5 h-3.5 text-slate-500" />
                        )}
                      </button>
                      <span className="font-semibold text-slate-200 truncate" title={op.name}>
                        {op.name}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 font-mono text-sky-300">
                        T{op.tool_id}
                      </span>
                      <button
                        disabled={idx === 0}
                        onClick={(e) => {
                          e.stopPropagation()
                          onMoveOp(op.op_id, 'up')
                        }}
                        className="p-1 hover:bg-slate-800 rounded disabled:opacity-30"
                      >
                        <ArrowUp className="w-3 h-3" />
                      </button>
                      <button
                        disabled={idx === operations.length - 1}
                        onClick={(e) => {
                          e.stopPropagation()
                          onMoveOp(op.op_id, 'down')
                        }}
                        className="p-1 hover:bg-slate-800 rounded disabled:opacity-30"
                      >
                        <ArrowDown className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteOp(op.op_id)
                        }}
                        className="p-1 hover:bg-red-950 text-slate-400 hover:text-red-400 rounded"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {op.warning_message && (
                    <div className="flex items-center gap-1 text-[10px] text-amber-400 mt-1">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span className="truncate">{op.warning_message}</span>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between mt-1">
                    <span>DOC: {op.doc_mm} mm</span>
                    <span>F: {op.feed_mm_rev} mm/r</span>
                    <span>{op.command_count} cmds</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
