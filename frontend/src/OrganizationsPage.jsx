import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import OrganizationsGraph from './OrganizationsGraph.jsx'

const PROSE_CLASS =
  'prose prose-sm max-w-none prose-headings:text-gray-800 prose-h2:text-lg prose-h2:font-semibold prose-h2:text-oregon-green prose-h3:font-semibold prose-h3:mt-5 prose-h3:mb-2 prose-p:text-gray-600 prose-li:text-gray-600 prose-a:text-oregon-green prose-a:underline hover:prose-a:underline prose-strong:text-gray-700'

export default function OrganizationsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('list')
  const [listContent, setListContent] = useState('')
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState(null)
  const graphRef = useRef(null)

  useEffect(() => {
    setListLoading(true)
    setListError(null)
    fetch('/organizations.md')
      .then((res) => {
        if (!res.ok) throw new Error('Page not found')
        return res.text()
      })
      .then(setListContent)
      .catch(setListError)
      .finally(() => setListLoading(false))
  }, [])

  const handlePrint = useCallback(async () => {
    const dataUrl = await graphRef.current?.getPrintDataUrl?.()
    if (!dataUrl) return
    const w = window.open('', '_blank')
    if (!w) return
    w.document.write(`
      <!DOCTYPE html>
      <html>
        <head><title>Organizations Graph</title></head>
        <body style="margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;">
          <img src="${dataUrl}" alt="Organizations graph" style="max-width:100%;height:auto;" />
        </body>
      </html>
    `)
    w.document.close()
  }, [])

  return (
    <main className="flex-1 max-w-4xl w-full mx-auto p-4 md:p-6">
      <div className="mb-4">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-oregon-green hover:underline focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 rounded"
        >
          ← Chat
        </button>
      </div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">List of Organizations</h1>

      <div className="flex gap-1 mb-4 border-b border-gray-200">
        <button
          type="button"
          onClick={() => setTab('list')}
          className={`px-4 py-2 rounded-t-lg font-medium focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 ${
            tab === 'list'
              ? 'bg-oregon-green text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Org List
        </button>
        <button
          type="button"
          onClick={() => setTab('map')}
          className={`px-4 py-2 rounded-t-lg font-medium focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 ${
            tab === 'map'
              ? 'bg-oregon-green text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Org Map
        </button>
      </div>

      {tab === 'list' && (
        <>
          {listLoading && <p className="text-gray-500">Loading…</p>}
          {listError && <p className="text-red-600">Failed to load content.</p>}
          {!listLoading && !listError && listContent && (
            <div className={PROSE_CLASS}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                {listContent}
              </ReactMarkdown>
            </div>
          )}
        </>
      )}

      {tab === 'map' && (
        <div className="flex flex-col gap-3">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handlePrint}
              className="bg-oregon-green hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-2"
            >
              Print
            </button>
          </div>
          <OrganizationsGraph ref={graphRef} />
        </div>
      )}
    </main>
  )
}
