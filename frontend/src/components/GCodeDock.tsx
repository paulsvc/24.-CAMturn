import React, { useState } from 'react'
import { VerificationReport } from '../types'
import { Copy, Download, Check, ShieldCheck, ShieldAlert, FileCode } from 'lucide-react'

interface GCodeDockProps {
  gcodeText: string
  dialect: string
  verification?: VerificationReport | null
  onChangeDialect: (dialect: string) => void
  onDownloadGCode: () => void
}

export const GCodeDock: React.FC<GCodeDockProps> = ({
  gcodeText,
  dialect,
  verification,
  onChangeDialect,
  onDownloadGCode,
}) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(gcodeText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const lines = gcodeText.split('\n')

  return (
    <div className="flex flex-col h-full bg-slate-900 border-t border-slate-800 text-slate-200 select-none text-xs">
      {/* Header Bar */}
      <div className="p-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-300">G-CODE OUTPUT</span>

          {/* Verification Status */}
          {verification && (
            <div
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${
                verification.is_valid
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                  : 'bg-red-950/60 text-red-400 border-red-800'
              }`}
            >
              {verification.is_valid ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>VERIFIED PASS</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>{verification.error_count} ERRORS</span>
                </>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Dialect Selector */}
          <select
            value={dialect}
            onChange={(e) => onChangeDialect(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 focus:outline-none"
          >
            <option value="linuxcnc">LinuxCNC (G7/G8/G76)</option>
            <option value="fanuc">Fanuc 0i-TD (G96/G76)</option>
            <option value="ncviewer">NCViewer Backplot</option>
          </select>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            title="Copy G-Code to clipboard"
            className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Download Button */}
          <button
            onClick={onDownloadGCode}
            title="Download production NC file"
            className="flex items-center gap-1 px-2 py-1 bg-sky-600 hover:bg-sky-500 rounded text-white font-medium transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .ngc</span>
          </button>
        </div>
      </div>

      {/* Verification details bar */}
      {verification && (
        <div className="bg-slate-950/80 px-3 py-1 border-b border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <div>
            Lines: <strong className="text-slate-200">{verification.total_lines}</strong> | Rapid:{' '}
            <strong className="text-red-400">{verification.rapid_count}</strong> | Linear:{' '}
            <strong className="text-emerald-400">{verification.linear_count}</strong> | Arcs:{' '}
            <strong className="text-cyan-400">{verification.arc_count}</strong>
          </div>
          <div>
            Max Part Gouge:{' '}
            <strong className={verification.max_part_gouge_mm > 0 ? 'text-red-400' : 'text-emerald-400'}>
              {verification.max_part_gouge_mm.toFixed(4)} mm
            </strong>
          </div>
        </div>
      )}

      {/* Editor Lines */}
      <div className="flex-1 overflow-y-auto bg-slate-950 p-2 font-mono text-xs select-text">
        {lines.map((line, idx) => (
          <div key={idx} className="flex hover:bg-slate-900/60 leading-5">
            <span className="w-10 text-right pr-3 text-slate-600 select-none">{idx + 1}</span>
            <span
              className={
                line.startsWith('(') || line.startsWith(';')
                  ? 'text-slate-500 italic'
                  : line.startsWith('G0')
                  ? 'text-red-400 font-semibold'
                  : line.startsWith('G1')
                  ? 'text-emerald-300'
                  : line.startsWith('G2') || line.startsWith('G3')
                  ? 'text-cyan-300'
                  : line.startsWith('G76') || line.startsWith('G33')
                  ? 'text-amber-300'
                  : 'text-slate-200'
              }
            >
              {line}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
