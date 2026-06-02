import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Eye, EyeOff } from 'lucide-react'

const PASSWORD = 'Noelzy0528'

export default function Login() {
  const navigate = useNavigate()
  const [value, setValue] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState(false)
  const [shake, setShake] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (value === PASSWORD) {
      localStorage.setItem('eastend_auth', 'true')
      navigate('/dashboard', { replace: true })
    } else {
      setError(true)
      setShake(true)
      setTimeout(() => setShake(false), 500)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#0d1a2d' }}>
      <div className="w-full max-w-sm">

        {/* Icon + title */}
        <div className="text-center mb-8">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5"
            style={{ background: '#1e3a5f' }}
          >
            <Lock size={28} style={{ color: '#e67a57' }} />
          </div>
          <h1 className="text-2xl font-bold text-white">EASTEND Agent</h1>
          <p className="text-sm mt-1" style={{ color: '#8899aa' }}>Sign in to your dashboard</p>
        </div>

        {/* Card */}
        <div
          className={`rounded-2xl p-8 space-y-4 ${shake ? 'animate-shake' : ''}`}
          style={{ background: '#142038' }}
        >
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: '#c8d8e8' }}>
              Password
            </label>
            <div className="relative">
              <input
                type={show ? 'text' : 'password'}
                value={value}
                onChange={(e) => { setValue(e.target.value); setError(false) }}
                placeholder="••••••••••"
                autoFocus
                className="w-full rounded-xl px-4 py-3 pr-11 text-sm focus:outline-none focus:ring-2 text-white"
                style={{
                  background: error ? '#2a1520' : '#ffffff',
                  color: error ? '#fff' : '#000',
                  border: error ? '1.5px solid #e67a57' : '1.5px solid #2a3f5f',
                  focusRingColor: '#e67a57',
                }}
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShow(!show)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: '#8899aa' }}
              >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {error && (
              <div
                className="mt-3 rounded-xl px-4 py-3 text-sm font-medium"
                style={{ background: '#2a1520', border: '1.5px solid #e67a57', color: '#e67a57' }}
              >
                Incorrect password. Try again.
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            className="w-full py-3 rounded-xl font-semibold text-sm transition-opacity hover:opacity-90"
            style={{ background: '#e67a57', color: '#fff' }}
          >
            Sign in
          </button>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: '#4a6080' }}>
          EASTEND Well St · Data protected under UK GDPR
        </p>
      </div>
    </div>
  )
}
