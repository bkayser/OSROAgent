import { useState, useEffect, useCallback, useRef } from 'react'
import { Routes, Route, Navigate, Outlet, useNavigate, useSearchParams, useLocation, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import OrganizationsPage from './OrganizationsPage.jsx'

// Beta Splash Screen Component
function BetaSplash({ onDismiss, content }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="p-6 md:p-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-200">
            <span className="text-3xl">⚽</span>
            <div>
              <span className="bg-yellow-100 text-yellow-800 text-xs font-semibold px-2.5 py-0.5 rounded-full">
                BETA
              </span>
              <h2 className="text-xl font-bold text-gray-800 mt-1">
                Welcome, Administrators & Assignors
              </h2>
            </div>
          </div>

          {/* Content - rendered from markdown */}
          <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-h2:text-lg prose-h2:font-semibold prose-h2:text-oregon-green prose-h3:font-semibold prose-h3:mt-5 prose-h3:mb-2 prose-p:text-gray-600 prose-li:text-gray-600 prose-a:text-oregon-green prose-a:no-underline hover:prose-a:underline prose-strong:text-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>

          {/* Dismiss Button */}
          <div className="mt-8 flex justify-center">
            <button
              onClick={onDismiss}
              className="bg-oregon-green hover:bg-green-700 text-white px-8 py-3 rounded-xl font-semibold transition-colors shadow-md"
            >
              Got it, let's go!
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Reusable markdown page: fetches /{slug}.md and renders with prose styling
function MarkdownPage({ slug, title }) {
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`/${slug}.md`)
      .then((res) => {
        if (!res.ok) throw new Error('Page not found')
        return res.text()
      })
      .then(setContent)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [slug])

  const linkStyle = slug === 'organizations'
    ? 'prose-a:text-oregon-green prose-a:underline hover:prose-a:underline'
    : 'prose-a:text-oregon-green prose-a:no-underline hover:prose-a:underline'
  const proseClass = `prose prose-sm max-w-none prose-headings:text-gray-800 prose-h2:text-lg prose-h2:font-semibold prose-h2:text-oregon-green prose-h3:font-semibold prose-h3:mt-5 prose-h3:mb-2 prose-p:text-gray-600 prose-li:text-gray-600 ${linkStyle} prose-strong:text-gray-700`
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
      {loading && <p className="text-gray-500">Loading…</p>}
      {error && <p className="text-red-600">Failed to load content.</p>}
      {!loading && !error && content && (
        <div className={proseClass}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>{content}</ReactMarkdown>
        </div>
      )}
    </main>
  )
}

// Sample questions page: clickable questions that navigate to chat and auto-submit
function SampleQuestionsPage() {
  const navigate = useNavigate()
  const [sections, setSections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch('/sample-questions.json')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load questions')
        return res.json()
      })
      .then(setSections)
      .catch(setError)
      .finally(() => setLoading(false))
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
      <h1 className="text-2xl font-bold text-gray-800 mb-2">Sample questions</h1>
      <p className="text-gray-600 mb-6">
        Click any question to ask it in the chat. The prompt will be sent automatically.
      </p>
      {loading && <p className="text-gray-500">Loading…</p>}
      {error && <p className="text-red-600">Failed to load sample questions.</p>}
      {!loading && !error && sections.map(({ section, questions }) => (
        <section key={section} className="mb-6">
          <h2 className="text-lg font-semibold text-oregon-green mb-3">{section}</h2>
          <ul className="space-y-2">
            {questions.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => navigate('/', { state: { submitQuestion: q } })}
                  className="w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 bg-white hover:bg-oregon-green hover:text-white hover:border-oregon-green focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-2 transition-colors group"
                >
                  <span className="flex-1">{q}</span>
                  <span className="shrink-0 text-sm font-medium text-oregon-green group-hover:text-white flex items-center gap-1">
                    Ask in chat
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {!loading && !error && sections.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-oregon-green mb-3">Other languages</h2>
          <ul className="space-y-2">
            {[
              { lang: 'Español', q: '¿Cómo me certifico para ser árbitro?' },
              { lang: 'Русский', q: 'Как мне получить сертификат судьи?' },
              { lang: 'Tiếng Việt', q: 'Làm thế nào để tôi được cấp chứng chỉ trọng tài?' },
              { lang: '中文', q: '如何获得裁判员认证？' },
              { lang: '한국어', q: '어떻게 심판 자격을 취득하나요?' },
            ].map(({ lang, q }) => (
              <li key={lang}>
                <button
                  type="button"
                  onClick={() => navigate('/', { state: { submitQuestion: q } })}
                  className="w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 bg-white hover:bg-oregon-green hover:text-white hover:border-oregon-green focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-2 transition-colors group"
                >
                  <span className="flex-1">{q}</span>
                  <span className="shrink-0 text-sm text-gray-500 group-hover:text-white">{lang}</span>
                  <span className="shrink-0 text-sm font-medium text-oregon-green group-hover:text-white flex items-center gap-1">
                    Ask in chat
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="text-sm text-gray-500 mt-6">
        Or use <strong>Look up License Info</strong> in the menu to check your USSF license status.
      </p>
    </main>
  )
}

// Keywords that trigger license lookup flow
const LICENSE_KEYWORDS = [
  'license', 'licenses', 'certification', 'certifications', 
  'credentials', 'ussf', 'my license', 'my certification',
  'check my', 'look up my', 'status'
]

function isLicenseQuery(text) {
  const lower = text.toLowerCase()
  return LICENSE_KEYWORDS.some(keyword => lower.includes(keyword))
}

// License Card Component
function LicenseCard({ discipline, licenses }) {
  const disciplineLabels = {
    referee: 'Referee',
    coach: 'Coach', 
    safety: 'Safety & Compliance'
  }

  const statusColors = {
    active: 'bg-green-100 text-green-800',
    expiring_soon: 'bg-yellow-100 text-yellow-800',
    critical: 'bg-orange-100 text-orange-800 font-semibold',
    expired: 'bg-red-100 text-red-800'
  }

  const statusLabels = {
    active: 'Active',
    expiring_soon: 'Expiring Soon',
    critical: 'Expires Very Soon!',
    expired: 'Expired'
  }

  return (
    <div className="bg-gray-50 rounded-lg p-3 mb-2">
      <h4 className="font-semibold text-gray-700 mb-2 capitalize">
        {disciplineLabels[discipline] || discipline}
      </h4>
      <div className="space-y-2">
        {licenses.map((lic, idx) => (
          <div key={idx} className="bg-white rounded p-2 border border-gray-200">
            <div className="flex justify-between items-start gap-2">
              <span className="font-medium text-sm">{lic.name}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[lic.status] || statusColors.active}`}>
                {statusLabels[lic.status] || 'Active'}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {lic.issuer && <div>Issued by: {lic.issuer}</div>}
              {lic.issue_date && <div>Issued: {lic.issue_date}</div>}
              {lic.expiration_date && (
                <div className={
                  lic.status === 'critical' ? 'text-orange-700 font-semibold' :
                  lic.status === 'expiring_soon' ? 'text-yellow-700' :
                  lic.status === 'expired' ? 'text-red-700' : ''
                }>
                  Expires: {lic.expiration_date}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// License Display Component
function LicenseDisplay({ data }) {
  if (!data) return null

  const { full_name, licenses } = data
  const disciplineOrder = ['referee', 'coach', 'safety']
  const sortedDisciplines = Object.keys(licenses).sort(
    (a, b) => disciplineOrder.indexOf(a) - disciplineOrder.indexOf(b)
  )

  return (
    <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-md border border-gray-100 max-w-[80%]">
      <h3 className="font-bold text-lg text-gray-800 mb-3">
        License Status for {full_name}
      </h3>
      {sortedDisciplines.length === 0 ? (
        <p className="text-gray-600">No active licenses found.</p>
      ) : (
        sortedDisciplines.map(discipline => (
          <LicenseCard 
            key={discipline} 
            discipline={discipline} 
            licenses={licenses[discipline]} 
          />
        ))
      )}
    </div>
  )
}

// Layout: header (hamburger right), drawer, footer, feedback modal, outlet
function Layout() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [feedbackName, setFeedbackName] = useState('')
  const [feedbackDescription, setFeedbackDescription] = useState('')
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackSuccess, setFeedbackSuccess] = useState(false)

  const openFeedbackModal = useCallback(() => {
    setFeedbackSuccess(false)
    setFeedbackName('')
    setFeedbackDescription('')
    setShowFeedbackModal(true)
  }, [])
  const closeFeedbackModal = useCallback(() => {
    setShowFeedbackModal(false)
    setFeedbackSubmitting(false)
  }, [])

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault()
    const description = feedbackDescription.trim()
    if (!description || feedbackSubmitting) return
    setFeedbackSubmitting(true)
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: feedbackName.trim() || null,
          description,
        }),
      })
      if (!res.ok) throw new Error(res.statusText)
      setFeedbackSuccess(true)
      setFeedbackDescription('')
      setFeedbackName('')
      setTimeout(() => closeFeedbackModal(), 1500)
    } catch (err) {
      console.error('Feedback submit failed:', err)
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    if (menuOpen) {
      window.addEventListener('keydown', onKeyDown)
      return () => window.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen])

  const menuItems = [
    { label: 'Chat', action: () => { navigate('/'); setMenuOpen(false) } },
    { label: 'Look up License Info', action: () => { navigate('/?license=1'); setMenuOpen(false) } },
    { label: 'Sample questions', action: () => { navigate('/sample-questions'); setMenuOpen(false) } },
    { label: 'List of Organizations', action: () => { navigate('/organizations'); setMenuOpen(false) } },
    { label: 'For Assignors', action: () => { navigate('/for-assignors'); setMenuOpen(false) } },
    { label: 'About', action: () => { navigate('/about'); setMenuOpen(false) } },
    { label: 'Feedback and Corrections', action: () => { openFeedbackModal(); setMenuOpen(false) } },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-oregon-green text-white py-3 px-4 md:py-6 md:px-6 shadow-lg">
        <div className="max-w-4xl mx-auto flex flex-row items-center justify-between gap-4">
          <div className="flex flex-row items-center gap-8 min-w-0">
            <img
              src="/Logo_OSRO-alpha.png"
              alt="Oregon Soccer Referee Organization"
              className="h-20 shrink-0 hidden md:block"
            />
            <div className="text-left min-w-0">
              <h1 className="text-2xl font-bold">Soccer Referee Concierge</h1>
              <p className="text-green-100 text-sm mt-1">
                Your AI assistant for soccer rules and referee procedures
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            className="shrink-0 p-1.5 rounded-lg hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Open menu"
          >
            <svg className="w-8 h-8 md:w-10 md:h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </header>

      {menuOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            aria-hidden="true"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed top-0 right-0 bottom-0 w-full max-w-xs bg-white shadow-xl z-50 flex flex-col p-4">
            <div className="flex justify-between items-center mb-4">
              <span className="font-semibold text-gray-800">Menu</span>
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="p-2 rounded-lg hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-oregon-green"
                aria-label="Close menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"> <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /> </svg>
              </button>
            </div>
            <nav className="flex flex-col gap-1">
              {menuItems.map(({ label, action }) => (
                <button
                  key={label}
                  type="button"
                  onClick={action}
                  className="text-left px-3 py-2.5 rounded-lg text-gray-700 hover:bg-gray-100 hover:text-oregon-green focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-inset"
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>
        </>
      )}

      <Outlet />

      <footer className="text-center text-gray-500 text-sm py-3 md:py-4 border-t border-gray-200 mt-auto">
        <p className="mb-2">Oregon Soccer Referee Concierge &copy; 2026</p>
        <button
          type="button"
          onClick={openFeedbackModal}
          className="text-oregon-green hover:underline focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 rounded"
        >
          Submit feedback
        </button>
      </footer>

      {showFeedbackModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl">
            <div className="p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-1">Submit feedback</h2>
              <p className="text-sm text-gray-500 mb-4">
                Tell us what information is missing or incorrect so we can improve.
              </p>
              {feedbackSuccess ? (
                <p className="text-oregon-green font-medium py-4">Thank you — your feedback has been submitted.</p>
              ) : (
                <form onSubmit={handleFeedbackSubmit} className="flex flex-col gap-3">
                  <div>
                    <label htmlFor="feedback-name" className="block text-sm font-medium text-gray-700 mb-1">
                      Name <span className="text-gray-400">(optional)</span>
                    </label>
                    <input
                      id="feedback-name"
                      type="text"
                      value={feedbackName}
                      onChange={(e) => setFeedbackName(e.target.value)}
                      placeholder="Your name"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-oregon-green focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label htmlFor="feedback-description" className="block text-sm font-medium text-gray-700 mb-1">
                      What's missing or incorrect?
                    </label>
                    <textarea
                      id="feedback-description"
                      value={feedbackDescription}
                      onChange={(e) => setFeedbackDescription(e.target.value)}
                      placeholder="Describe what information is missing or incorrect..."
                      rows={4}
                      required
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-oregon-green focus:border-transparent resize-y"
                    />
                  </div>
                  <div className="flex gap-2 justify-end pt-1">
                    <button
                      type="button"
                      onClick={closeFeedbackModal}
                      className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={feedbackSubmitting || !feedbackDescription.trim()}
                      className="bg-oregon-green hover:bg-green-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
                    >
                      {feedbackSubmitting ? 'Submitting…' : 'Submit'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ChatView() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [showEmailPrompt, setShowEmailPrompt] = useState(false)
  const [licenseEmail, setLicenseEmail] = useState('')
  const [licenseLoading, setLicenseLoading] = useState(false)
  const [showBetaSplash, setShowBetaSplash] = useState(false)
  const [betaContent, setBetaContent] = useState('')
  const [gradesByLogId, setGradesByLogId] = useState({})
  const [gradingLogId, setGradingLogId] = useState(null)
  const [gradeError, setGradeError] = useState(null)

  // When navigated with ?license=1, show license prompt once then clear param
  useEffect(() => {
    if (searchParams.get('license') === '1') {
      setShowEmailPrompt(true)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const submittedFromStateRef = useRef(false)
  // When navigated from Sample questions with state.submitQuestion, load and send it
  useEffect(() => {
    const q = location.state?.submitQuestion
    if (q && typeof q === 'string' && !submittedFromStateRef.current) {
      submittedFromStateRef.current = true
      navigate('/', { replace: true, state: {} })
      submitQuestion(q)
    }
  }, [location.state?.submitQuestion, navigate])

  useEffect(() => {
    const dismissed = localStorage.getItem('betaSplashDismissed')
    if (!dismissed) {
      fetch('/beta.md')
        .then(res => res.text())
        .then(text => {
          setBetaContent(text)
          setShowBetaSplash(true)
        })
        .catch(err => console.error('Failed to load beta.md:', err))
    }
  }, [])

  const dismissBetaSplash = () => {
    localStorage.setItem('betaSplashDismissed', 'true')
    setShowBetaSplash(false)
  }

  const submitQuestion = async (text) => {
    const q = (typeof text === 'string' ? text : question).trim()
    if (!q || isLoading || licenseLoading) return

    // Check if this is a license-related query
    if (isLicenseQuery(q)) {
      const userMessage = { role: 'user', content: q }
      setMessages((prev) => [...prev, userMessage])
      setQuestion('')
      setShowEmailPrompt(true)
      return
    }

    const userMessage = { role: 'user', content: q }
    setMessages((prev) => [...prev, userMessage])
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(
        `/api/chat?q=${encodeURIComponent(q)}`,
        { method: 'GET' }
      )

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to get response')
      }

      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        logId: data.log_id ?? null,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: error.message || 'Sorry, there was an error processing your request. Please try again.',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleLicenseLookup = async (e) => {
    e.preventDefault()
    const email = licenseEmail.trim()
    if (!email || licenseLoading) return

    // Triggering query: the user message that led to the license prompt (empty if from menu)
    const lastUser = messages[messages.length - 1]
    const triggerQuery = lastUser?.role === 'user' ? lastUser.content : ''

    setLicenseLoading(true)
    setShowEmailPrompt(false)

    // Add user message showing they entered email
    const userMessage = { role: 'user', content: `Look up licenses for: ${email}` }
    setMessages((prev) => [...prev, userMessage])

    const params = new URLSearchParams({ email })
    if (triggerQuery) params.set('trigger_query', triggerQuery)

    try {
      const response = await fetch(
        `/api/license-status?${params.toString()}`,
        { method: 'GET' }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to look up license')
      }

      const data = await response.json()
      const licenseMessage = {
        role: 'assistant',
        type: 'license',
        licenseData: data,
      }
      setMessages((prev) => [...prev, licenseMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `Sorry, I couldn't find license information: ${error.message}`,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLicenseLoading(false)
      setLicenseEmail('')
    }
  }

  const cancelLicenseLookup = () => {
    setShowEmailPrompt(false)
    setLicenseEmail('')
  }

  const skipLicenseLookup = async () => {
    const lastMsg = messages[messages.length - 1]
    const query = lastMsg?.role === 'user' ? lastMsg.content : ''
    if (!query || isLoading || licenseLoading) return
    setShowEmailPrompt(false)
    setLicenseEmail('')
    setIsLoading(true)
    try {
      const response = await fetch(
        `/api/chat?q=${encodeURIComponent(query)}`,
        { method: 'GET' }
      )
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to get response')
      }
      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        logId: data.log_id ?? null,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: error.message || 'Sorry, there was an error processing your request. Please try again.',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    submitQuestion(question)
  }

  const handleGrade = async (logId, grade) => {
    if (!logId || gradingLogId) return
    setGradingLogId(logId)
    setGradeError(null)
    const prevGrade = gradesByLogId[logId]
    setGradesByLogId((g) => ({ ...g, [logId]: grade }))
    try {
      const res = await fetch('/api/chat/grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_id: logId, grade }),
      })
      if (!res.ok) throw new Error(res.status === 404 ? 'Log entry not found' : 'Failed to save grade')
    } catch (err) {
      setGradesByLogId((g) => ({ ...g, [logId]: prevGrade }))
      setGradeError({ logId, message: err.message })
    } finally {
      setGradingLogId(null)
    }
  }

  return (
    <>
      {showBetaSplash && <BetaSplash onDismiss={dismissBetaSplash} content={betaContent} />}
      <main className="flex-1 max-w-4xl w-full mx-auto p-2 md:p-4 flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-3 mb-3 md:space-y-4 md:mb-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-2 md:mt-20">
              <div className="mb-2 md:mb-4 flex justify-center">
                <img
                  src="/OSRO_Site_Logo_About-300x126.png"
                  alt="OSRO"
                  className="h-24 w-auto md:hidden"
                />
                <span className="text-6xl hidden md:inline">⚽</span>
              </div>
              <h2 className="text-xl font-semibold mb-1 md:mb-2">Welcome!</h2>
              <p className="max-w-md mx-auto mb-3 md:mb-6">
                Ask about Oregon soccer officiating: IFAB and league rules, procedures, getting assignments, and Reftown. Include the organization or league name when your question is specific to one.
              </p>
              <p className="max-w-md mx-auto mb-4">
                <Link
                  to="/sample-questions"
                  className="text-oregon-green hover:underline focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 rounded font-medium"
                >
                  Sample questions
                </Link>
              </p>
              <p className="max-w-md mx-auto text-sm italic text-gray-400">
                I understand Español, Русский, Tiếng Việt, and 中文.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {/* License display message */}
                {message.type === 'license' ? (
                  <LicenseDisplay data={message.licenseData} />
                ) : (
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-oregon-green text-white rounded-br-md'
                        : 'bg-white text-gray-800 shadow-md rounded-bl-md border border-gray-100'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-pre:bg-gray-800 prose-pre:text-gray-100 prose-code:text-oregon-green prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <p className="text-xs text-gray-500">
                          Sources:{' '}
                          {message.sources.map((source, idx) => (
                            <span key={idx}>
                              {idx > 0 && ', '}
                              {source.startsWith('http://') || source.startsWith('https://') ? (
                                <a 
                                  href={source} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="text-gray-500 underline hover:text-gray-700"
                                >
                                  {source.replace(/^https?:\/\//, '').split('/')[0]}
                                </a>
                              ) : (
                                source
                              )}
                            </span>
                          ))}
                        </p>
                      </div>
                    )}
                    {message.logId && (
                      <div className="mt-2 pt-2 flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleGrade(message.logId, 'up')}
                          disabled={gradingLogId === message.logId}
                          title="Helpful"
                          className={`p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 disabled:opacity-50 ${
                            gradesByLogId[message.logId] === 'up'
                              ? 'bg-oregon-green/15 shadow-inner text-oregon-green'
                              : 'hover:bg-gray-100 text-gray-400'
                          }`}
                          aria-label="Thumbs up"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleGrade(message.logId, 'down')}
                          disabled={gradingLogId === message.logId}
                          title="Not helpful"
                          className={`p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-oregon-green focus:ring-offset-1 disabled:opacity-50 ${
                            gradesByLogId[message.logId] === 'down'
                              ? 'bg-gray-200 shadow-inner text-gray-600'
                              : 'hover:bg-gray-100 text-gray-400'
                          }`}
                          aria-label="Thumbs down"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2M5 4a2 2 0 00-2 2v6a2 2 0 002 2h2" />
                          </svg>
                        </button>
                        {gradeError?.logId === message.logId && (
                          <span className="text-xs text-red-600 ml-1">{gradeError.message}</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
          {/* Email Prompt for License Lookup */}
          {showEmailPrompt && (
            <div className="flex justify-start">
              <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-md border border-gray-100 max-w-[80%]">
                <p className="text-gray-800 mb-3">
                  I can look up your USSF license status. Please enter the email address associated with your US Soccer account:
                </p>
                <form onSubmit={handleLicenseLookup} className="flex flex-col gap-2">
                  <input
                    type="email"
                    value={licenseEmail}
                    onChange={(e) => setLicenseEmail(e.target.value)}
                    placeholder="your.email@example.com"
                    className="rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-oregon-green focus:border-transparent"
                    autoFocus
                    required
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      className="bg-oregon-green hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                      Look Up
                    </button>
                    <button
                      type="button"
                      onClick={skipLicenseLookup}
                      className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                      Skip
                    </button>
                    <button
                      type="button"
                      onClick={cancelLicenseLookup}
                      className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
          {/* Loading indicator */}
          {(isLoading || licenseLoading) && (
            <div className="flex justify-start">
              <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-md border border-gray-100">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about league rules, using Reftown, assignments, certification, and more..."
            className="flex-1 rounded-xl border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-oregon-green focus:border-transparent shadow-sm"
            disabled={isLoading || licenseLoading || showEmailPrompt}
          />
          <button
            type="submit"
            disabled={isLoading || licenseLoading || showEmailPrompt || !question.trim()}
            className="bg-oregon-green hover:bg-green-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium transition-colors shadow-sm disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </main>
    </>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ChatView />} />
        <Route path="/license" element={<Navigate to="/?license=1" replace />} />
        <Route path="/about" element={<MarkdownPage slug="about" title="About" />} />
        <Route path="/for-assignors" element={<MarkdownPage slug="for-assignors" title="For Assignors" />} />
        <Route path="/organizations" element={<OrganizationsPage />} />
        <Route path="/sample-questions" element={<SampleQuestionsPage />} />
      </Route>
    </Routes>
  )
}

export default App
