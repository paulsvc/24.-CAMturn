import React, { useState, useEffect, useRef } from 'react'
import {
  ProjectState,
  MeshData,
  SimulationWaypoint,
  LatheTool,
  OperationNode,
} from './types'
import {
  fetchProject,
  loadDemoProject,
  recalculateProject,
  addFaceOperation,
  uploadCAD,
  fetchPartMesh,
  fetchStockMesh,
  fetchSimulationWaypoints,
} from './api/client'
import { Viewport3D } from './components/Viewport3D'
import { SimulationControls } from './components/SimulationControls'
import { FeatureTree } from './components/FeatureTree'
import { OperationEditor } from './components/OperationEditor'
import { GCodeDock } from './components/GCodeDock'
import { ToolLibraryModal } from './components/ToolLibraryModal'
import {
  Cpu,
  Upload,
  RotateCcw,
  Wrench,
  FileDown,
  Loader2,
  Box,
  Layers,
  Settings2,
  FileCode,
} from 'lucide-react'

type MobileTab = 'viewport' | 'features' | 'inspector' | 'gcode'

export const App: React.FC = () => {
  const [project, setProject] = useState<ProjectState | null>(null)
  const [partMesh, setPartMesh] = useState<MeshData | null>(null)
  const [stockMesh, setStockMesh] = useState<MeshData | null>(null)
  const [waypoints, setWaypoints] = useState<SimulationWaypoint[]>([])
  const [selectedOpId, setSelectedOpId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isToolModalOpen, setIsToolModalOpen] = useState(false)

  // Mobile navigation tab state
  const [activeMobileTab, setActiveMobileTab] = useState<MobileTab>('viewport')

  // Viewport Settings
  const [cutaway, setCutaway] = useState(true)
  const [showStock, setShowStock] = useState(true)
  const [showRapids, setShowRapids] = useState(true)

  // Simulation Playback State
  const [simIndex, setSimIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speedMultiplier, setSpeedMultiplier] = useState(1)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Initial Load
  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    setIsLoading(true)
    try {
      const proj = await fetchProject()
      setProject(proj)
      if (proj.operations.length > 0) {
        setSelectedOpId(proj.operations[0].op_id)
      }
      await refreshGeometryAndWaypoints(cutaway)
    } catch (err) {
      console.error('Failed to load project:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const refreshGeometryAndWaypoints = async (useCutaway: boolean) => {
    try {
      const [pm, sm, wp] = await Promise.all([
        fetchPartMesh(useCutaway),
        fetchStockMesh(),
        fetchSimulationWaypoints(),
      ])
      setPartMesh(pm)
      setStockMesh(sm)
      setWaypoints(wp)
      setSimIndex(0)
    } catch (err) {
      console.error('Failed to load geometry/waypoints:', err)
    }
  }

  // Animation Playback Loop
  useEffect(() => {
    if (!isPlaying || waypoints.length === 0) return

    const intervalTime = Math.max(16, Math.floor(40 / speedMultiplier))
    const timer = setInterval(() => {
      setSimIndex((prev) => {
        if (prev >= waypoints.length - 1) {
          setIsPlaying(false)
          return 0
        }
        return prev + 1
      })
    }, intervalTime)

    return () => clearInterval(timer)
  }, [isPlaying, speedMultiplier, waypoints])

  // Handlers
  const handleToggleCutaway = async () => {
    const nextVal = !cutaway
    setCutaway(nextVal)
    try {
      const pm = await fetchPartMesh(nextVal)
      setPartMesh(pm)
    } catch (e) {
      console.error(e)
    }
  }

  const handleLoadDemo = async () => {
    setIsLoading(true)
    try {
      const proj = await loadDemoProject()
      setProject(proj)
      if (proj.operations.length > 0) {
        setSelectedOpId(proj.operations[0].op_id)
      }
      await refreshGeometryAndWaypoints(cutaway)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsLoading(true)
    try {
      const updated = await uploadCAD(file)
      setProject(updated)
      setSelectedOpId(null)
      await refreshGeometryAndWaypoints(cutaway)
      setActiveMobileTab('viewport')
    } catch (err: any) {
      alert(`CAD Import Error: ${err.message}`)
    } finally {
      setIsLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleAddFaceOp = async (faceId: string, opType: string) => {
    setIsLoading(true)
    try {
      const updated = await addFaceOperation(faceId, opType)
      setProject(updated)
      const lastOp = updated.operations[updated.operations.length - 1]
      setSelectedOpId(lastOp?.op_id || null)
      const wp = await fetchSimulationWaypoints()
      setWaypoints(wp)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleOp = async (opId: string) => {
    if (!project) return
    const updatedOps = project.operations.map((o) =>
      o.op_id === opId ? { ...o, enabled: !o.enabled } : o
    )
    const updated = await recalculateProject({ operations: updatedOps })
    setProject(updated)
    const wp = await fetchSimulationWaypoints()
    setWaypoints(wp)
  }

  const handleDeleteOp = async (opId: string) => {
    if (!project) return
    const updatedOps = project.operations.filter((o) => o.op_id !== opId)
    const updated = await recalculateProject({ operations: updatedOps })
    setProject(updated)
    if (selectedOpId === opId) {
      setSelectedOpId(updated.operations[0]?.op_id || null)
    }
    const wp = await fetchSimulationWaypoints()
    setWaypoints(wp)
  }

  const handleMoveOp = async (opId: string, direction: 'up' | 'down') => {
    if (!project) return
    const idx = project.operations.findIndex((o) => o.op_id === opId)
    if (idx === -1) return
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1
    if (targetIdx < 0 || targetIdx >= project.operations.length) return

    const newOps = [...project.operations]
    const temp = newOps[idx]
    newOps[idx] = newOps[targetIdx]
    newOps[targetIdx] = temp

    const updated = await recalculateProject({ operations: newOps })
    setProject(updated)
    const wp = await fetchSimulationWaypoints()
    setWaypoints(wp)
  }

  const handleUpdateOperation = async (updatedOp: OperationNode) => {
    if (!project) return
    const newOps = project.operations.map((o) => (o.op_id === updatedOp.op_id ? updatedOp : o))
    const updated = await recalculateProject({ operations: newOps })
    setProject(updated)
    const wp = await fetchSimulationWaypoints()
    setWaypoints(wp)
  }

  const handleSaveTurretTools = async (tools: LatheTool[]) => {
    if (!project) return
    const updated = await recalculateProject({ tools })
    setProject(updated)
    const wp = await fetchSimulationWaypoints()
    setWaypoints(wp)
  }

  const handleChangeDialect = async (dialect: string) => {
    if (!project) return
    const updated = await recalculateProject({ post_dialect: dialect })
    setProject(updated)
  }

  const handleDownloadGCode = () => {
    if (!project) return
    window.location.href = `/api/project/gcode?dialect=${project.post_dialect}`
  }

  const activeOp = project?.operations.find((o) => o.op_id === selectedOpId) || null

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Top Navbar */}
      <header className="h-12 bg-slate-900 border-b border-slate-800 px-3 sm:px-4 flex items-center justify-between shrink-0 select-none">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="flex items-center gap-1.5 font-bold text-sm sm:text-base tracking-tight text-white shrink-0">
            <Cpu className="w-5 h-5 text-sky-400" />
            <span>CAMturn</span>
          </div>
          <span className="hidden sm:inline text-xs text-slate-400 font-mono">
            {project?.name || ''}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2 text-xs">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".step,.stp,.dxf"
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            title="Import 3D STEP or 2D DXF CAD Model"
            className="flex items-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-200 transition"
          >
            <Upload className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden xs:inline">Import</span>
          </button>

          <button
            onClick={handleLoadDemo}
            title="Reload Stepped Aerospace Shaft Demo"
            className="flex items-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-200 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Demo</span>
          </button>

          <button
            onClick={() => setIsToolModalOpen(true)}
            title="ISO Insert Tool Library"
            className="flex items-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-200 transition"
          >
            <Wrench className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Tools</span>
          </button>

          <button
            onClick={handleDownloadGCode}
            title="Download G-Code program"
            className="flex items-center gap-1 px-2.5 py-1.5 bg-sky-600 hover:bg-sky-500 rounded text-white font-medium transition"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">G-Code</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {/* 1. Desktop Layout (lg screens and wider: 3-column studio layout) */}
      <div className="hidden lg:flex flex-1 overflow-hidden">
        {/* Left: Feature Tree */}
        <aside className="w-80 h-full shrink-0">
          {project && (
            <FeatureTree
              stock={project.stock}
              faces={project.faces}
              operations={project.operations}
              selectedOpId={selectedOpId}
              onSelectOp={(id) => setSelectedOpId(id)}
              onToggleOp={handleToggleOp}
              onDeleteOp={handleDeleteOp}
              onMoveOp={handleMoveOp}
              onAddFaceOp={handleAddFaceOp}
            />
          )}
        </aside>

        {/* Center: 3D Viewport & Simulation Transport Controls */}
        <main className="flex-1 flex flex-col h-full overflow-hidden border-r border-slate-800">
          <div className="flex-1 relative">
            {isLoading && (
              <div className="absolute inset-0 z-40 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center gap-2 text-sky-400 text-sm">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Processing CAD / CAM Toolpaths...</span>
              </div>
            )}
            <Viewport3D
              partMesh={partMesh}
              stockMesh={stockMesh}
              waypoints={waypoints}
              activeWaypointIndex={simIndex}
              cutaway={cutaway}
              onToggleCutaway={handleToggleCutaway}
              showStock={showStock}
              onToggleStock={() => setShowStock(!showStock)}
              showRapids={showRapids}
              onToggleRapids={() => setShowRapids(!showRapids)}
            />
          </div>

          <SimulationControls
            waypoints={waypoints}
            currentIndex={simIndex}
            isPlaying={isPlaying}
            speedMultiplier={speedMultiplier}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onReset={() => {
              setIsPlaying(false)
              setSimIndex(0)
            }}
            onStepBack={() => {
              setIsPlaying(false)
              setSimIndex((prev) => Math.max(0, prev - 1))
            }}
            onStepForward={() => {
              setIsPlaying(false)
              setSimIndex((prev) => Math.min(waypoints.length - 1, prev + 1))
            }}
            onSeek={(idx) => {
              setIsPlaying(false)
              setSimIndex(idx)
            }}
            onChangeSpeed={(spd) => setSpeedMultiplier(spd)}
          />
        </main>

        {/* Right: Properties Inspector & G-Code Dock */}
        <aside className="w-96 h-full shrink-0 flex flex-col bg-slate-900">
          <div className="h-1/2 overflow-hidden">
            <OperationEditor
              operation={activeOp}
              tools={project?.tools || []}
              onUpdateOperation={handleUpdateOperation}
            />
          </div>
          <div className="h-1/2 overflow-hidden">
            {project && (
              <GCodeDock
                gcodeText={project.gcode_text}
                dialect={project.post_dialect}
                verification={project.verification}
                onChangeDialect={handleChangeDialect}
                onDownloadGCode={handleDownloadGCode}
              />
            )}
          </div>
        </aside>
      </div>

      {/* 2. Mobile Layout (< lg screens: Tabbed Full-Screen Experience) */}
      <div className="flex lg:hidden flex-1 overflow-hidden flex-col relative">
        {isLoading && (
          <div className="absolute inset-0 z-40 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center gap-2 text-sky-400 text-sm">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Recalculating...</span>
          </div>
        )}

        {/* Tab 1: 3D Viewport & Simulation Controls */}
        <div className={`flex-1 flex flex-col h-full ${activeMobileTab === 'viewport' ? 'flex' : 'hidden'}`}>
          <div className="flex-1 relative">
            <Viewport3D
              partMesh={partMesh}
              stockMesh={stockMesh}
              waypoints={waypoints}
              activeWaypointIndex={simIndex}
              cutaway={cutaway}
              onToggleCutaway={handleToggleCutaway}
              showStock={showStock}
              onToggleStock={() => setShowStock(!showStock)}
              showRapids={showRapids}
              onToggleRapids={() => setShowRapids(!showRapids)}
            />
          </div>

          <SimulationControls
            waypoints={waypoints}
            currentIndex={simIndex}
            isPlaying={isPlaying}
            speedMultiplier={speedMultiplier}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onReset={() => {
              setIsPlaying(false)
              setSimIndex(0)
            }}
            onStepBack={() => {
              setIsPlaying(false)
              setSimIndex((prev) => Math.max(0, prev - 1))
            }}
            onStepForward={() => {
              setIsPlaying(false)
              setSimIndex((prev) => Math.min(waypoints.length - 1, prev + 1))
            }}
            onSeek={(idx) => {
              setIsPlaying(false)
              setSimIndex(idx)
            }}
            onChangeSpeed={(spd) => setSpeedMultiplier(spd)}
          />
        </div>

        {/* Tab 2: Feature Manager (Stock, CAD Faces, Operations) */}
        <div className={`flex-1 overflow-y-auto ${activeMobileTab === 'features' ? 'block' : 'hidden'}`}>
          {project && (
            <FeatureTree
              stock={project.stock}
              faces={project.faces}
              operations={project.operations}
              selectedOpId={selectedOpId}
              onSelectOp={(id) => {
                setSelectedOpId(id)
                setActiveMobileTab('inspector') // Jump to inspector on mobile
              }}
              onToggleOp={handleToggleOp}
              onDeleteOp={handleDeleteOp}
              onMoveOp={handleMoveOp}
              onAddFaceOp={(faceId, opType) => {
                handleAddFaceOp(faceId, opType)
                setActiveMobileTab('viewport') // Jump back to see the path
              }}
            />
          )}
        </div>

        {/* Tab 3: Properties Inspector */}
        <div className={`flex-1 overflow-y-auto ${activeMobileTab === 'inspector' ? 'block' : 'hidden'}`}>
          <OperationEditor
            operation={activeOp}
            tools={project?.tools || []}
            onUpdateOperation={handleUpdateOperation}
          />
        </div>

        {/* Tab 4: G-Code Dock */}
        <div className={`flex-1 overflow-y-auto ${activeMobileTab === 'gcode' ? 'block' : 'hidden'}`}>
          {project && (
            <GCodeDock
              gcodeText={project.gcode_text}
              dialect={project.post_dialect}
              verification={project.verification}
              onChangeDialect={handleChangeDialect}
              onDownloadGCode={handleDownloadGCode}
            />
          )}
        </div>

        {/* Mobile Bottom Navigation Bar */}
        <nav className="h-14 bg-slate-900 border-t border-slate-800 grid grid-cols-4 select-none shrink-0 text-slate-400">
          <button
            onClick={() => setActiveMobileTab('viewport')}
            className={`flex flex-col items-center justify-center gap-1 transition ${
              activeMobileTab === 'viewport' ? 'text-sky-400 font-semibold bg-slate-800/40' : 'hover:text-slate-200'
            }`}
          >
            <Box className="w-5 h-5" />
            <span className="text-[10px]">3D View</span>
          </button>

          <button
            onClick={() => setActiveMobileTab('features')}
            className={`flex flex-col items-center justify-center gap-1 transition relative ${
              activeMobileTab === 'features' ? 'text-sky-400 font-semibold bg-slate-800/40' : 'hover:text-slate-200'
            }`}
          >
            <Layers className="w-5 h-5" />
            <span className="text-[10px]">Operations</span>
            {project && project.operations.length > 0 && (
              <span className="absolute top-1.5 right-4 bg-sky-600 text-white rounded-full w-4 h-4 text-[9px] flex items-center justify-center font-bold">
                {project.operations.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveMobileTab('inspector')}
            className={`flex flex-col items-center justify-center gap-1 transition ${
              activeMobileTab === 'inspector' ? 'text-sky-400 font-semibold bg-slate-800/40' : 'hover:text-slate-200'
            }`}
          >
            <Settings2 className="w-5 h-5" />
            <span className="text-[10px]">Inspector</span>
          </button>

          <button
            onClick={() => setActiveMobileTab('gcode')}
            className={`flex flex-col items-center justify-center gap-1 transition relative ${
              activeMobileTab === 'gcode' ? 'text-sky-400 font-semibold bg-slate-800/40' : 'hover:text-slate-200'
            }`}
          >
            <FileCode className="w-5 h-5" />
            <span className="text-[10px]">G-Code</span>
            {project?.verification?.is_valid && (
              <span className="absolute top-2 right-5 bg-emerald-500 rounded-full w-2 h-2" />
            )}
          </button>
        </nav>
      </div>

      {/* ISO Tool Library Modal (Both Desktop & Mobile) */}
      {project && (
        <ToolLibraryModal
          isOpen={isToolModalOpen}
          tools={project.tools}
          onClose={() => setIsToolModalOpen(false)}
          onSaveTools={handleSaveTurretTools}
        />
      )}
    </div>
  )
}

export default App
