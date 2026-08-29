"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { FileUp, KeyRound, Loader2, TriangleAlert, X, RotateCcw } from "lucide-react"
import { API_URL } from "@/lib/pipeline"
import type { PipelineSummary, Transaction } from "@/lib/pipeline/types"
import { cn } from "@/lib/utils"

export interface UploadResult {
  transactions: Transaction[]
  summary: PipelineSummary
  filename: string
  uploadId: string
  modelVersion?: string
}

const API_KEY_STORAGE_KEY = "afc_api_key"
const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 2 * 60 * 1000

async function parseErrorDetail(res: Response): Promise<string[]> {
  const body = await res.json().catch(() => null)
  const detail = body?.detail
  if (Array.isArray(detail?.errors)) return detail.errors
  if (typeof detail === "string") return [detail]
  return ["Upload failed. Please check the file and try again."]
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function UploadPanel({
  onResult,
  onReset,
  active,
}: {
  onResult: (result: UploadResult) => void
  onReset: () => void
  active: boolean
}) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [error, setError] = useState<string[] | null>(null)
  const [filename, setFilename] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState("")
  const [showKeyField, setShowKeyField] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const saved = window.localStorage.getItem(API_KEY_STORAGE_KEY)
    if (saved) {
      setApiKey(saved)
      setShowKeyField(true)
    }
  }, [])

  const persistApiKey = (value: string) => {
    setApiKey(value)
    if (value) window.localStorage.setItem(API_KEY_STORAGE_KEY, value)
    else window.localStorage.removeItem(API_KEY_STORAGE_KEY)
  }

  const authHeaders = useCallback(
    (): Record<string, string> => (apiKey ? { "X-API-Key": apiKey } : {}),
    [apiKey],
  )

  const fetchFinishedUpload = useCallback(
    async (uploadId: string, fallbackFilename: string) => {
      const res = await fetch(`${API_URL}/api/upload/${uploadId}`, {
        headers: authHeaders(),
      })
      if (!res.ok) {
        setError(await parseErrorDetail(res))
        return
      }
      const data = await res.json()
      onResult({
        transactions: data.transactions,
        summary: data.summary,
        filename: data.filename ?? fallbackFilename,
        uploadId,
        modelVersion: data.modelVersion,
      })
    },
    [authHeaders, onResult],
  )

  const pollJob = useCallback(
    async (uploadId: string, fallbackFilename: string) => {
      const deadline = Date.now() + POLL_TIMEOUT_MS
      while (Date.now() < deadline) {
        await sleep(POLL_INTERVAL_MS)
        const res = await fetch(`${API_URL}/api/jobs/${uploadId}`, {
          headers: authHeaders(),
        })
        if (!res.ok) {
          setError(await parseErrorDetail(res))
          return
        }
        const job = await res.json()
        if (job.status === "DONE") {
          setProgress("Finalizing…")
          await fetchFinishedUpload(uploadId, fallbackFilename)
          return
        }
        if (job.status === "FAILED") {
          setError([job.error ?? "Scoring failed."])
          return
        }
        setProgress(
          job.rowCount
            ? `Scoring ${job.rowCount.toLocaleString()} rows in the background…`
            : "Scoring in the background…",
        )
      }
      setError(["Scoring is taking longer than expected. Check back at /api/jobs/" + uploadId + " shortly."])
    },
    [authHeaders, fetchFinishedUpload],
  )

  const upload = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".csv")) {
        setError(["Only .csv files are accepted."])
        return
      }

      setLoading(true)
      setError(null)
      setProgress("Uploading…")

      try {
        const formData = new FormData()
        formData.append("file", file)

        const res = await fetch(`${API_URL}/api/upload`, {
          method: "POST",
          headers: authHeaders(),
          body: formData,
        })

        if (res.status === 401) {
          setError(["This backend requires an API key. Enter yours below and try again."])
          setShowKeyField(true)
          return
        }

        if (res.status === 429) {
          const retryAfter = res.headers.get("Retry-After")
          const body = await res.json().catch(() => null)
          setError([
            body?.detail ??
              `Rate limit exceeded.${retryAfter ? ` Try again in ${retryAfter}s.` : ""}`,
          ])
          return
        }

        if (!res.ok) {
          setError(await parseErrorDetail(res))
          return
        }

        const data = await res.json()
        setFilename(file.name)

        if (data.status === "PROCESSING") {
          setProgress(data.message ?? "Scoring in the background…")
          await pollJob(data.uploadId, file.name)
          return
        }

        onResult({
          transactions: data.transactions,
          summary: data.summary,
          filename: data.filename ?? file.name,
          uploadId: data.uploadId,
          modelVersion: data.modelVersion,
        })
      } catch {
        setError([
          "Couldn't reach the scoring backend. Make sure api_server.py is running and NEXT_PUBLIC_API_URL points to it.",
        ])
      } finally {
        setLoading(false)
        setProgress(null)
      }
    },
    [authHeaders, onResult, pollJob],
  )

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return
      upload(files[0])
    },
    [upload],
  )

  return (
    <div className="rounded-xl border border-border bg-card/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Score your own payments file</h2>
          <p className="text-xs text-muted-foreground">
            CSV with <code className="rounded bg-muted px-1 py-0.5">payment_id</code>,{" "}
            <code className="rounded bg-muted px-1 py-0.5">payment_amount</code>,{" "}
            <code className="rounded bg-muted px-1 py-0.5">actual_settlement</code> required.
            fee / tax / refund / adjustment optional (default 0).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowKeyField((s) => !s)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium",
              apiKey
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-border bg-muted/40 text-muted-foreground hover:bg-muted",
            )}
          >
            <KeyRound className="size-3.5" aria-hidden />
            {apiKey ? "API key set" : "API key"}
          </button>
          {active && (
            <button
              type="button"
              onClick={() => {
                setFilename(null)
                setError(null)
                onReset()
              }}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted"
            >
              <RotateCcw className="size-3.5" aria-hidden />
              Back to demo data
            </button>
          )}
        </div>
      </div>

      {showKeyField && (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="password"
            placeholder="X-API-Key (leave blank if the backend has no auth)"
            value={apiKey}
            onChange={(e) => persistApiKey(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs outline-none focus:border-primary/50"
          />
        </div>
      )}

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        className={cn(
          "mt-3 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/40",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        {loading ? (
          <>
            <Loader2 className="size-6 animate-spin text-primary" aria-hidden />
            <p className="text-sm text-muted-foreground">
              {progress ?? "Running reconciliation → duplicate → anomaly → risk → decision pipeline…"}
            </p>
          </>
        ) : (
          <>
            <FileUp className="size-6 text-muted-foreground" aria-hidden />
            <p className="text-sm">
              {filename ? (
                <span className="font-medium text-foreground">{filename}</span>
              ) : (
                <>
                  <span className="font-medium text-primary">Click to upload</span> or drag and drop a CSV
                </>
              )}
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-xs text-risk-critical">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          <div className="space-y-0.5">
            {error.map((msg, i) => (
              <p key={i}>{msg}</p>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-auto shrink-0 text-risk-critical/70 hover:text-risk-critical"
            aria-label="Dismiss error"
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
