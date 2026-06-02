import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scissors } from 'lucide-react'

const PASSWORD = 'Noelzy0528'

export default function Login() {
  const navigate = useNavigate()
  const [value, setValue] = useState('')
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
      setValue('')
      setTimeout(() => setShake(false), 500)
    }
  }

  return (
    <div className="min-h-screen bg-charcoal-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-brand-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Scissors size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-charcoal-900">EASTEND</h1>
          <p className="text-charcoal-400 text-sm mt-1">Social Media Agent</p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className={`bg-white rounded-2xl shadow-sm border border-charcoal-100 p-8 space-y-4 ${shake ? 'animate-shake' : ''}`}
        >
          <div>
            <label className="block text-sm font-medium text-charcoal-700 mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={value}
              onChange={(e) => { setValue(e.target.value); setError(false) }}
              placeholder="Enter your password"
              autoFocus
              className={`w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 transition-colors ${
                error
                  ? 'border-red-300 focus:ring-red-200 bg-red-50'
                  : 'border-charcoal-200 focus:ring-brand-200'
              }`}
            />
            {error && (
              <p className="text-red-500 text-xs mt-1.5">Incorrect password. Try again.</p>
            )}
          </div>

          <button
            type="submit"
            className="btn-primary w-full py-3"
          >
            Sign In
          </button>
        </form>

        <p className="text-center text-xs text-charcoal-300 mt-6">
          EASTEND Salon · East London
        </p>
      </div>
    </div>
  )
}
