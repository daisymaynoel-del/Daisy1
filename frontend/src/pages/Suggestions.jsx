import { useQuery } from '@tanstack/react-query'
import { Lightbulb, Instagram, TrendingUp, Music, Eye } from 'lucide-react'
import { api } from '../api/client'
import clsx from 'clsx'

const PILLAR_COLORS = {
  transformation: 'bg-brand-50 border-brand-200',
  education: 'bg-blue-50 border-blue-200',
  process: 'bg-green-50 border-green-200',
  lifestyle: 'bg-amber-50 border-amber-200',
}

const PILLAR_BADGE = {
  transformation: 'badge-transformation',
  education: 'badge-education',
  process: 'badge-process',
  lifestyle: 'badge-lifestyle',
}

export default function Suggestions() {
  const { data: suggestions, isLoading, refetch } = useQuery({
    queryKey: ['suggestions'],
    queryFn: api.getSuggestions,
    staleTime: 5 * 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center">
          <Lightbulb size={22} className="text-brand-500 animate-pulse" />
        </div>
        <p className="text-charcoal-500">AI is analysing your performance data...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-charcoal-900">5 Recommended Next Posts</h2>
          <p className="text-sm text-charcoal-400 mt-0.5">Based on your performance data, current trends, and what's working for EASTEND</p>
        </div>
        <button onClick={refetch} className="btn-secondary text-sm">Regenerate</button>
      </div>

      {suggestions?.length === 0 && (
        <div className="text-center py-16 text-charcoal-400">
          <Lightbulb size={32} className="mx-auto mb-3 opacity-40" />
          <p>Upload content and publish a few posts first — then AI can suggest based on your data.</p>
        </div>
      )}

      {suggestions?.map((s, i) => (
        <div
          key={i}
          className={clsx('card border', PILLAR_COLORS[s.content_pillar] || 'border-charcoal-100')}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-white rounded-xl border border-charcoal-200 flex items-center justify-center flex-shrink-0 font-bold text-sm text-charcoal-500">
                #{s.rank}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={clsx('badge flex items-center gap-1', s.platform === 'instagram' ? 'badge-instagram' : 'badge-tiktok')}>
                    {s.platform === 'instagram' ? <Instagram size={10} /> : (
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V9.05a8.16 8.16 0 004.77 1.52V7.12a4.85 4.85 0 01-1-.43z"/>
                      </svg>
                    )}
                    {s.platform}
                  </span>
                  <span className={clsx('badge', PILLAR_BADGE[s.content_pillar] || 'bg-charcoal-100 text-charcoal-600')}>
                    {s.content_pillar}
                  </span>
                  <span className="text-xs text-charcoal-400">
                    {Math.round(s.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-charcoal-700 flex-shrink-0">
              <Eye size={14} className="text-brand-400" />
              ~{s.predicted_views?.toLocaleString()}
            </div>
          </div>

          <div className="mt-3 space-y-2">
            <div>
              <p className="text-xs text-charcoal-400 font-medium uppercase tracking-wide">Hook</p>
              <p className="font-semibold text-charcoal-900 mt-0.5">"{s.hook}"</p>
            </div>

            <div>
              <p className="text-xs text-charcoal-400 font-medium uppercase tracking-wide">Caption Preview</p>
              <p className="text-sm text-charcoal-700 mt-0.5">{s.caption_preview}</p>
            </div>

            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-charcoal-400 font-medium uppercase tracking-wide">Suggested Audio</p>
                <p className="text-sm text-charcoal-700 flex items-center gap-1.5 mt-0.5">
                  <Music size={12} className="text-brand-400" />
                  {s.suggested_audio}
                </p>
              </div>
            </div>

            <div className="bg-white bg-opacity-70 rounded-xl p-3 border border-white">
              <p className="text-xs text-charcoal-400 font-medium uppercase tracking-wide mb-1">Why this post</p>
              <p className="text-sm text-charcoal-700">{s.reasoning}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
