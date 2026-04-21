import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Music, Hash, TrendingUp, Flame } from 'lucide-react'
import { api } from '../api/client'
import clsx from 'clsx'

const SATURATION_COLORS = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
}

function TrendRow({ trend }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-charcoal-50 last:border-0">
      <div className="flex items-center gap-3 min-w-0">
        {trend.trend_type === 'sound' ? (
          <Music size={14} className="text-brand-400 flex-shrink-0" />
        ) : (
          <Hash size={14} className="text-blue-400 flex-shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium text-charcoal-800 truncate">{trend.trend_value}</p>
          <p className="text-xs text-charcoal-400">{trend.use_count?.toLocaleString()} uses · {(trend.growth_rate * 100).toFixed(0)}% growth</p>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <div className="w-16 bg-charcoal-100 rounded-full h-1.5">
          <div
            className="bg-brand-400 h-1.5 rounded-full"
            style={{ width: `${Math.min(trend.relevance_score * 100, 100)}%` }}
          />
        </div>
        <span className={clsx('badge', SATURATION_COLORS[trend.saturation_level] || SATURATION_COLORS.low)}>
          {trend.saturation_level}
        </span>
      </div>
    </div>
  )
}

export default function TrendTracker() {
  const [platform, setPlatform] = useState('instagram')
  const qc = useQueryClient()

  const { data: sounds } = useQuery({
    queryKey: ['sounds', platform],
    queryFn: () => api.getTrendingSounds(platform),
    refetchInterval: 60_000,
  })

  const { data: hashtags } = useQuery({
    queryKey: ['hashtags', platform],
    queryFn: () => api.getTrendingHashtags(platform),
    refetchInterval: 60_000,
  })

  const { data: benchmarks } = useQuery({
    queryKey: ['benchmarks', platform],
    queryFn: () => api.getViralBenchmarks(platform),
  })

  const refreshMutation = useMutation({
    mutationFn: api.refreshTrends,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sounds'] })
      qc.invalidateQueries({ queryKey: ['hashtags'] })
    },
  })

  return (
    <div className="max-w-6xl space-y-5">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {['instagram', 'tiktok'].map(p => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={clsx(
                'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
                platform === p ? 'bg-charcoal-900 text-white' : 'bg-white border border-charcoal-200 text-charcoal-600 hover:bg-charcoal-50'
              )}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} className={refreshMutation.isPending ? 'animate-spin' : ''} />
          Refresh Trends
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Trending Sounds */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Music size={16} className="text-brand-500" />
            <h2 className="font-semibold text-charcoal-900">Trending Sounds</h2>
            <span className="text-xs text-charcoal-400 ml-auto">Sweet spot: low/medium saturation</span>
          </div>
          {sounds?.length > 0 ? (
            sounds.map(t => <TrendRow key={t.id} trend={t} />)
          ) : (
            <p className="text-sm text-charcoal-400 py-4 text-center">No sound trends yet — click Refresh</p>
          )}
        </div>

        {/* Trending Hashtags */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Hash size={16} className="text-blue-500" />
            <h2 className="font-semibold text-charcoal-900">Trending Hashtags</h2>
          </div>
          {hashtags?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {hashtags.map(t => (
                <div
                  key={t.id}
                  className={clsx(
                    'text-sm px-3 py-1.5 rounded-xl font-medium',
                    t.saturation_level === 'low' ? 'bg-green-50 text-green-700 border border-green-200' :
                    t.saturation_level === 'medium' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                    'bg-charcoal-100 text-charcoal-500'
                  )}
                >
                  {t.trend_value}
                  <span className="text-xs opacity-60 ml-1">{(t.relevance_score * 100).toFixed(0)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-charcoal-400 py-4 text-center">No hashtag trends yet — click Refresh</p>
          )}
        </div>
      </div>

      {/* Viral Benchmarks */}
      {benchmarks?.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Flame size={16} className="text-red-500" />
            <h2 className="font-semibold text-charcoal-900">Viral Benchmarks</h2>
            <p className="text-xs text-charcoal-400 ml-auto">Top videos in your niche to emulate</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-charcoal-100">
                  <th className="text-left py-2 text-charcoal-400 font-medium">Hook</th>
                  <th className="text-left py-2 text-charcoal-400 font-medium">Audio</th>
                  <th className="text-right py-2 text-charcoal-400 font-medium">Views</th>
                  <th className="text-right py-2 text-charcoal-400 font-medium">Completion</th>
                  <th className="text-left py-2 text-charcoal-400 font-medium">CTA</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.slice(0, 10).map(b => (
                  <tr key={b.id} className="border-b border-charcoal-50">
                    <td className="py-3 font-medium text-charcoal-800 max-w-48">
                      <p className="truncate">"{b.hook_text}"</p>
                    </td>
                    <td className="py-3 text-charcoal-500 max-w-40">
                      <p className="truncate">{b.audio_name}</p>
                    </td>
                    <td className="py-3 text-right font-semibold">{b.views?.toLocaleString()}</td>
                    <td className="py-3 text-right">{b.completion_rate ? `${(b.completion_rate * 100).toFixed(0)}%` : '—'}</td>
                    <td className="py-3 text-charcoal-500">{b.cta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
