import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { FileText, RefreshCw, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react'
import { api } from '../api/client'

export default function Reports() {
  const [selectedId, setSelectedId] = useState(null)
  const qc = useQueryClient()

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: api.listReports,
  })

  const generateMutation = useMutation({
    mutationFn: api.generateReport,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  })

  const selected = reports?.find(r => r.id === selectedId) || reports?.[0]

  if (isLoading) {
    return <div className="text-center py-20 text-charcoal-400">Loading reports...</div>
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-semibold text-charcoal-900">Weekly Strategy Reports</h2>
          <p className="text-sm text-charcoal-400 mt-0.5">Generated every Monday at 09:00 London time</p>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} className={generateMutation.isPending ? 'animate-spin' : ''} />
          Generate Now
        </button>
      </div>

      {!reports?.length ? (
        <div className="text-center py-20 text-charcoal-400">
          <FileText size={32} className="mx-auto mb-3 opacity-40" />
          <p className="font-medium">No reports yet</p>
          <p className="text-sm mt-1">Click "Generate Now" or wait for Monday's automatic report</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Report List */}
          <div className="lg:col-span-1 space-y-2">
            {reports.map(r => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`w-full text-left p-3 rounded-xl border transition-colors ${
                  (selected?.id === r.id)
                    ? 'bg-brand-50 border-brand-200 text-brand-800'
                    : 'bg-white border-charcoal-100 text-charcoal-700 hover:bg-charcoal-50'
                }`}
              >
                <p className="font-semibold text-sm">{format(new Date(r.report_date), 'dd MMM yyyy')}</p>
                <p className="text-xs text-charcoal-400 mt-0.5">{r.total_posts} posts · {r.avg_views?.toLocaleString()} avg views</p>
              </button>
            ))}
          </div>

          {/* Report Detail */}
          {selected && (
            <div className="lg:col-span-3 space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="card text-center">
                  <p className="text-2xl font-bold text-charcoal-900">{selected.total_posts}</p>
                  <p className="text-xs text-charcoal-400 mt-0.5">Posts Published</p>
                </div>
                <div className="card text-center">
                  <p className="text-2xl font-bold text-charcoal-900">{Math.round(selected.avg_views).toLocaleString()}</p>
                  <p className="text-xs text-charcoal-400 mt-0.5">Avg Views</p>
                </div>
                <div className="card text-center">
                  <p className="text-2xl font-bold text-charcoal-900">{selected.avg_engagement_rate?.toFixed(1)}%</p>
                  <p className="text-xs text-charcoal-400 mt-0.5">Avg Engagement</p>
                </div>
              </div>

              {/* Wins & Losses */}
              <div className="grid grid-cols-2 gap-4">
                {selected.wins?.length > 0 && (
                  <div className="card bg-green-50 border-green-200">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={15} className="text-green-600" />
                      <h3 className="font-semibold text-green-800 text-sm">Wins</h3>
                    </div>
                    <ul className="space-y-1.5">
                      {selected.wins.map((w, i) => (
                        <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                          <span className="text-green-400 mt-0.5">✓</span>
                          {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {selected.losses?.length > 0 && (
                  <div className="card bg-red-50 border-red-200">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingDown size={15} className="text-red-600" />
                      <h3 className="font-semibold text-red-800 text-sm">To Improve</h3>
                    </div>
                    <ul className="space-y-1.5">
                      {selected.losses.map((l, i) => (
                        <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                          <span className="text-red-400 mt-0.5">×</span>
                          {l}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Next Week Direction */}
              {selected.next_week_direction && (
                <div className="card bg-brand-50 border-brand-200">
                  <div className="flex items-center gap-2 mb-2">
                    <ArrowRight size={15} className="text-brand-600" />
                    <h3 className="font-semibold text-brand-800 text-sm">Next Week's Direction</h3>
                  </div>
                  <p className="text-sm text-brand-700">{selected.next_week_direction}</p>
                </div>
              )}

              {/* Full Report */}
              {selected.report_content && (
                <div className="card prose prose-sm max-w-none">
                  <ReactMarkdown>{selected.report_content}</ReactMarkdown>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
