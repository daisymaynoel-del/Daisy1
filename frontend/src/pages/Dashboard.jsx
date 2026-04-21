import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Eye, TrendingUp, Users, Clock, Instagram, CheckSquare, BarChart2, AlertTriangle } from 'lucide-react'
import { api } from '../api/client'
import StatCard from '../components/StatCard'
import PostCard from '../components/PostCard'

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: api.getDashboardStats,
    refetchInterval: 30_000,
  })

  const { data: topPosts } = useQuery({
    queryKey: ['top-posts'],
    queryFn: () => api.getTopPosts(7, 3),
  })

  const { data: pendingPosts } = useQuery({
    queryKey: ['pending-approval'],
    queryFn: api.getPendingApproval,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-charcoal-400">Loading dashboard...</div>
      </div>
    )
  }

  const todayPosts = (stats?.instagram_posts_today || 0) + (stats?.tiktok_posts_today || 0)
  const targetPosts = 6 // 3 per platform

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Avg Views (7d)"
          value={stats?.avg_views_7d ? Math.round(stats.avg_views_7d).toLocaleString() : '0'}
          icon={Eye}
          color="brand"
        />
        <StatCard
          label="Engagement Rate"
          value={`${stats?.avg_engagement_rate_7d?.toFixed(1) || '0'}%`}
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          label="Follower Growth (7d)"
          value={`+${stats?.follower_growth_7d || 0}`}
          icon={Users}
          color="blue"
        />
        <StatCard
          label="Posts Today"
          value={`${todayPosts}/${targetPosts}`}
          sub={`${stats?.instagram_posts_today || 0} IG · ${stats?.tiktok_posts_today || 0} TT`}
          icon={Clock}
          color="gold"
        />
      </div>

      {/* Alert: Pending Approval */}
      {(stats?.pending_approval_count || 0) > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-amber-100 rounded-xl flex items-center justify-center">
              <AlertTriangle size={16} className="text-amber-600" />
            </div>
            <div>
              <p className="font-semibold text-charcoal-900 text-sm">
                {stats.pending_approval_count} post{stats.pending_approval_count > 1 ? 's' : ''} waiting for your approval
              </p>
              <p className="text-xs text-charcoal-500">Review and approve before they can be scheduled</p>
            </div>
          </div>
          <Link to="/approval" className="btn-primary text-sm whitespace-nowrap">
            Review Now
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Posts This Week */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-charcoal-900">Top Posts This Week</h2>
            <Link to="/analytics" className="text-sm text-brand-500 hover:text-brand-600 font-medium">View all</Link>
          </div>
          {topPosts?.length > 0 ? (
            <div className="space-y-3">
              {topPosts.map(post => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-charcoal-400">
              <BarChart2 size={32} className="mx-auto mb-2 opacity-40" />
              <p className="text-sm">No published posts yet</p>
              <Link to="/upload" className="text-brand-500 text-sm hover:underline mt-1 block">Upload content to get started</Link>
            </div>
          )}
        </div>

        {/* Quick Actions / Status */}
        <div className="space-y-4">
          <div className="card">
            <h2 className="font-semibold text-charcoal-900 mb-4">Platform Status</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="badge badge-instagram flex items-center gap-1">
                    <Instagram size={11} />
                    Instagram
                  </div>
                </div>
                <span className="text-sm font-medium text-charcoal-700">
                  {stats?.instagram_posts_today || 0}/3 today
                </span>
              </div>
              <div className="w-full bg-charcoal-100 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all"
                  style={{ width: `${Math.min(((stats?.instagram_posts_today || 0) / 3) * 100, 100)}%` }}
                />
              </div>

              <div className="flex items-center justify-between mt-3">
                <span className="badge badge-tiktok">TikTok</span>
                <span className="text-sm font-medium text-charcoal-700">
                  {stats?.tiktok_posts_today || 0}/3 today
                </span>
              </div>
              <div className="w-full bg-charcoal-100 rounded-full h-2">
                <div
                  className="bg-charcoal-800 h-2 rounded-full transition-all"
                  style={{ width: `${Math.min(((stats?.tiktok_posts_today || 0) / 3) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="font-semibold text-charcoal-900 mb-3">Quick Actions</h2>
            <div className="space-y-2">
              <Link to="/upload" className="btn-primary w-full text-center block text-sm">Upload New Content</Link>
              <Link to="/approval" className="btn-secondary w-full text-center block text-sm">
                Review Queue {stats?.pending_approval_count > 0 && `(${stats.pending_approval_count})`}
              </Link>
              <Link to="/suggestions" className="btn-ghost w-full text-center block text-sm">View AI Suggestions</Link>
            </div>
          </div>

          <div className="card">
            <h2 className="font-semibold text-charcoal-900 mb-2">Active Trends</h2>
            <p className="text-3xl font-bold text-brand-500">{stats?.active_trends_count || 0}</p>
            <p className="text-sm text-charcoal-400 mt-0.5">sounds & hashtags tracked</p>
            <Link to="/trends" className="text-sm text-brand-500 hover:underline mt-2 block">View trends →</Link>
          </div>
        </div>
      </div>

      {/* Pending Approval Preview */}
      {pendingPosts?.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-charcoal-900">Pending Your Approval</h2>
            <Link to="/approval" className="text-sm text-brand-500 font-medium">See all</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {pendingPosts.slice(0, 3).map(post => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
