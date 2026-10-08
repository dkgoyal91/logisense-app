import QRCode from 'qrcode'
import { useEffect, useState } from 'react'

const QR_OPTIONS = { margin: 1, width: 520, color: { dark: '#0b1430', light: '#ffffff' } }

export function useQrDataUrl(text: string): string | null {
  const [dataUrl, setDataUrl] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    QRCode.toDataURL(text, QR_OPTIONS)
      .then((url) => active && setDataUrl(url))
      .catch(() => active && setDataUrl(null))
    return () => {
      active = false
    }
  }, [text])
  return dataUrl
}
