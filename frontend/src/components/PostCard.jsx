import { format } from 'date-fns'
import { Instagram, Music, Clock, Eye, Heart, MessageCircle, Bookmark, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

const PLATFORM_ICON = {
  instagram: <Instagram size={13} />,
  tiktok: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V9.05a8.16 8.16 0 004.77 1.52V7.12a4.85 4.85 0 01-1-.43z"/>
    </svg>
  ),
}

export default function PostCard({ post, metrics, onClick }) {
  const pillarColors = {
    transformation: 'badge-transformation',
    education: 'badge-education',
    process: 'badge-process',
    lifestyle: 'badge-lifestyle',
  }

  return (
    <div
      className={clsx(
        'card hover:shadow-md transition-shadow cursor-pointer relative overflow-hidden',
        post.needs_review && 'border-amber-300'
      )}
      onClick={() => onClick && onClick(post)}
    >
      {post.needs_review && (
        <div className="absolute top-0 left-0 right-0 bg-amber-50 border-b border-amber-200 px-3 py-1.5 flex items-center gap-1.5 text-amber-700 text-xs font-medium">
          <AlertTriangle size={11} />
          Flagged for review
        </div>
      )}

      <div className={clsx('flex gap-3', post.needs_review && 'mt-6')}>
        {/* Thumbnail */}
        <div className="w-16 h-20 rounded-lg bg-charcoal-100 flex-shrink-0 overflow-hidden">
          {post.thumbnail_path ? (
            <img
              src={`/thumbnails/${post.thumbnail_path.split('/').pop()}`}
              alt="thumbnail"
              className="w-full h-full object-cover"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-charcoal-300">
              <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                <path d="M8 5v10l7-5-7-5z"/>
              </svg>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={clsx('badge flex items-center gap-1', post.platform === 'instagram' ? 'badge-instagram' : 'badge-tiktok')}>
              {PLATFORM_ICON[post.platform]}
              {post.platform}
            </span>
            {post.content_pillar && (
              <span className={clsx('badge', pillarColors[post.content_pillar] || 'bg-charcoal-100 text-charcoal-600')}>
                {post.content_pillar}
              </span>
            )}
            <span className={clsx('status-badge ml-auto', `status-${post.status}`)}>
              {post.status.replace('_', ' ')}
            </span>
          </div>

          {post.hook_text && (
            <p className="font-semibold text-sm text-charcoal-900 truncate mb-1">{post.hook_text}</p>
          )}

          {post.caption && (
            <p className="text-xs text-charcoal-500 line-clamp-2 mb-2">{post.caption}</p>
          )}

          <div className="flex items-center gap-3 text-xs text-charcoal-400">
            {post.audio_name && (
              <span className="flex items-center gap-1 truncate max-w-28">
                <Music size={10} />
                <span className="truncate">{post.audio_name}</span>
              </span>
            )}
            {post.scheduled_time && (
              <span className="flex items-center gap-1">
                <Clock size={10} />
                {format(new Date(post.scheduled_time), 'dd MMM HH:mm')}
              </span>
            )}
          </div>

          {metrics && (
            <div className="flex items-center gap-3 mt-2 text-xs font-medium">
              <span className="flex items-center gap-1 text-charcoal-600">
                <Eye size={11} /> {metrics.views?.toLocaleString()}
              </span>
              <span className="flex items-center gap-1 text-red-500">
                <Heart size={11} /> {metrics.likes?.toLocaleString()}
              </span>
              <span className="flex items-center gap-1 text-blue-500">
                <MessageCircle size={11} /> {metrics.comments?.toLocaleString()}
              </span>
              <span className="flex items-center gap-1 text-green-500">
                <Bookmark size={11} /> {metrics.saves?.toLocaleString()}
              </span>
              <span className="ml-auto text-charcoal-400">{metrics.engagement_rate?.toFixed(1)}% ER</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
