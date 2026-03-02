import { useState, useEffect, useMemo, useCallback, useRef, useImperativeHandle, forwardRef } from 'react'
import { Link } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  Handle,
  Position,
} from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import { toPng } from 'html-to-image'
import '@xyflow/react/dist/style.css'

const NODE_WIDTH = 120
const NODE_HEIGHT = 44

function getLayoutedElements(nodes, edges, direction = 'LR') {
  const isHorizontal = direction === 'LR'
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 70,
    ranker: 'longest-path',
    align: 'UL',
  })

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  return {
    nodes: nodes.map((node) => {
      const nodeWithPosition = g.node(node.id)
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - NODE_WIDTH / 2,
          y: nodeWithPosition.y - NODE_HEIGHT / 2,
        },
        sourcePosition: isHorizontal ? 'right' : 'bottom',
        targetPosition: isHorizontal ? 'left' : 'top',
      }
    }),
    edges,
  }
}

function SlugNodeBase({ data, className, children }) {
  return (
    <div
      className={`relative flex items-center justify-center px-2 py-1.5 text-center text-xs font-medium text-gray-800 ${className}`}
      style={{ minWidth: 80, minHeight: 32, cursor: 'pointer' }}
    >
      <Handle type="target" position={Position.Left} />
      {children ?? (data.label ?? data.id)}
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function RefTownOrgNode({ data }) {
  return (
    <SlugNodeBase
      data={data}
      className="rounded bg-[#166534] text-white shadow"
    />
  )
}

function NWSCParentNode({ data }) {
  return (
    <SlugNodeBase
      data={data}
      className="rounded bg-[#14532d] text-white shadow-md"
    />
  )
}

function NWSCPayorNode({ data }) {
  return (
    <SlugNodeBase
      data={data}
      className="rounded-lg bg-[#15803d] text-white shadow"
    />
  )
}

function LeagueNode({ data }) {
  return (
    <SlugNodeBase
      data={data}
      className="rounded-full border border-gray-400 bg-gray-200"
    />
  )
}

function TournamentNode({ data }) {
  return (
    <SlugNodeBase
      data={data}
      className="rotate-45 rounded border-2 border-gray-500 bg-gray-200 text-gray-800"
    >
      <span className="-rotate-45 block truncate max-w-[70px]">
        {data.label ?? data.id}
      </span>
    </SlugNodeBase>
  )
}

function DefaultNode({ data }) {
  return <SlugNodeBase data={data} className="rounded border border-gray-300 bg-gray-100" />
}

const nodeTypes = {
  default: DefaultNode,
  reftown_top: RefTownOrgNode,
  nwsc_parent: NWSCParentNode,
  nwsc_payor: NWSCPayorNode,
  league: LeagueNode,
  tournament: TournamentNode,
}

function formatList(val) {
  if (!val || !String(val).trim()) return ''
  return String(val)
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .join(', ')
}

function NodePopup({ node, onClose }) {
  if (!node?.data) return null
  const d = node.data
  const fullName = d.fullName ?? d.label ?? d.id
  const league = formatList(d.league)
  const region = formatList(d.region)
  const contact = formatList(d.contact)
  const homepage = d.homepage ? String(d.homepage).trim() : ''

  return (
    <div
      className="absolute z-10 max-w-[30rem] rounded-lg border border-gray-200 bg-white px-3 py-2 text-left shadow-lg"
      role="dialog"
      aria-label="Organization details"
    >
      <div className="space-y-1 text-sm">
        <div className="font-semibold text-gray-900">{fullName}</div>
        {league && <div><span className="text-gray-500">League:</span> {league}</div>}
        {region && <div><span className="text-gray-500">Region:</span> {region}</div>}
        {contact && <div><span className="text-gray-500">Contact:</span> {contact}</div>}
        {homepage && (
          <div>
            <span className="text-gray-500">Homepage:</span>{' '}
            <a href={homepage} target="_blank" rel="noopener noreferrer" className="text-oregon-green hover:underline">
              {homepage.replace(/^https?:\/\//, '').split('/')[0]}
            </a>
          </div>
        )}
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Link
          to={`/${d.slug ?? (d.id?.match(/^S5_-_(.+)$/)?.[1] ?? d.id)}`}
          className="text-xs font-medium text-oregon-green hover:underline"
        >
          Ask about {fullName}
        </Link>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-gray-500 hover:underline"
          aria-label="Close"
        >
          Close
        </button>
      </div>
    </div>
  )
}

function graphJsonToFlow(rawNodes, rawEdges) {
  const flowNodes = (rawNodes || []).map((n) => ({
    id: n.id,
    type: n.subtype || n.type || 'default',
    data: {
      ...n,
      label: n.label ?? n.id,
    },
    position: { x: 0, y: 0 },
  }))

  const flowEdges = (rawEdges || []).map((e, i) => ({
    id: e.id ?? `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    animated: e.type === 'parent_of',
    style: e.type === 'parent_of'
      ? { stroke: '#166534', strokeWidth: 2, strokeDasharray: '5,5' }
      : { stroke: '#6b7280', strokeWidth: 2 },
  }))

  return { flowNodes, flowEdges }
}

function OrganizationsGraphInner({ graphData: propGraphData, containerRef, onPrintReady }) {
  const [graphData, setGraphData] = useState(propGraphData ?? null)
  const [loading, setLoading] = useState(!propGraphData)
  const [error, setError] = useState(null)
  const [popupNode, setPopupNode] = useState(null)

  const { flowNodes: initialFlowNodes, flowEdges: initialFlowEdges } = useMemo(
    () => (graphData ? graphJsonToFlow(graphData.nodes, graphData.edges) : { flowNodes: [], flowEdges: [] }),
    [graphData]
  )

  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    if (!initialFlowNodes.length) return { nodes: [], edges: [] }
    return getLayoutedElements(initialFlowNodes, initialFlowEdges, 'LR')
  }, [initialFlowNodes, initialFlowEdges])

  useEffect(() => {
    if (propGraphData) {
      setGraphData(propGraphData)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    fetch('/organizations-graph.json')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load graph data')
        return res.json()
      })
      .then(setGraphData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [propGraphData])

  const hasLayoutedData = layoutedNodes.length > 0
  if (loading) return <div className="p-8 text-gray-500">Loading graph…</div>
  if (error) return <div className="p-8 text-red-600">{error.message}</div>
  if (!hasLayoutedData) return <div className="p-8 text-gray-500">No graph data.</div>

  return (
    <OrganizationsFlow
      key="org-flow"
      layoutedNodes={layoutedNodes}
      layoutedEdges={layoutedEdges}
      containerRef={containerRef}
      onPrintReady={onPrintReady}
    />
  )
}

function OrganizationsFlow({
  layoutedNodes,
  layoutedEdges,
  containerRef,
  onPrintReady,
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)
  const [pinnedNodeId, setPinnedNodeId] = useState(null)

  const displayNode = pinnedNodeId
    ? nodes.find((n) => n.id === pinnedNodeId) ?? null
    : null

  const onNodeClick = useCallback((_evt, node) => {
    setPinnedNodeId((prev) => (prev === node.id ? null : node.id))
  }, [])

  useEffect(() => {
    if (!containerRef?.current || !onPrintReady) return
    onPrintReady({
      getPrintDataUrl: async () => {
        setPinnedNodeId(null)
        await new Promise((r) => setTimeout(r, 150))
        if (!containerRef.current) return null
        return toPng(containerRef.current, { pixelRatio: 2 })
      },
    })
  }, [containerRef, onPrintReady, layoutedNodes.length])

  return (
    <div ref={containerRef} className="relative w-full min-h-[400px]" style={{ height: '70vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{ type: 'smoothstep', style: { strokeWidth: 2 } }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        onNodeClick={onNodeClick}
        panOnDrag
        zoomOnScroll
        nodesDraggable
        elementsSelectable
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const s = node.type
            if (s === 'nwsc_parent') return '#14532d'
            if (s === 'nwsc_payor') return '#15803d'
            if (s === 'reftown_top') return '#166534'
            return '#9ca3af'
          }}
        />
      </ReactFlow>
      {displayNode && (
        <div
          className="pointer-events-auto absolute left-4 top-4"
          style={{ transform: `translate(0, 0)` }}
        >
          <NodePopup
            node={displayNode}
            onClose={() => setPinnedNodeId(null)}
          />
        </div>
      )}
    </div>
  )
}

const OrganizationsGraph = forwardRef(function OrganizationsGraph(
  { graphData, onPrintReady },
  ref
) {
  const containerRef = useRef(null)
  const printApiRef = useRef(null)

  useImperativeHandle(
    ref,
    () => ({
      getPrintDataUrl: () => printApiRef.current?.getPrintDataUrl?.() ?? Promise.resolve(null),
    }),
    []
  )

  const handlePrintReady = useCallback((api) => {
    printApiRef.current = api
  }, [])

  return (
    <ReactFlowProvider>
      <OrganizationsGraphInner
        graphData={graphData}
        containerRef={containerRef}
        onPrintReady={handlePrintReady}
      />
    </ReactFlowProvider>
  )
})

export default OrganizationsGraph
