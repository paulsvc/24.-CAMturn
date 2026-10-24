import { MeshData, ProjectState, SimulationWaypoint, LatheTool, OperationNode, Stock } from '../types'

const BASE_URL = '/api'

export async function fetchProject(): Promise<ProjectState> {
  const res = await fetch(`${BASE_URL}/project`)
  if (!res.ok) throw new Error('Failed to load project')
  return res.json()
}

export async function loadDemoProject(): Promise<ProjectState> {
  const res = await fetch(`${BASE_URL}/project/load_demo`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to load demo project')
  return res.json()
}

export async function recalculateProject(params: {
  name?: string
  stock?: Stock
  operations?: OperationNode[]
  tools?: LatheTool[]
  is_diameter_mode?: boolean
  post_dialect?: string
}): Promise<ProjectState> {
  const res = await fetch(`${BASE_URL}/project/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error('Failed to recalculate project')
  return res.json()
}

export async function addFaceOperation(faceId: string, opType: string): Promise<ProjectState> {
  const res = await fetch(`${BASE_URL}/project/face_operation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ face_id: faceId, op_type: opType }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to add face operation')
  }
  return res.json()
}

export async function uploadCAD(file: File): Promise<ProjectState> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE_URL}/cad/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to upload CAD file')
  }
  return res.json()
}

export async function fetchPartMesh(cutaway: boolean = true): Promise<MeshData> {
  const res = await fetch(`${BASE_URL}/project/mesh/part?cutaway=${cutaway}`)
  if (!res.ok) throw new Error('Failed to load part mesh')
  return res.json()
}

export async function fetchStockMesh(): Promise<MeshData> {
  const res = await fetch(`${BASE_URL}/project/mesh/stock`)
  if (!res.ok) throw new Error('Failed to load stock mesh')
  return res.json()
}

export async function fetchSimulationWaypoints(): Promise<SimulationWaypoint[]> {
  const res = await fetch(`${BASE_URL}/simulation/waypoints`)
  if (!res.ok) throw new Error('Failed to load simulation waypoints')
  return res.json()
}

export async function fetchISOPresets(): Promise<Record<string, any>> {
  const res = await fetch(`${BASE_URL}/tools/presets`)
  if (!res.ok) throw new Error('Failed to load ISO presets')
  return res.json()
}

export async function fetchISOShapeDescriptions(): Promise<Record<string, string>> {
  const res = await fetch(`${BASE_URL}/tools/iso_shapes`)
  if (!res.ok) throw new Error('Failed to load ISO shape descriptions')
  return res.json()
}
