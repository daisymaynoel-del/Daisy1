import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Check, X, Clock, Music, AlertTriangle, Eye, Bookmark } from 'lucide-react'
import { api } from '../api/client'
import clsx from 'clsx'

export default function Approval() {
  const qc = useQueryClient()
  const [scheduleTimes, setScheduleTimes] = useState({})
  const [rejectionReasons, setRejectionReasons] = useState({})

  const { data: pendingPosts, isLoading } = useQuery({
    queryKey: ['pending-approval'],
    queryFn: api.getPendingApproval,
    refetchInterval: 15_000,
  })

  const approveMutation = useMutation({
    mutationFn: ({ id, action, scheduledTime, rejectionReason }) =>
      api.approvePost(id, { action, scheduled_time: scheduledTime || undefined, rejection_reason: rejectionReason || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-approval'] })
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] })
      qc.invalidateQueries({ queryKey: ['posts'] })
    },
  })

  const handleAction = (post, action) => {
    approveMutation.mutate({
      id: post.id,
      action,
      scheduledTime: scheduleTimes[post.id],
      rejectionReason: rejectionReasons[post.id],
    })
  }

  if (isLoading) {
    return <div className="text-center py-20 text-charcoal-400">Loading...</div>
  }

  if (!pendingPosts?.length) {
    return (
      <div className="max-w-2xl mx-auto text-center py-24">
        <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Check size={28} className="text-green-500" />
        </div>
        <h2 className="text-xl font-semibold text-charcoal-900 mb-2">You're all caught up</h2>
        <p className="text-charcoal-400">No posts waiting for approval right now.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 bg-amber-400 rounded-full" />
        <p className="text-sm text-charcoal-500 font-medium">{pendingPosts.length} post{pendingPosts.length > 1 ? 's' : ''} waiting for your approval</p>
      </div>

      {pendingPosts.map(post => (
        <div key={post.id} className={clsx('card border', post.needs_review ? 'border-amber-300' : 'border-charcoal-100')}>
          {post.needs_review && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4 text-sm text-amber-700">
              <AlertTriangle size={14} />
              <span className="font-medium">Flagged:</span> {post.review_reason || 'Predicted to underperform'}
            </div>
          )}

          <div className="flex gap-4">
            {/* Thumbnail */}
            <div className="w-24 h-32 rounded-xl bg-charcoal-100 flex-shrink-0 overflow-hidden">
              {post.thumbnail_path ? (
                <img
                  src={`/thumbnails/${post.thumbnail_path.split('/').pop()}`}
                  alt=""
                  className="w-full h-full object-cover"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-charcoal-300 text-xs">No preview</div>
              )}
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={clsx('badge', post.platform === 'instagram' ? 'badge-instagram' : 'badge-tiktok')}>
                    {post.platform}
                  </span>
                  {post.content_pillar && (
                    <span className="badge bg-charcoal-100 text-charcoal-600">{post.content_pillar}</span>
                  )}
                  {post.ai_confidence_score && (
                    <span className="text-xs text-charcoal-400">AI confidence: {Math.round(post.ai_confidence_score)}%</span>
                  )}
                </div>
                {post.predicted_performance && (
                  <div className="flex items-center gap-1 text-xs text-charcoal-400 flex-shrink-0">
                    <Eye size={11} />
                    ~{Math.round(post.predicted_performance).toLocaleString()} predicted views
                  </div>
                )}
              </div>

              {post.hook_text && (
                <p className="font-semibold text-charcoal-900 mb-1">"{post.hook_text}"</p>
              )}

              {post.caption && (
                <p className="text-sm text-charcoal-600 mb-3 whitespace-pre-line line-clamp-4">{post.caption}</p>
              )}

              {post.patch_test_included && (
                <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 rounded-lg px-2.5 py-1.5 mb-3 w-fit">
                  <AlertTriangle size={11} />
                  Patch test notice included
                </div>
              )}

              <div className="flex items-center gap-4 text-xs text-charcoal-400 mb-4">
                {post.audio_name && (
                  <span className="flex items-center gap-1">
                    <Music size={10} />
                    {post.audio_name}
                  </span>
                )}
                {post.hashtags?.length > 0 && (
                  <span>{post.hashtags.length} hashtags</span>
                )}
              </div>

              {/* Schedule Time */}
              <div className="flex items-center gap-2 mb-4">
                <Clock size={13} className="text-charcoal-400" />
                <label className="text-xs text-charcoal-500 font-medium">Schedule for:</label>
                <input
                  type="datetime-local"
                  className="text-xs border border-charcoal-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  value={scheduleTimes[post.id] || ''}
                  onChange={(e) => setScheduleTimes(prev => ({ ...prev, [post.id]: e.target.value }))}
                />
                <span className="text-xs text-charcoal-400">(or leave for auto-schedule)</span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAction(post, 'approve')}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white font-medium px-4 py-2 rounded-xl text-sm transition-colors"
                >
                  <Check size={14} />
                  Approve
                </button>
                <button
                  onClick={() => handleAction(post, 'reject')}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-2 bg-red-50 hover:bg-red-100 text-red-600 font-medium px-4 py-2 rounded-xl text-sm transition-colors"
                >
                  <X size={14} />
                  Reject
                </button>
                <input
                  type="text"
                  placeholder="Rejection reason (optional)"
                  className="text-xs border border-charcoal-200 rounded-lg px-3 py-2 flex-1 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  value={rejectionReasons[post.id] || ''}
                  onChange={(e) => setRejectionReasons(prev => ({ ...prev, [post.id]: e.target.value }))}
                />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
