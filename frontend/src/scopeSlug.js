/**
 * Slug lookup for URL path scoping. Resolves org/competition slugs from organizations-graph.json.
 * Case-insensitive; hyphens and underscores are interchangeable (e.g. bend-fc, bend_fc, BEND-FC → Bend_FC).
 */

let _slugLookup = null

function _aliasKeys(slug) {
  const lower = (slug || '').toLowerCase()
  const keys = [lower]
  if (lower.includes('_')) keys.push(lower.replace(/_/g, '-'))
  if (lower.includes('-')) keys.push(lower.replace(/-/g, '_'))
  return [...new Set(keys)]
}

/**
 * Get the URL path slug for a node (Org ID or Competition ID).
 * Uses node.slug when present; for nwsc_payor with id "S5_-_WUFC" derives "WUFC".
 */
function _nodeSlug(node) {
  if (node.slug) return node.slug
  const id = node.id || ''
  const m = id.match(/^S5_-_(.+)$/)
  return m ? m[1] : id
}

/**
 * Build lookup map from organizations-graph.json nodes.
 * Uses slug (Org ID / Competition ID) for path resolution, not payor league labels.
 * @param {Array<{id: string, slug?: string, fullName?: string, type: string}>} nodes
 * @returns {Map<string, {canonicalSlug: string, fullName: string, type: string}>}
 */
export function buildSlugLookup(nodes) {
  const map = new Map()
  const relevant = (nodes || []).filter(
    (n) => n.type === 'organization' || n.type === 'competition'
  )
  for (const node of relevant) {
    const slug = _nodeSlug(node)
    if (!slug) continue
    const entry = {
      canonicalSlug: slug,
      fullName: node.fullName || node.label || slug,
      type: node.type,
    }
    for (const key of _aliasKeys(slug)) {
      map.set(key, entry)
    }
  }
  return map
}

/**
 * Fetch organizations-graph.json and build the slug lookup. Caches result.
 * @returns {Promise<Map<string, {canonicalSlug: string, fullName: string, type: string}>>}
 */
export async function getSlugLookup() {
  if (_slugLookup) return _slugLookup
  const res = await fetch('/organizations-graph.json')
  if (!res.ok) throw new Error('Failed to load organizations graph')
  const data = await res.json()
  _slugLookup = buildSlugLookup(data.nodes || [])
  return _slugLookup
}

/**
 * Resolve a URL path slug to org/competition metadata.
 * @param {string} input - Raw slug from URL (e.g. "bend-fc", "BEND_FC", "founders_cup")
 * @returns {Promise<{canonicalSlug: string, fullName: string, type: string} | null>}
 */
export async function resolveScopeSlug(input) {
  const trimmed = (input || '').trim()
  if (!trimmed) return null
  const lookup = await getSlugLookup()
  const key = trimmed.toLowerCase()
  const withHyphen = key.replace(/_/g, '-')
  const withUnderscore = key.replace(/-/g, '_')
  return lookup.get(key) ?? lookup.get(withHyphen) ?? lookup.get(withUnderscore) ?? null
}
