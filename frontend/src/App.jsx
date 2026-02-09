import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return

    const userMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMessage])
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(
        `/api/chat?q=${encodeURIComponent(question)}`,
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-oregon-green text-white py-4 px-6 shadow-lg">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold">Oregon Soccer Referee Concierge</h1>
          <p className="text-green-100 text-sm mt-1">
            Your AI assistant for soccer rules and referee procedures
          </p>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <div className="text-6xl mb-4">⚽</div>
              <h2 className="text-xl font-semibold mb-2">Welcome!</h2>
              <p className="max-w-md mx-auto">
                Ask me anything about being a soccer official in Oregon: IFAB and league rules, referee procedures, getting assignments, and using Reftown.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
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
                        Sources: {message.sources.join(', ')}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {isLoading && (
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
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            className="bg-oregon-green hover:bg-green-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium transition-colors shadow-sm disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </main>

      {/* Footer */}
      <footer className="text-center text-gray-500 text-sm py-4 border-t border-gray-200">
        <p>Oregon Soccer Referee Concierge &copy; 2026</p>
      </footer>
    </div>
  )
}

export default App
