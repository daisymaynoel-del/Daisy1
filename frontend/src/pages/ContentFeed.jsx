import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, ExternalLink } from 'lucide-react'
import { api } from '../api/client'
import PostCard from '../components/PostCard'

const PLATFORMS = ['all', 'instagram', 'tiktok']
const STATUSES = ['all', 'published', 'scheduled', 'pending_approval', 'draft', 'rejected']
const PILLARS = ['all', 'transformation', 'education', 'process', 'lifestyle']

export default function ContentFeed() {
  const [platform, setPlatform] = useState('all')
  const [status, setStatus] = useState('all')
  const [pillar, setPillar] = useState('all')

  const params = {}
  if (platform !== 'all') params.platform = platform
  if (status !== 'all') params.status = status
  if (pillar !== 'all') params.pillar = pillar

  const { data: posts, isLoading } = useQuery({
    queryKey: ['posts', params],
    queryFn: () => api.listPosts(params),
    refetchInterval: 30_000,
  })

  return (
    <div className="max-w-5xl space-y-5">
      {/* Filters */}
      <div className="card py-3">
        <div className="flex flex-wrap items-center gap-3">
          <Filter size={15} className="text-charcoal-400" />

          <div>
            <label className="text-xs text-charcoal-400 font-medium mr-2">Platform</label>
            {PLATFORMS.map(p => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={`text-sm px-3 py-1 rounded-lg mr-1 font-medium transition-colors ${
                  platform === p ? 'bg-brand-500 text-white' : 'text-charcoal-500 hover:bg-charcoal-100'
                }`}
              >
                {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          <div className="h-4 w-px bg-charcoal-200" />

          <div>
            <label className="text-xs text-charcoal-400 font-medium mr-2">Status</label>
            {STATUSES.map(s => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`text-sm px-3 py-1 rounded-lg mr-1 font-medium transition-colors ${
                  status === s ? 'bg-charcoal-800 text-white' : 'text-charcoal-500 hover:bg-charcoal-100'
                }`}
              >
                {s === 'all' ? 'All' : s.replace('_', ' ')}
              </button>
            ))}
          </div>

          <div className="h-4 w-px bg-charcoal-200" />

          <div>
            <label className="text-xs text-charcoal-400 font-medium mr-2">Pillar</label>
            {PILLARS.map(p => (
              <button
                key={p}
                onClick={() => setPillar(p)}
                className={`text-sm px-3 py-1 rounded-lg mr-1 font-medium transition-colors ${
                  pillar === p ? 'bg-charcoal-700 text-white' : 'text-charcoal-500 hover:bg-charcoal-100'
                }`}
              >
                {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Feed */}
      {isLoading ? (
        <div className="text-center py-20 text-charcoal-400">Loading posts...</div>
      ) : posts?.length === 0 ? (
        <div className="text-center py-20 text-charcoal-400">
          <p className="font-medium">No posts match these filters</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {posts?.map(post => (
            <PostCard
              key={post.id}
              post={post}
              onClick={(p) => p.platform_url && window.open(p.platform_url, '_blank')}
            />
          ))}
        </div>
      )}

      {posts?.length > 0 && (
        <p className="text-center text-sm text-charcoal-400">{posts.length} posts shown</p>
      )}
    </div>
  )
}
