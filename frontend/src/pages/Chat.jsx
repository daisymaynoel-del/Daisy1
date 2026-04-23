import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Bot, User, Trash2, Settings2, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import ReactMarkdown from 'react-markdown'

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-brand-500' : 'bg-charcoal-800'
      }`}>
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-white" />}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
        isUser
          ? 'bg-brand-500 text-white rounded-tr-sm'
          : 'bg-white border border-charcoal-100 text-charcoal-800 rounded-tl-sm'
      }`}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

function BriefPanel({ brief, onClose }) {
  if (!brief) return null
  return (
    <div className="absolute right-0 top-0 bottom-0 w-72 bg-white border-l border-charcoal-100 p-4 overflow-y-auto z-10">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm text-charcoal-900">Active Creative Brief</h3>
        <button onClick={onClose} className="text-charcoal-400 hover:text-charcoal-600 text-xs">Close</button>
      </div>
      <div className="space-y-3 text-sm">
        {[
          ['Platform', brief.platform],
          ['Video Length', brief.video_length_seconds ? `${brief.video_length_seconds}s` : '—'],
          ['Hook Style', brief.hook_style],
          ['Music', brief.music_preference],
          ['Tone', brief.tone],
          ['Pillar', brief.content_pillar],
          ['CTA', brief.cta],
        ].map(([label, val]) => val && (
          <div key={label}>
            <p className="text-xs text-charcoal-400 font-medium">{label}</p>
            <p className="text-charcoal-800 capitalize">{val}</p>
          </div>
        ))}
        {brief.special_instructions && (
          <div>
            <p className="text-xs text-charcoal-400 font-medium">Special Instructions</p>
            <p className="text-charcoal-700 text-xs leading-relaxed">{brief.special_instructions}</p>
          </div>
        )}
      </div>
    </div>
  )
}

const QUICK_PROMPTS = [
  "Make all videos 15 seconds with a before/after hook",
  "Use trending pop music for every video",
  "Focus on transformation content this week",
  "Always start with a question hook",
  "What's performing best this week?",
  "Suggest 3 posts for today",
]

export default function Chat() {
  const [input, setInput] = useState('')
  const [showBrief, setShowBrief] = useState(false)
  const [localMessages, setLocalMessages] = useState([])
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const qc = useQueryClient()

  const { data: historyData, isLoading } = useQuery({
    queryKey: ['chat-history'],
    queryFn: api.getChatHistory,
  })

  const { data: briefData } = useQuery({
    queryKey: ['chat-brief'],
    queryFn: api.getChatBrief,
    refetchInterval: 10_000,
  })

  const messages = historyData?.length > 0 ? historyData : localMessages

  const sendMutation = useMutation({
    mutationFn: api.sendChatMessage,
    onMutate: (msg) => {
      setLocalMessages(prev => [
        ...prev,
        { role: 'user', content: msg, id: Date.now() },
      ])
    },
    onSuccess: (data) => {
      setLocalMessages(prev => [
        ...prev,
        { role: 'assistant', content: data.response, id: Date.now() + 1 },
      ])
      qc.invalidateQueries({ queryKey: ['chat-history'] })
      qc.invalidateQueries({ queryKey: ['chat-brief'] })
    },
  })

  const clearMutation = useMutation({
    mutationFn: api.clearChatHistory,
    onSuccess: () => {
      setLocalMessages([])
      qc.invalidateQueries({ queryKey: ['chat-history'] })
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  const send = (text) => {
    const msg = text || input.trim()
    if (!msg || sendMutation.isPending) return
    setInput('')
    sendMutation.mutate(msg)
    inputRef.current?.focus()
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const displayMessages = historyData?.length > 0 ? historyData : localMessages

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div>
          <h2 className="font-semibold text-charcoal-900">Agent Chat</h2>
          <p className="text-xs text-charcoal-400 mt-0.5">
            Give instructions, set creative briefs, ask about performance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowBrief(!showBrief)}
            className="flex items-center gap-1.5 btn-secondary text-sm"
          >
            <Settings2 size={13} />
            {briefData?.brief ? 'View Brief' : 'No Brief Set'}
          </button>
          <button
            onClick={() => clearMutation.mutate()}
            className="btn-ghost text-sm flex items-center gap-1.5 text-charcoal-400"
          >
            <Trash2 size={13} />
            Clear
          </button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0 gap-4 relative">
        {/* Chat area */}
        <div className={`flex flex-col flex-1 min-w-0 transition-all ${showBrief ? 'mr-72' : ''}`}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto bg-charcoal-50 rounded-2xl p-4 space-y-4 mb-3">
            {isLoading ? (
              <div className="text-center py-8 text-charcoal-400 text-sm">Loading...</div>
            ) : displayMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 py-8">
                <div className="w-12 h-12 bg-charcoal-800 rounded-2xl flex items-center justify-center">
                  <Bot size={22} className="text-white" />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-charcoal-700">Your EASTEND agent is ready</p>
                  <p className="text-sm text-charcoal-400 mt-1">
                    Tell me how you want your content made, or ask anything about your account.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {QUICK_PROMPTS.map(p => (
                    <button
                      key={p}
                      onClick={() => send(p)}
                      className="text-xs bg-white border border-charcoal-200 text-charcoal-600 px-3 py-1.5 rounded-xl hover:border-brand-300 hover:text-brand-600 transition-colors"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              displayMessages.map((msg, i) => <Message key={msg.id || i} msg={msg} />)
            )}

            {/* Typing indicator */}
            {sendMutation.isPending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-charcoal-800 flex items-center justify-center flex-shrink-0">
                  <Bot size={14} className="text-white" />
                </div>
                <div className="bg-white border border-charcoal-100 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-charcoal-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-charcoal-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-charcoal-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2 flex-shrink-0">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Tell me how you want videos made, ask about performance, set instructions..."
              rows={2}
              className="flex-1 border border-charcoal-200 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand-400 resize-none bg-white"
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || sendMutation.isPending}
              className="btn-primary px-4 rounded-2xl flex-shrink-0 self-end h-[52px] flex items-center justify-center disabled:opacity-50"
            >
              <Send size={16} />
            </button>
          </div>
        </div>

        {/* Brief panel */}
        {showBrief && briefData?.brief && (
          <BriefPanel brief={briefData.brief} onClose={() => setShowBrief(false)} />
        )}
      </div>
    </div>
  )
}
