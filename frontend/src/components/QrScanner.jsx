import { useEffect, useRef, useState } from 'react'
import { Modal } from './ui'

/**
 * Camera QR reader built on the browser's native BarcodeDetector, so the app
 * ships no scanning library. Where the API is missing (Safari, Firefox) the
 * guard is told to use a USB scanner or type the code - both still work,
 * because a hardware scanner just types the payload into the search box.
 */
export function QrScanner({ onDetected, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState('')
  const supported = typeof window !== 'undefined' && 'BarcodeDetector' in window

  useEffect(() => {
    if (!supported) return undefined
    let cancelled = false
    let frame = null
    let detector

    async function start() {
      try {
        detector = new window.BarcodeDetector({ formats: ['qr_code'] })
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
        })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        tick()
      } catch (err) {
        if (!cancelled) {
          setError(
            err.name === 'NotAllowedError'
              ? 'Camera permission was refused. Allow it in the browser, or type the code instead.'
              : 'Could not start the camera on this device.',
          )
        }
      }
    }

    async function tick() {
      if (cancelled || !videoRef.current) return
      try {
        const codes = await detector.detect(videoRef.current)
        if (codes.length) {
          onDetected(codes[0].rawValue)
          return
        }
      } catch {
        // A dropped frame is normal; keep looking.
      }
      frame = requestAnimationFrame(tick)
    }

    start()
    return () => {
      cancelled = true
      if (frame) cancelAnimationFrame(frame)
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [supported, onDetected])

  return (
    <Modal title="Scan the QR sticker" onClose={onClose}>
      {!supported ? (
        <div className="note note-warn">
          This browser has no built-in QR reader. Use a USB barcode scanner (it types straight
          into the search box) or read the serial number aloud and type it in. Chrome and Edge on
          Android support the camera scanner.
        </div>
      ) : error ? (
        <div className="note note-error">{error}</div>
      ) : (
        <>
          <video
            ref={videoRef}
            style={{ width: '100%', borderRadius: 10, background: '#000' }}
            muted
            playsInline
          />
          <p className="muted" style={{ fontSize: 13 }}>
            Hold the sticker on the laptop steady inside the frame.
          </p>
        </>
      )}
    </Modal>
  )
}
