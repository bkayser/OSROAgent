import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  
  // License lookup state
  const [showEmailPrompt, setShowEmailPrompt] = useState(false)
  const [licenseEmail, setLicenseEmail] = useState('')
  const [licenseLoading, setLicenseLoading] = useState(false)

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
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
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

    setLicenseLoading(true)
    setShowEmailPrompt(false)

    // Add user message showing they entered email
    const userMessage = { role: 'user', content: `Look up licenses for: ${email}` }
    setMessages((prev) => [...prev, userMessage])

    try {
      const response = await fetch(
        `/api/license-status?email=${encodeURIComponent(email)}`,
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

  const handleSubmit = (e) => {
    e.preventDefault()
    submitQuestion(question)
  }

  const exampleQuestions = [
    "I'm a new ref. Where do I start?",
    'Check my license status',
    'Why am I not getting assignments?',
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-oregon-green text-white py-3 px-4 md:py-6 md:px-6 shadow-lg">
        <div className="max-w-4xl mx-auto flex justify-center">
          <div className="flex flex-row items-center gap-8">
            <img 
              src="/Logo_OSRO-alpha.png" 
              alt="Oregon Soccer Referee Organization" 
              className="h-20 shrink-0 hidden md:block"
            />
            <div className="text-left">
              <h1 className="text-2xl font-bold">Soccer Referee Concierge</h1>
              <p className="text-green-100 text-sm mt-1">
                Your AI assistant for soccer rules and referee procedures
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Area */}
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
                Ask me anything about being a soccer official in Oregon: IFAB and league rules, referee procedures, getting assignments, and using Reftown.
              </p>
              <div className="flex flex-col items-end gap-2 md:gap-3 max-w-md mx-auto">
                {exampleQuestions.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => submitQuestion(q)}
                    disabled={isLoading}
                    className="w-full max-w-[80%] text-left rounded-2xl rounded-br-md px-4 py-3 bg-oregon-green text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
                  >
                    <p className="whitespace-pre-wrap">{q}</p>
                  </button>
                ))}
              </div>
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
            placeholder="Ask about soccer rules, offside, fouls, or Oregon regulations..."
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

      {/* Footer */}
      <footer className="text-center text-gray-500 text-sm py-3 md:py-4 border-t border-gray-200">
        <p>Oregon Soccer Referee Concierge &copy; 2026</p>
      </footer>
    </div>
  )
}

export default App
