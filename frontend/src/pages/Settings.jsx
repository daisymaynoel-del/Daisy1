import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Settings2, Link2, CheckCircle2, XCircle, Loader2,
  ExternalLink, Eye, EyeOff, Zap, ChevronDown, ChevronRight
} from 'lucide-react'
import { api } from '../api/client'
import clsx from 'clsx'

export default function Settings() {
  const qc = useQueryClient()

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations'],
    queryFn: api.getIntegrations,
  })

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-semibold text-charcoal-900">Settings & Integrations</h2>
        <p className="text-sm text-charcoal-400 mt-0.5">
          Connect your social accounts via Make.com to enable live posting
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-charcoal-400 text-sm">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : (
        <>
          <DemoModeToggle integrations={integrations} qc={qc} />
          <PlatformCard
            platform="instagram"
            label="Instagram"
            color="from-pink-500 to-purple-600"
            webhookUrl={integrations?.instagram?.webhook_url || ''}
            connected={integrations?.instagram?.connected}
            demo={integrations?.demo_mode}
            qc={qc}
          />
          <PlatformCard
            platform="tiktok"
            label="TikTok"
            color="from-black to-charcoal-700"
            webhookUrl={integrations?.tiktok?.webhook_url || ''}
            connected={integrations?.tiktok?.connected}
            demo={integrations?.demo_mode}
            qc={qc}
          />
          <MakeSetupGuide />
        </>
      )}
    </div>
  )
}

// ── Demo mode toggle ──────────────────────────────────────────────────────────

function DemoModeToggle({ integrations, qc }) {
  const mutation = useMutation({
    mutationFn: (demo) => api.updateIntegrations({ demo_mode: demo }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations'] }),
  })

  const demo = integrations?.demo_mode ?? true

  return (
    <div className="card flex items-center justify-between gap-4">
      <div>
        <p className="font-semibold text-charcoal-900 text-sm">Demo Mode</p>
        <p className="text-xs text-charcoal-400 mt-0.5">
          When on, all posts are simulated — nothing is sent to Instagram or TikTok.
          Turn off only after adding your webhook URLs below.
        </p>
      </div>
      <button
        onClick={() => mutation.mutate(!demo)}
        disabled={mutation.isPending}
        className={clsx(
          'relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none',
          demo ? 'bg-amber-400' : 'bg-brand-500'
        )}
      >
        <span
          className={clsx(
            'inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200',
            demo ? 'translate-x-0' : 'translate-x-5'
          )}
        />
      </button>
    </div>
  )
}

// ── Per-platform card ─────────────────────────────────────────────────────────

function PlatformCard({ platform, label, color, webhookUrl, connected, demo, qc }) {
  const [url, setUrl] = useState(webhookUrl)
  const [show, setShow] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const saveMutation = useMutation({
    mutationFn: (newUrl) =>
      api.updateIntegrations({ [`${platform}_webhook_url`]: newUrl }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations'] }),
  })

  const handleTest = async () => {
    if (!url) return
    setTesting(true)
    setTestResult(null)
    const result = await api.testWebhook({ url })
    setTestResult(result)
    setTesting(false)
  }

  const statusColor = connected ? 'text-green-600' : demo ? 'text-amber-500' : 'text-charcoal-400'
  const statusLabel = connected ? 'Connected' : demo ? 'Demo Mode' : 'Not connected'
  const StatusIcon = connected ? CheckCircle2 : demo ? Zap : XCircle

  return (
    <div className="card space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className={clsx('w-9 h-9 rounded-xl bg-gradient-to-br flex items-center justify-center', color)}>
          <span className="text-white font-bold text-sm">{label[0]}</span>
        </div>
        <div className="flex-1">
          <p className="font-semibold text-charcoal-900">{label}</p>
          <div className={clsx('flex items-center gap-1 text-xs font-medium', statusColor)}>
            <StatusIcon size={12} />
            {statusLabel}
          </div>
        </div>
      </div>

      {/* Webhook URL input */}
      <div>
        <label className="text-xs font-medium text-charcoal-600 block mb-1.5">
          Make.com Webhook URL
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type={show ? 'text' : 'password'}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://hook.eu2.make.com/..."
              className="w-full text-sm border border-charcoal-200 rounded-xl px-3 py-2 pr-10 focus:outline-none focus:ring-1 focus:ring-brand-400"
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-charcoal-400 hover:text-charcoal-600"
            >
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button
            onClick={() => saveMutation.mutate(url)}
            disabled={saveMutation.isPending || url === webhookUrl}
            className="btn-primary text-sm px-4 whitespace-nowrap"
          >
            {saveMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Save'}
          </button>
        </div>
        {saveMutation.isSuccess && (
          <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
            <CheckCircle2 size={11} /> Saved
          </p>
        )}
      </div>

      {/* Test button */}
      {url && (
        <div>
          <button
            onClick={handleTest}
            disabled={testing}
            className="text-sm text-brand-600 font-medium hover:underline flex items-center gap-1"
          >
            {testing ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
            Send test ping to Make.com
          </button>
          {testResult && (
            <div className={clsx(
              'mt-2 text-xs rounded-lg px-3 py-2',
              testResult.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            )}>
              {testResult.ok
                ? `Webhook responded with HTTP ${testResult.status_code} — Make.com received your ping.`
                : `Failed: ${testResult.error}`}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Make.com setup guide ──────────────────────────────────────────────────────

function MakeSetupGuide() {
  const [open, setOpen] = useState(false)

  return (
    <div className="card">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Link2 size={15} className="text-brand-500" />
          <span className="font-semibold text-charcoal-900 text-sm">How to set up Make.com</span>
        </div>
        {open ? <ChevronDown size={16} className="text-charcoal-400" /> : <ChevronRight size={16} className="text-charcoal-400" />}
      </button>

      {open && (
        <div className="mt-4 space-y-5 text-sm text-charcoal-700">

          {/* Instagram steps */}
          <div>
            <p className="font-semibold text-charcoal-900 mb-2">Instagram Scenario</p>
            <ol className="space-y-2 list-none">
              {[
                <>Go to <ExternalHref href="https://make.com">make.com</ExternalHref> and create a free account.</>,
                'Click "Create a new scenario".',
                'Add a Webhooks module → choose "Custom webhook" → click Add → copy the URL it gives you.',
                'Add a second module: search for "Instagram for Business" → choose "Create a Photo/Video Post".',
                'Map the webhook fields: use the video_url, caption, and audio_name variables from the webhook payload.',
                'Turn the scenario ON (toggle in the bottom left).',
                'Paste the webhook URL into the Instagram field above and click Save.',
              ].map((step, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* TikTok steps */}
          <div>
            <p className="font-semibold text-charcoal-900 mb-2">TikTok Scenario</p>
            <ol className="space-y-2 list-none">
              {[
                'Create another new scenario in Make.com.',
                'Add a Webhooks module → "Custom webhook" → copy the new URL.',
                'Add a second module: search for "TikTok" → choose "Upload a Video".',
                'Map video_url and caption from the webhook payload.',
                'Turn the scenario ON and paste the URL into the TikTok field above.',
              ].map((step, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-charcoal-100 text-charcoal-700 text-xs font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800">
            Once both URLs are saved and tested, turn Demo Mode off above. Your agent will then publish real posts automatically.
          </div>
        </div>
      )}
    </div>
  )
}

function ExternalHref({ href, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-brand-600 underline inline-flex items-center gap-0.5"
    >
      {children}<ExternalLink size={11} />
    </a>
  )
}
