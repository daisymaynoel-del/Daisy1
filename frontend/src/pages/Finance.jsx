import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PoundSterling, Plus, Trash2, AlertTriangle, CheckCircle2,
  Clock, Loader2, FileText, TrendingDown, Bell, ChevronDown, ChevronUp, X
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import ReactMarkdown from 'react-markdown'
import { api } from '../api/client'
import clsx from 'clsx'

const CATEGORIES = [
  { value: 'rent',      label: 'Rent',        color: '#c85a3d' },
  { value: 'utilities', label: 'Utilities',   color: '#e67a57' },
  { value: 'supplies',  label: 'Supplies',    color: '#efa48a' },
  { value: 'staff',     label: 'Staff',       color: '#d4a853' },
  { value: 'insurance', label: 'Insurance',   color: '#e8c56a' },
  { value: 'equipment', label: 'Equipment',   color: '#888888' },
  { value: 'marketing', label: 'Marketing',   color: '#555555' },
  { value: 'software',  label: 'Software',    color: '#3c3c3c' },
  { value: 'other',     label: 'Other',       color: '#cccccc' },
]
const FREQUENCIES = [
  { value: 'weekly',    label: 'Weekly' },
  { value: 'monthly',   label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual',    label: 'Annual' },
  { value: 'one_off',   label: 'One-off' },
]

function catColor(cat) {
  return CATEGORIES.find(c => c.value === cat)?.color || '#cccccc'
}
function catLabel(cat) {
  return CATEGORIES.find(c => c.value === cat)?.label || cat
}

export default function Finance() {
  const qc = useQueryClient()
  const [tab, setTab] = useState('overview')
  const [showAdd, setShowAdd] = useState(false)

  const { data: bills = [], isLoading: billsLoading } = useQuery({
    queryKey: ['bills'],
    queryFn: api.listBills,
  })
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['bills-summary'],
    queryFn: api.getBillsSummary,
  })
  const { data: latestReport } = useQuery({
    queryKey: ['bills-report-latest'],
    queryFn: api.getLatestBillReport,
  })

  const deleteMutation = useMutation({
    mutationFn: api.deleteBill,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bills'] })
      qc.invalidateQueries({ queryKey: ['bills-summary'] })
    },
  })

  const reportMutation = useMutation({
    mutationFn: api.generateBillReport,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bills-report-latest'] })
      setTab('report')
    },
  })

  const isLoading = billsLoading || summaryLoading

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-charcoal-900">Finance & Expenditure</h2>
          <p className="text-sm text-charcoal-400 mt-0.5">
            Track salon bills, spot due dates and cut costs
          </p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Bill
        </button>
      </div>

      {/* Due-soon notification bar */}
      {summary?.due_soon?.filter(b => b.urgent || b.overdue).length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3">
          <Bell size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-amber-800">
            <span className="font-semibold">Upcoming bills: </span>
            {summary.due_soon
              .filter(b => b.urgent || b.overdue)
              .map(b => (
                <span key={b.id} className="mr-3">
                  {b.name} — {b.overdue ? 'OVERDUE' : `due in ${b.days_until_due}d`} (£{b.amount.toFixed(2)})
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-charcoal-100">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'bills',    label: `Bills (${bills.length})` },
          { id: 'report',   label: 'Cost Report' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              tab === t.id
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-charcoal-500 hover:text-charcoal-700'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-charcoal-400 text-sm py-8 justify-center">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : (
        <>
          {tab === 'overview' && <OverviewTab summary={summary} />}
          {tab === 'bills' && (
            <BillsTab
              bills={bills}
              onDelete={(id) => deleteMutation.mutate(id)}
              qc={qc}
            />
          )}
          {tab === 'report' && (
            <ReportTab
              report={latestReport}
              generating={reportMutation.isPending}
              onGenerate={() => reportMutation.mutate()}
            />
          )}
        </>
      )}

      {showAdd && (
        <AddBillModal
          onClose={() => setShowAdd(false)}
          onSaved={() => {
            setShowAdd(false)
            qc.invalidateQueries({ queryKey: ['bills'] })
            qc.invalidateQueries({ queryKey: ['bills-summary'] })
          }}
        />
      )}
    </div>
  )
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ summary }) {
  if (!summary) return null

  const pieData = Object.entries(summary.by_category || {}).map(([cat, val]) => ({
    name: catLabel(cat),
    value: val,
    fill: catColor(cat),
  }))

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-3 gap-4">
        <KpiCard label="Monthly spend" value={`£${summary.monthly_total?.toFixed(2)}`} icon={PoundSterling} />
        <KpiCard label="Quarterly spend" value={`£${summary.quarterly_total?.toFixed(2)}`} icon={TrendingDown} />
        <KpiCard label="Annual spend" value={`£${summary.annual_total?.toFixed(2)}`} icon={FileText} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Monthly bar chart */}
        <div className="card">
          <p className="font-semibold text-charcoal-900 text-sm mb-4">Monthly Spend (next 12 months)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={summary.monthly_breakdown || []} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eeeeee" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={v => v.split(' ')[0]} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `£${v}`} />
              <Tooltip formatter={v => [`£${Number(v).toFixed(2)}`, 'Total']} />
              <Bar dataKey="total" fill="#c85a3d" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Category pie chart */}
        <div className="card">
          <p className="font-semibold text-charcoal-900 text-sm mb-4">Spend by Category</p>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={70} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={v => `£${Number(v).toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-charcoal-400 text-sm text-center py-12">No bills yet</p>
          )}
        </div>
      </div>

      {/* Due soon list */}
      {summary.due_soon?.length > 0 && (
        <div className="card">
          <p className="font-semibold text-charcoal-900 text-sm mb-3">Bills Due Soon</p>
          <div className="space-y-2">
            {summary.due_soon.map(bill => (
              <div key={bill.id} className={clsx(
                'flex items-center justify-between rounded-xl px-4 py-3 text-sm',
                bill.overdue ? 'bg-red-50 border border-red-200' :
                bill.urgent  ? 'bg-amber-50 border border-amber-200' :
                               'bg-charcoal-50 border border-charcoal-100'
              )}>
                <div className="flex items-center gap-3">
                  {bill.overdue ? <AlertTriangle size={14} className="text-red-500" /> :
                   bill.urgent  ? <Clock size={14} className="text-amber-500" /> :
                                  <CheckCircle2 size={14} className="text-charcoal-400" />}
                  <div>
                    <p className="font-medium text-charcoal-900">{bill.name}</p>
                    <p className="text-xs text-charcoal-400">
                      {bill.overdue ? 'Overdue!' : `Due in ${bill.days_until_due} day${bill.days_until_due === 1 ? '' : 's'}`}
                      {' · '}{bill.next_due}
                    </p>
                  </div>
                </div>
                <span className="font-semibold text-charcoal-900">£{bill.amount.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function KpiCard({ label, value, icon: Icon }) {
  return (
    <div className="card flex items-center gap-4">
      <div className="w-10 h-10 bg-brand-50 rounded-xl flex items-center justify-center flex-shrink-0">
        <Icon size={18} className="text-brand-500" />
      </div>
      <div>
        <p className="text-xs text-charcoal-400">{label}</p>
        <p className="text-xl font-bold text-charcoal-900">{value}</p>
      </div>
    </div>
  )
}

// ── Bills list tab ────────────────────────────────────────────────────────────

function BillsTab({ bills, onDelete, qc }) {
  if (bills.length === 0) {
    return (
      <div className="text-center py-16 text-charcoal-400">
        <PoundSterling size={32} className="mx-auto mb-3 opacity-40" />
        <p className="text-sm">No bills added yet. Click "Add Bill" to get started.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {bills.map(bill => (
        <div key={bill.id} className="card flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div
              className="w-3 h-10 rounded-full flex-shrink-0"
              style={{ background: catColor(bill.category) }}
            />
            <div className="min-w-0">
              <p className="font-semibold text-charcoal-900 text-sm">{bill.name}</p>
              <p className="text-xs text-charcoal-400">
                {catLabel(bill.category)} · {bill.frequency}
                {bill.next_due && ` · next due ${bill.next_due}`}
              </p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="font-bold text-charcoal-900">£{bill.amount.toFixed(2)}</p>
            <p className="text-xs text-charcoal-400">≈ £{bill.monthly_equivalent}/mo</p>
          </div>
          <button
            onClick={() => onDelete(bill.id)}
            className="text-charcoal-300 hover:text-red-500 transition-colors flex-shrink-0"
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
    </div>
  )
}

// ── Report tab ────────────────────────────────────────────────────────────────

function ReportTab({ report, generating, onGenerate }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-charcoal-600">
            AI analysis of your bills — actionable ways to cut salon costs.
          </p>
          {report && (
            <p className="text-xs text-charcoal-400 mt-0.5">
              Last generated: {new Date(report.generated_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
        <button
          onClick={onGenerate}
          disabled={generating}
          className="btn-primary flex items-center gap-2"
        >
          {generating ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />}
          {generating ? 'Analysing…' : report ? 'Refresh Report' : 'Generate Report'}
        </button>
      </div>

      {report ? (
        <div className="card prose prose-sm max-w-none">
          <ReactMarkdown>{report.report_content}</ReactMarkdown>
        </div>
      ) : (
        <div className="card text-center py-16 text-charcoal-400">
          <TrendingDown size={32} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">Click "Generate Report" to get AI cost-cutting recommendations.</p>
        </div>
      )}
    </div>
  )
}

// ── Add bill modal ────────────────────────────────────────────────────────────

const EMPTY = {
  name: '', amount: '', category: 'other', frequency: 'monthly',
  due_day: '', due_date: '', notes: '',
}

function AddBillModal({ onClose, onSaved }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const set = (field, val) => setForm(f => ({ ...f, [field]: val }))

  const handleSave = async () => {
    if (!form.name.trim() || !form.amount) { setErr('Name and amount are required.'); return }
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        amount: parseFloat(form.amount),
        category: form.category,
        frequency: form.frequency,
        due_day: form.due_day ? parseInt(form.due_day) : null,
        due_date: form.due_date || null,
        notes: form.notes || null,
      }
      await api.createBill(payload)
      onSaved()
    } catch (e) {
      setErr(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-charcoal-900">Add Bill</h3>
          <button onClick={onClose} className="text-charcoal-400 hover:text-charcoal-700"><X size={18} /></button>
        </div>

        <div className="space-y-3">
          <Field label="Bill name">
            <input className="input-field" placeholder="e.g. Salon rent" value={form.name} onChange={e => set('name', e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Amount (£)">
              <input className="input-field" type="number" min="0" step="0.01" placeholder="0.00" value={form.amount} onChange={e => set('amount', e.target.value)} />
            </Field>
            <Field label="Frequency">
              <select className="input-field" value={form.frequency} onChange={e => set('frequency', e.target.value)}>
                {FREQUENCIES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Category">
            <select className="input-field" value={form.category} onChange={e => set('category', e.target.value)}>
              {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>

          {form.frequency !== 'one_off' ? (
            <Field label="Due day of month (1–31)">
              <input className="input-field" type="number" min="1" max="31" placeholder="e.g. 1 for 1st of month" value={form.due_day} onChange={e => set('due_day', e.target.value)} />
            </Field>
          ) : (
            <Field label="Due date">
              <input className="input-field" type="date" value={form.due_date} onChange={e => set('due_date', e.target.value)} />
            </Field>
          )}

          <Field label="Notes (optional)">
            <input className="input-field" placeholder="Any extra details" value={form.notes} onChange={e => set('notes', e.target.value)} />
          </Field>
        </div>

        {err && <p className="text-red-500 text-xs">{err}</p>}

        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 size={14} className="animate-spin" /> : null}
            Save Bill
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-charcoal-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
