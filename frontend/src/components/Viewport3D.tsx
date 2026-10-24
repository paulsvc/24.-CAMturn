import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { MeshData, SimulationWaypoint } from '../types'
import { RotateCcw, Eye, Layers, Compass, Scissors } from 'lucide-react'

interface Viewport3DProps {
  partMesh: MeshData | null
  stockMesh: MeshData | null
  waypoints: SimulationWaypoint[]
  activeWaypointIndex: number
  cutaway: boolean
  onToggleCutaway: () => void
  showStock: boolean
  onToggleStock: () => void
  showRapids: boolean
  onToggleRapids: () => void
}

export const Viewport3D: React.FC<Viewport3DProps> = ({
  partMesh,
  stockMesh,
  waypoints,
  activeWaypointIndex,
  cutaway,
  onToggleCutaway,
  showStock,
  onToggleStock,
  showRapids,
  onToggleRapids,
}) => {
  const mountRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)

  // Mesh refs
  const partObjectRef = useRef<THREE.Mesh | null>(null)
  const stockObjectRef = useRef<THREE.Mesh | null>(null)
  const toolObjectRef = useRef<THREE.Group | null>(null)
  const pathsGroupRef = useRef<THREE.Group | null>(null)

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x131722) // Industrial dark CAD slate
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      2000
    )
    camera.position.set(-60, 50, 90)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.1
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.target.set(-20, 0, 0) // Center near middle of lathe part
    controlsRef.current = controls

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2)
    keyLight.position.set(50, 100, 75)
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0x90b0e0, 0.8)
    fillLight.position.set(-80, -40, -50)
    scene.add(fillLight)

    // Lathe Spindle Centerline (Z axis)
    const axisMat = new THREE.LineDashedMaterial({
      color: 0x64748b,
      dashSize: 3,
      gapSize: 2,
    })
    const axisGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(20, 0, 0),
      new THREE.Vector3(-80, 0, 0),
    ])
    const axisLine = new THREE.Line(axisGeo, axisMat)
    axisLine.computeLineDistances()
    scene.add(axisLine)

    // Tool Group (Holder + Carbide Insert)
    const toolGroup = new THREE.Group()
    
    // Shank
    const shankGeo = new THREE.BoxGeometry(10, 8, 25)
    const shankMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.8,
      roughness: 0.3,
    })
    const shankMesh = new THREE.Mesh(shankGeo, shankMat)
    shankMesh.position.set(5, 4, 12.5)
    toolGroup.add(shankMesh)

    // Insert (Rhombic carbide gold)
    const insertGeo = new THREE.ConeGeometry(4, 3, 4) // Diamond approximation
    insertGeo.rotateZ(Math.PI / 4)
    const insertMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b, // Tungsten carbide gold/amber
      metalness: 0.85,
      roughness: 0.2,
    })
    const insertMesh = new THREE.Mesh(insertGeo, insertMat)
    insertMesh.position.set(0, 0, 0)
    toolGroup.add(insertMesh)

    toolGroup.visible = false
    scene.add(toolGroup)
    toolObjectRef.current = toolGroup

    // Toolpaths group
    const pathsGroup = new THREE.Group()
    scene.add(pathsGroup)
    pathsGroupRef.current = pathsGroup

    // Animation Loop
    let animId: number
    const animate = () => {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize Handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // Update Part Mesh
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || !partMesh) return

    if (partObjectRef.current) {
      scene.remove(partObjectRef.current)
      partObjectRef.current.geometry.dispose()
      partObjectRef.current = null
    }

    if (partMesh.vertices.length > 0) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(partMesh.vertices, 3)
      )
      if (partMesh.normals.length > 0) {
        geo.setAttribute(
          'normal',
          new THREE.Float32BufferAttribute(partMesh.normals, 3)
        )
      } else {
        geo.computeVertexNormals()
      }
      geo.setIndex(partMesh.indices)

      const mat = new THREE.MeshStandardMaterial({
        color: 0xc8d3e2, // Machined metal
        metalness: 0.7,
        roughness: 0.28,
        side: THREE.DoubleSide,
      })
      const mesh = new THREE.Mesh(geo, mat)
      scene.add(mesh)
      partObjectRef.current = mesh
    }
  }, [partMesh])

  // Update Stock Mesh
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || !stockMesh) return

    if (stockObjectRef.current) {
      scene.remove(stockObjectRef.current)
      stockObjectRef.current.geometry.dispose()
      stockObjectRef.current = null
    }

    if (stockMesh.vertices.length > 0) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(stockMesh.vertices, 3)
      )
      geo.computeVertexNormals()
      geo.setIndex(stockMesh.indices)

      const mat = new THREE.MeshStandardMaterial({
        color: 0x94a3b8,
        transparent: true,
        opacity: 0.18,
        roughness: 0.5,
        depthWrite: false,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.visible = showStock
      scene.add(mesh)
      stockObjectRef.current = mesh
    }
  }, [stockMesh, showStock])

  // Update Toolpaths
  useEffect(() => {
    const group = pathsGroupRef.current
    if (!group) return

    // Clear old lines
    while (group.children.length > 0) {
      const obj = group.children[0] as THREE.LineSegments
      group.remove(obj)
      obj.geometry.dispose()
    }

    if (waypoints.length < 2) return

    // Group segments into rapid (G0), feed (G1), arc (G2/G3)
    const rapidPts: number[] = []
    const feedPts: number[] = []
    const arcPts: number[] = []

    for (let i = 1; i < waypoints.length; i++) {
      const p0 = waypoints[i - 1]
      const p1 = waypoints[i]

      // Lathe Z -> 3D X, Lathe X (rad) -> 3D Y
      const x0 = p0.z, y0 = p0.x, z0 = 0
      const x1 = p1.z, y1 = p1.x, z1 = 0

      if (p1.mode === 'G0') {
        rapidPts.push(x0, y0, z0, x1, y1, z1)
      } else if (p1.mode === 'G2' || p1.mode === 'G3') {
        arcPts.push(x0, y0, z0, x1, y1, z1)
      } else {
        feedPts.push(x0, y0, z0, x1, y1, z1)
      }
    }

    if (rapidPts.length > 0 && showRapids) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(rapidPts, 3))
      const mat = new THREE.LineBasicMaterial({ color: 0xef4444, opacity: 0.8, transparent: true }) // Red
      group.add(new THREE.LineSegments(geo, mat))
    }

    if (feedPts.length > 0) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(feedPts, 3))
      const mat = new THREE.LineBasicMaterial({ color: 0x22c55e, linewidth: 2 }) // Green
      group.add(new THREE.LineSegments(geo, mat))
    }

    if (arcPts.length > 0) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(arcPts, 3))
      const mat = new THREE.LineBasicMaterial({ color: 0x06b6d4, linewidth: 2 }) // Cyan
      group.add(new THREE.LineSegments(geo, mat))
    }
  }, [waypoints, showRapids])

  // Update Dynamic Tool Position
  useEffect(() => {
    const tool = toolObjectRef.current
    if (!tool) return

    if (waypoints.length === 0 || activeWaypointIndex < 0 || activeWaypointIndex >= waypoints.length) {
      tool.visible = false
      return
    }

    const wp = waypoints[activeWaypointIndex]
    tool.visible = true
    // In our 3D space: Spindle Z is X axis, Radial X is Y axis
    tool.position.set(wp.z, wp.x, 0)
  }, [activeWaypointIndex, waypoints])

  // Camera presets
  const setCameraIso = () => {
    if (!cameraRef.current || !controlsRef.current) return
    cameraRef.current.position.set(-60, 50, 90)
    controlsRef.current.target.set(-20, 0, 0)
    controlsRef.current.update()
  }

  const setCameraZX = () => {
    if (!cameraRef.current || !controlsRef.current) return
    cameraRef.current.position.set(-20, 0, 120) // Normal to Z-X plane
    controlsRef.current.target.set(-20, 0, 0)
    controlsRef.current.update()
  }

  const resetView = () => {
    setCameraIso()
  }

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none touch-none">
      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing touch-none" />

      {/* Viewport Top HUD Controls */}
      <div className="absolute top-2 left-2 right-2 sm:right-auto flex items-center justify-between sm:justify-start gap-1 bg-slate-900/85 backdrop-blur-md px-2 py-1.5 rounded-lg border border-slate-700/60 shadow-lg text-xs text-slate-300">
        <button
          onClick={resetView}
          title="Reset View"
          className="p-1.5 hover:bg-slate-700/70 rounded transition"
        >
          <RotateCcw className="w-4 h-4 text-slate-300" />
        </button>
        <button
          onClick={setCameraIso}
          title="Isometric View"
          className="p-1.5 hover:bg-slate-700/70 rounded transition font-medium"
        >
          <Compass className="w-4 h-4 text-sky-400" />
        </button>
        <button
          onClick={setCameraZX}
          title="2D ZX Side Section"
          className="px-2 py-1 hover:bg-slate-700/70 rounded font-semibold text-sky-400 transition"
        >
          ZX
        </button>
        <div className="h-4 w-px bg-slate-700 mx-0.5" />
        <button
          onClick={onToggleCutaway}
          title="Toggle 3/4 Cutaway Revolve"
          className={`flex items-center gap-1 px-1.5 py-1 rounded transition ${
            cutaway ? 'bg-sky-600/30 text-sky-300 border border-sky-500/50' : 'hover:bg-slate-700/70'
          }`}
        >
          <Scissors className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Cutaway</span>
        </button>
        <button
          onClick={onToggleStock}
          title="Toggle Stock Cylinder Envelope"
          className={`flex items-center gap-1 px-1.5 py-1 rounded transition ${
            showStock ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50' : 'hover:bg-slate-700/70'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Stock</span>
        </button>
        <button
          onClick={onToggleRapids}
          title="Toggle Rapid (G0) Motion Lines"
          className={`flex items-center gap-1 px-1.5 py-1 rounded transition ${
            showRapids ? 'bg-red-600/30 text-red-300 border border-red-500/50' : 'hover:bg-slate-700/70'
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Rapids</span>
        </button>
      </div>

      {/* Axis legend */}
      <div className="hidden sm:block absolute bottom-3 right-3 bg-slate-900/70 backdrop-blur px-2.5 py-1 rounded border border-slate-800 text-[11px] text-slate-400 font-mono">
        Lathe Spindle Z (Longitudinal) | Radial X (Dia/Radius)
      </div>
    </div>
  )
}
