import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { Eye, TrendingUp, Bookmark, Users } from 'lucide-react'
import { api } from '../api/client'
import StatCard from '../components/StatCard'
import PostCard from '../components/PostCard'

export default function Analytics() {
  const { data: rolling30 } = useQuery({ queryKey: ['rolling-30'], queryFn: () => api.getRollingAverages(30) })
  const { data: rolling7 } = useQuery({ queryKey: ['rolling-7'], queryFn: () => api.getRollingAverages(7) })
  const { data: platformStats } = useQuery({ queryKey: ['by-platform'], queryFn: () => api.getByPlatform(7) })
  const { data: topPosts } = useQuery({ queryKey: ['top-posts-analytics'], queryFn: () => api.getTopPosts(30, 5) })

  const platformChartData = platformStats
    ? [
        { name: 'Instagram', views: platformStats.instagram?.avg_views || 0, er: platformStats.instagram?.avg_engagement_rate || 0 },
        { name: 'TikTok', views: platformStats.tiktok?.avg_views || 0, er: platformStats.tiktok?.avg_engagement_rate || 0 },
      ]
    : []

  return (
    <div className="max-w-6xl space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Avg Views (7d)"
          value={Math.round(rolling7?.avg_views || 0).toLocaleString()}
          icon={Eye}
          color="brand"
          trend={rolling30?.avg_views ? Math.round(((rolling7?.avg_views || 0) / rolling30.avg_views - 1) * 100) : 0}
          trendLabel="vs 30d avg"
        />
        <StatCard
          label="Engagement Rate (7d)"
          value={`${(rolling7?.avg_engagement_rate || 0).toFixed(1)}%`}
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          label="Avg Saves (7d)"
          value={Math.round(rolling7?.avg_saves || 0).toLocaleString()}
          icon={Bookmark}
          color="blue"
        />
        <StatCard
          label="Sample Size (7d)"
          value={rolling7?.sample_size || 0}
          sub="published posts with 24h data"
          icon={Users}
          color="gold"
        />
      </div>

      {/* Platform Comparison */}
      {platformChartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="font-semibold text-charcoal-900 mb-4">Avg Views by Platform (7d)</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={platformChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0ede9" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="views" fill="#c85a3d" radius={[6, 6, 0, 0]} name="Avg Views" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h2 className="font-semibold text-charcoal-900 mb-4">Engagement Rate by Platform (7d)</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={platformChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0ede9" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `${v}%`} />
                <Tooltip formatter={v => `${v.toFixed(1)}%`} />
                <Bar dataKey="er" fill="#d4a853" radius={[6, 6, 0, 0]} name="Engagement Rate" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Rolling Average Comparison */}
      <div className="card">
        <h2 className="font-semibold text-charcoal-900 mb-4">7-Day vs 30-Day Averages</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-charcoal-100">
                <th className="text-left py-2 text-charcoal-400 font-medium">Metric</th>
                <th className="text-right py-2 text-charcoal-400 font-medium">Last 7 Days</th>
                <th className="text-right py-2 text-charcoal-400 font-medium">Last 30 Days</th>
                <th className="text-right py-2 text-charcoal-400 font-medium">Trend</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Avg Views', key: 'avg_views', format: v => Math.round(v).toLocaleString() },
                { label: 'Avg Likes', key: 'avg_likes', format: v => Math.round(v).toLocaleString() },
                { label: 'Avg Engagement Rate', key: 'avg_engagement_rate', format: v => `${v.toFixed(1)}%` },
                { label: 'Avg Saves', key: 'avg_saves', format: v => Math.round(v).toLocaleString() },
              ].map(({ label, key, format }) => {
                const v7 = rolling7?.[key] || 0
                const v30 = rolling30?.[key] || 0
                const trend = v30 > 0 ? Math.round(((v7 / v30) - 1) * 100) : 0
                return (
                  <tr key={key} className="border-b border-charcoal-50">
                    <td className="py-3 font-medium text-charcoal-700">{label}</td>
                    <td className="py-3 text-right font-semibold">{format(v7)}</td>
                    <td className="py-3 text-right text-charcoal-500">{format(v30)}</td>
                    <td className={`py-3 text-right font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Performing Posts */}
      {topPosts?.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-charcoal-900 mb-4">Top Posts (Last 30 Days)</h2>
          <div className="space-y-3">
            {topPosts.map((post, i) => (
              <div key={post.id} className="flex items-center gap-3">
                <span className="text-2xl font-bold text-charcoal-200 w-8 text-center">#{i + 1}</span>
                <div className="flex-1">
                  <PostCard post={post} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
