import { useState, useEffect, useRef, useMemo, useImperativeHandle, forwardRef } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import popper from 'cytoscape-popper'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'

cytoscape.use(popper)

const STYLESHEET = [
  {
    selector: 'node',
    style: {
      'label': 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': '11px',
      'color': '#1f2937',
      'text-max-width': '90px',
      'text-wrap': 'ellipsis',
    },
  },
  {
    selector: 'node[subtype="reftown_top"]',
    style: {
      'shape': 'rectangle',
      'background-color': '#166534',
      'color': '#fff',
      'width': '80px',
      'height': '40px',
    },
  },
  {
    selector: 'node[subtype="nwsc_parent"]',
    style: {
      'shape': 'rectangle',
      'background-color': '#14532d',
      'color': '#fff',
      'width': '100px',
      'height': '50px',
      'font-size': '12px',
    },
  },
  {
    selector: 'node[subtype="nwsc_payor"]',
    style: {
      'shape': 'round-rectangle',
      'background-color': '#15803d',
      'color': '#fff',
      'width': '90px',
      'height': '36px',
    },
  },
  {
    selector: 'node[subtype="league"]',
    style: {
      'shape': 'ellipse',
      'background-color': '#e5e7eb',
      'border-width': '1px',
      'border-color': '#9ca3af',
      'width': '70px',
      'height': '36px',
    },
  },
  {
    selector: 'node[subtype="tournament"]',
    style: {
      'shape': 'diamond',
      'background-color': '#e5e7eb',
      'border-width': '2px',
      'border-color': '#6b7280',
      'width': '52px',
      'height': '52px',
    },
  },
  {
    selector: 'edge[type="serves"]',
    style: {
      'width': 1,
      'line-color': '#6b7280',
      'target-arrow-color': '#6b7280',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
    },
  },
  {
    selector: 'edge[type="parent_of"]',
    style: {
      'width': 1.5,
      'line-color': '#166534',
      'line-style': 'dashed',
      'target-arrow-color': '#166534',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
    },
  },
]

const LAYOUT = {
  name: 'cose',
  animate: true,
  animationDuration: 500,
  nodeRepulsion: 10000,
  idealEdgeLength: 120,
  padding: 80,
  nodeDimensionsIncludeLabels: true,
}

function buildElements(graphData) {
  if (!graphData?.nodes?.length) return { nodes: [], edges: [] }
  const nodes = graphData.nodes.map((n) => ({
    group: 'nodes',
    data: {
      id: n.id,
      label: n.label,
      type: n.type,
      subtype: n.subtype,
      fullName: n.fullName ?? '',
      league: n.league ?? '',
      region: n.region ?? '',
      contact: n.contact ?? '',
    },
  }))
  const edges = (graphData.edges || []).map((e) => ({
    group: 'edges',
    data: {
      id: `${e.source}-${e.target}-${e.type}`,
      source: e.source,
      target: e.target,
      type: e.type || 'serves',
    },
  }))
  return [...nodes, ...edges]
}

function tooltipContent(node) {
  const d = node.data()
  const parts = []
  if (d.fullName) parts.push(`<strong>${escapeHtml(d.fullName)}</strong>`)
  if (d.league) parts.push(`League: ${escapeHtml(d.league)}`)
  if (d.region) parts.push(`Region: ${escapeHtml(d.region)}`)
  if (d.contact) parts.push(`Contact: ${escapeHtml(d.contact)}`)
  return parts.length ? parts.join('<br/>') : 'No details'
}

function escapeHtml(s) {
  const div = document.createElement('div')
  div.textContent = s
  return div.innerHTML
}

const OrganizationsGraph = forwardRef(function OrganizationsGraph(
  { graphData: propGraphData, onCyReady },
  ref
) {
  const cyRef = useRef(null)
  const [graphData, setGraphData] = useState(propGraphData ?? null)
  const [loading, setLoading] = useState(!propGraphData)
  const [error, setError] = useState(null)

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

  const elements = useMemo(() => buildElements(graphData), [graphData])
  const removeListenersRef = useRef(null)

  useImperativeHandle(ref, () => ({
    getCy: () => cyRef.current,
  }), [])

  const setupCy = (cy) => {
    cyRef.current = cy
    onCyReady?.(cy)
    removeListenersRef.current?.()
    let tipInstances = []
    const showTip = (evt) => {
      const node = evt.target
      if (!node.isNode()) return
      tipInstances.forEach((t) => t.destroy())
      tipInstances = []
      const dummy = document.createElement('div')
      const inst = tippy(dummy, {
        getReferenceClientRect: node.popperRef().getBoundingClientRect,
        trigger: 'manual',
        content: tooltipContent(node),
        allowHTML: true,
        theme: 'light',
        placement: 'top',
        arrow: true,
      })
      tipInstances.push(inst)
      inst.show()
    }
    const hideTip = () => {
      tipInstances.forEach((t) => t.destroy())
      tipInstances = []
    }
    const onTap = (evt) => {
      if (evt.target.isNode()) showTip(evt)
      else hideTip()
    }
    cy.on('mouseover', 'node', showTip)
    cy.on('tap', onTap)
    cy.on('mouseout', 'node', hideTip)
    removeListenersRef.current = () => {
      hideTip()
      cy.off('mouseover', 'node', showTip)
      cy.off('tap', onTap)
      cy.off('mouseout', 'node', hideTip)
    }
  }

  useEffect(() => {
    return () => removeListenersRef.current?.()
  }, [])

  if (loading) return <div className="p-8 text-gray-500">Loading graph…</div>
  if (error) return <div className="p-8 text-red-600">{error.message}</div>
  if (!elements.length) return <div className="p-8 text-gray-500">No graph data.</div>

  return (
    <div className="w-full h-full min-h-[400px]" style={{ height: '70vh' }}>
      <CytoscapeComponent
        cy={setupCy}
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={STYLESHEET}
        layout={LAYOUT}
      />
    </div>
  )
})

export default OrganizationsGraph
