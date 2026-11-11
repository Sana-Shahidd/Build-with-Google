import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BookOpen, LogIn, MonitorCheck, ShieldCheck, Siren, UserRound } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { LanguageToggle } from '@/components/LanguageToggle'
import { VideoBackdrop } from '@/components/VideoBackdrop'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RESPONDER_ROLES } from '@/hooks/useRole'
import { supabase } from '@/lib/supabase'

type Mode = 'choose' | 'dispatcher' | 'control'

const cardClass =
  'w-full border border-[#2F7FB8]/20 bg-[#FFFBF2]/80 p-4 text-[#12324A] shadow-2xl backdrop-blur-sm'

/** Entry page: bystander goes straight to the app; dispatcher and control room sign in (docs/09 section 3.7). */
export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>('choose')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password })
    if (authError || !data.user) {
      setError(t('login.error'))
      setBusy(false)
      return
    }
    const { data: profile } = await supabase.from('profiles').select('role').eq('id', data.user.id).single()
    const allowed =
      profile && (mode === 'control' ? profile.role === 'admin' : RESPONDER_ROLES.includes(profile.role) && profile.role !== 'admin')
    if (!allowed) {
      await supabase.auth.signOut()
      setError(t(mode === 'control' ? 'login.notControl' : 'login.forbidden'))
      setBusy(false)
      return
    }
    await queryClient.invalidateQueries({ queryKey: ['profile'] })
    navigate(mode === 'control' ? '/control-room' : '/dashboard')
  }

  const roles = [
    { key: 'dispatcher' as const, icon: Siren, title: t('login.roleDispatcher'), desc: t('login.roleDispatcherDesc'), tone: 'bg-[#CFE6F6]' },
    { key: 'bystander' as const, icon: UserRound, title: t('login.roleBystander'), desc: t('login.roleBystanderDesc'), tone: 'bg-[#FCE2E0]' },
    { key: 'control' as const, icon: MonitorCheck, title: t('login.roleControl'), desc: t('login.roleControlDesc'), tone: 'bg-[#E9E3FA]' },
  ]

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-4 text-[#12324A]">
      <VideoBackdrop visible />
      <div className="flex items-center gap-2 text-white drop-shadow">
        <ShieldCheck className="size-9 text-[#F2C14E]" strokeWidth={1.6} />
        <div>
          <p className="text-lg font-extrabold leading-tight">{t('app.name')}</p>
          <p className="text-[11px] text-white/85">{t('dash.tagline')}</p>
        </div>
      </div>
      {mode === 'choose' ? (
        <Card className={`${cardClass} max-w-xl gap-3`}>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-base font-extrabold">{t('login.chooseTitle')}</h1>
              <p className="text-xs text-[#4F6E84]">{t('login.chooseSub')}</p>
            </div>
            <LanguageToggle />
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {roles.map(({ key, icon: Icon, title, desc, tone }) => (
              <button
                key={key}
                type="button"
                onClick={() => (key === 'bystander' ? navigate('/') : setMode(key))}
                className="flex flex-col items-start gap-2 rounded-xl border border-[#2F7FB8]/20 bg-white/80 p-3 text-start shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <span className={`grid size-9 place-items-center rounded-full ${tone}`}>
                  <Icon className="size-5" />
                </span>
                <span className="text-sm font-extrabold">{title}</span>
                <span className="text-xs text-[#4F6E84]">{desc}</span>
              </button>
            ))}
          </div>
          <button type="button" onClick={() => navigate('/guide')} className="flex items-center gap-2 self-start text-xs font-semibold text-[#2F7FB8]">
            <BookOpen className="size-4" /> {t('dash.guideNav')}
          </button>
        </Card>
      ) : (
        <Card className={`${cardClass} max-w-xs gap-3`}>
          <div className="flex items-center justify-between">
            <h1 className="text-base font-extrabold">{t(mode === 'control' ? 'login.controlTitle' : 'login.dispatcherTitle')}</h1>
            <LanguageToggle />
          </div>
          <form onSubmit={(e) => void submit(e)} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="email">{t('login.email')}</Label>
              <Input className="border-[#2F7FB8]/40 bg-white/80 text-[#12324A]" id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">{t('login.password')}</Label>
              <Input className="border-[#2F7FB8]/40 bg-white/80 text-[#12324A]" id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            {error && <p className="text-sm text-escalated" role="alert">{error}</p>}
            <Button type="submit" className="w-full bg-[#2F7FB8] text-[#FFF8EA] hover:bg-[#256a9c]" disabled={busy}>
              <LogIn /> {t('login.submit')}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => { setMode('choose'); setError(null) }}>
              <ArrowLeft /> {t('login.back')}
            </Button>
          </form>
        </Card>
      )}
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 rounded-full bg-[#0B2A4A]/70 px-4 py-1.5 text-[11px] font-semibold text-white backdrop-blur-sm">
        <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-[#4C8DF6]" /> {t('login.legend.reporter')}</span>
        <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full border-2 border-[#E11D2E]" /> {t('login.legend.incident')}</span>
        <span className="flex items-center gap-1.5"><span className="grid size-3 place-items-center rounded-full bg-[#2DD4A0] text-[9px] font-black leading-none text-[#0B2A4A]">+</span> {t('login.legend.hospital')}</span>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-[#2DD4A0]" /> {t('login.legend.route')}</span>
      </div>
    </div>
  )
}
