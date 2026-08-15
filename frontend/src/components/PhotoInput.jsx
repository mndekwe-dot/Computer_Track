import { useEffect, useRef, useState } from 'react'
import { Camera, ImageUp, RotateCcw, X } from 'lucide-react'

/**
 * Photo capture for a registration.
 *
 * A guard comparing a picture to the machine in front of them is far more
 * reliable than reading a serial off a worn sticker, so this is offered
 * wherever equipment is registered.
 *
 * On a phone, `capture="environment"` opens the camera directly, which is the
 * whole interaction for a student standing with their laptop. On a desktop the
 * same control is an ordinary file picker, plus a webcam option where the
 * browser allows it.
 *
 * Images are downscaled in the browser before upload - a modern phone photo is
 * several megabytes, and nothing here needs more than about 1000px.
 */
const MAX_EDGE = 1000
const QUALITY = 0.82

async function downscale(file) {
  if (!file.type.startsWith('image/')) return file

  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height))
    if (scale === 1 && file.size < 600 * 1024) return file

    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)

    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', QUALITY),
    )
    if (!blob) return file
    return new File([blob], file.name.replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' })
  } catch {
    // If anything about the resize fails, send the original rather than nothing.
    return file
  }
}

export function PhotoInput({ label, hint, value, onChange, existingUrl, error }) {
  const [preview, setPreview] = useState(null)
  const [cameraOn, setCameraOn] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    if (!value) {
      setPreview(null)
      return undefined
    }
    const url = URL.createObjectURL(value)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [value])

  const pick = async (event) => {
    const file = event.target.files?.[0]
    if (file) onChange(await downscale(file))
  }

  const shown = preview || existingUrl

  return (
    <div className="field">
      <span className="field-label">{label}</span>

      <div className="photo-input">
        {shown ? (
          <div className="photo-preview">
            <img src={shown} alt="" />
            <button
              type="button"
              className="photo-clear"
              onClick={() => {
                onChange(null)
                if (fileRef.current) fileRef.current.value = ''
              }}
              aria-label="Remove photo"
            >
              <X size={15} />
            </button>
          </div>
        ) : (
          <div className="photo-empty" aria-hidden="true">
            <ImageUp size={26} />
          </div>
        )}

        <div className="photo-actions">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={pick}
            className="visually-hidden"
            id={`photo-${label}`}
          />
          <label className="btn btn-outline btn-sm" htmlFor={`photo-${label}`}>
            <Camera size={15} aria-hidden="true" />
            {shown ? 'Replace photo' : 'Take or choose a photo'}
          </label>

          {'mediaDevices' in navigator && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setCameraOn(true)}
            >
              <RotateCcw size={15} aria-hidden="true" />
              Use webcam
            </button>
          )}
        </div>
      </div>

      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}

      {cameraOn && (
        <WebcamCapture
          onClose={() => setCameraOn(false)}
          onCapture={async (file) => {
            onChange(await downscale(file))
            setCameraOn(false)
          }}
        />
      )}
    </div>
  )
}

function WebcamCapture({ onCapture, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play()
        }
      })
      .catch(() => !cancelled && setError('Could not open the camera on this device.'))

    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  const shoot = () => {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => blob && onCapture(new File([blob], 'photo.jpg', { type: 'image/jpeg' })),
      'image/jpeg',
      0.9,
    )
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Take a photo">
        <header className="modal-header">
          <h2>Take a photo</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>
        <div className="modal-body">
          {error ? (
            <div className="note note-error">{error}</div>
          ) : (
            <>
              <video
                ref={videoRef}
                style={{ width: '100%', borderRadius: 10, background: '#000' }}
                muted
                playsInline
              />
              <div className="form-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose}>
                  Cancel
                </button>
                <button type="button" className="btn btn-primary" onClick={shoot}>
                  <Camera size={16} aria-hidden="true" />
                  Capture
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
