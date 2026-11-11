import { Send, Type } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'

const MAX_CHARS = 1000

/** F-04: free text in any language, from a bottom sheet. */
export function TextReportSheet({
  onSend,
  disabled,
}: {
  onSend: (text: string) => Promise<void>
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    try {
      await onSend(text.trim())
      setText('')
      setOpen(false)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button type="button" size="lg" variant="outline" disabled={disabled} className="h-24 w-full min-w-0 flex-col gap-1 whitespace-normal px-2 text-center text-base font-extrabold leading-tight">
          <Type className="size-9" />
          {t('report.type')}
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="gap-3 p-4">
        <SheetHeader className="p-0">
          <SheetTitle>{t('report.type')}</SheetTitle>
        </SheetHeader>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={MAX_CHARS}
          placeholder={t('report.placeholder')}
          className="min-h-32 text-lg"
          autoFocus
        />
        <Button
          type="button"
          size="lg"
          disabled={busy || !text.trim()}
          onClick={() => void submit()}
          className="h-16 text-xl font-extrabold"
        >
          <Send className="size-6" /> {t('report.send')}
        </Button>
      </SheetContent>
    </Sheet>
  )
}
