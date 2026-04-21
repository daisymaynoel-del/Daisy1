import clsx from 'clsx'

export default function StatCard({ label, value, sub, icon: Icon, trend, trendLabel, color = 'brand' }) {
  const colorMap = {
    brand: 'text-brand-500 bg-brand-50',
    blue:  'text-blue-500 bg-blue-50',
    green: 'text-green-500 bg-green-50',
    gold:  'text-gold-600 bg-amber-50',
    purple:'text-purple-500 bg-purple-50',
  }

  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{label}</p>
          <p className="stat-value mt-1">{value ?? '—'}</p>
          {sub && <p className="text-xs text-charcoal-400 mt-0.5">{sub}</p>}
        </div>
        {Icon && (
          <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', colorMap[color])}>
            <Icon size={18} />
          </div>
        )}
      </div>
      {trend !== undefined && (
        <div className={clsx('flex items-center gap-1 text-xs font-medium mt-2', trend >= 0 ? 'text-green-600' : 'text-red-500')}>
          <span>{trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%</span>
          {trendLabel && <span className="text-charcoal-400 font-normal">{trendLabel}</span>}
        </div>
      )}
    </div>
  )
}
