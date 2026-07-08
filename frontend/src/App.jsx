import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import './App.css'

const API = ''

async function api(path, options) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

function usePywebview() {
  return typeof window !== 'undefined' && window.pywebview?.api
}

export default function App() {
  const pyApi = usePywebview()
  const logRef = useRef(null)
  const [tab, setTab] = useState('translate')
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('idle')
  const [statusMsg, setStatusMsg] = useState('就绪')
  const [running, setRunning] = useState(false)
  const [changelog, setChangelog] = useState([])

  const [inputFile, setInputFile] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [outputName, setOutputName] = useState('')
  const [deeplKey, setDeeplKey] = useState('')
  const [mode, setMode] = useState('zh_to_fr')
  const [translateBlocks, setTranslateBlocks] = useState(false)

  useEffect(() => {
    api('/api/config').then((c) => setDeeplKey(c.deepl_key || '')).catch(() => {})
    api('/api/changelog').then((d) => setChangelog(d.changelog || [])).catch(() => {})
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      api('/api/config', { method: 'POST', body: JSON.stringify({ deepl_key: deeplKey }) }).catch(() => {})
    }, 600)
    return () => clearTimeout(timer)
  }, [deeplKey])

  useEffect(() => {
    const es = new EventSource(`${API}/api/logs/stream`)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'status') {
          setStatus(data.status)
          setStatusMsg(data.message || '')
          setRunning(data.status === 'running')
        } else if (data.type === 'log') {
          setLogs((prev) => [...prev.slice(-500), data.message])
        }
      } catch {
        /* ignore */
      }
    }
    return () => es.close()
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  const pickInput = useCallback(async () => {
    if (pyApi?.pick_dxf_file) {
      const r = await pyApi.pick_dxf_file()
      if (r.path) {
        setInputFile(r.path)
        if (!outputDir) setOutputDir(r.dir)
        const prefix = mode === 'zh_to_fr' ? 'fr' : 'zh'
        const ts = new Date().toLocaleString('en-GB').replace(/[/,: ]/g, '-').slice(0, 16)
        setOutputName(`${prefix}_${r.base}_${ts}`)
      }
      return
    }
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.dxf'
    input.onchange = () => {
      const f = input.files?.[0]
      if (f) setInputFile(f.name)
    }
    input.click()
  }, [pyApi, mode, outputDir])

  const pickOutput = useCallback(async () => {
    if (pyApi?.pick_output_dir) {
      const r = await pyApi.pick_output_dir()
      if (r.path) setOutputDir(r.path)
    }
  }, [pyApi])

  const startTranslate = async () => {
    try {
      setRunning(true)
      setStatus('running')
      setLogs((p) => [...p, '提交翻译任务...'])
      await api('/api/translate', {
        method: 'POST',
        body: JSON.stringify({
          input_file: inputFile,
          output_dir: outputDir,
          output_name: outputName,
          translation_mode: mode,
          translate_blocks: translateBlocks,
          deepl_key: deeplKey,
        }),
      })
    } catch (e) {
      setRunning(false)
      setStatus('error')
      setStatusMsg(e.message)
      setLogs((p) => [...p, `ERROR: ${e.message}`])
    }
  }

  const statusColor = {
    idle: '#94a3b8',
    running: '#38bdf8',
    success: '#34d399',
    error: '#f87171',
  }[status] || '#94a3b8'

  return (
    <div className="app-shell">
      <div className="bg-orbs">
        <motion.div className="orb orb-a" animate={{ x: [0, 40, 0], y: [0, -30, 0] }} transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb orb-b" animate={{ x: [0, -50, 0], y: [0, 40, 0] }} transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="orb orb-c" animate={{ scale: [1, 1.15, 1] }} transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }} />
      </div>

      <motion.header className="glass topbar" initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
        <div className="brand">
          <motion.span className="brand-icon" animate={{ rotate: [0, 8, -8, 0] }} transition={{ duration: 4, repeat: Infinity }}>⬡</motion.span>
          <div>
            <h1>Honsen CAD 中法互译</h1>
            <p>DeepL · 半透明毛玻璃界面</p>
          </div>
        </div>
        <div className="tabs">
          {['translate', 'changelog'].map((t) => (
            <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
              {t === 'translate' ? '翻译' : '更新日志'}
            </button>
          ))}
        </div>
      </motion.header>

      <main className="main-area">
        <AnimatePresence mode="wait">
          {tab === 'translate' ? (
            <motion.div key="translate" className="translate-grid" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.35 }}>
              <section className="glass panel">
                <h2>文件</h2>
                <Field label="DXF 输入">
                  <div className="row">
                    <input readOnly value={inputFile} placeholder="选择 .dxf 文件" />
                    <motion.button className="btn secondary" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={pickInput}>浏览</motion.button>
                  </div>
                </Field>
                <Field label="输出目录">
                  <div className="row">
                    <input readOnly value={outputDir} placeholder="选择输出文件夹" />
                    <motion.button className="btn secondary" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={pickOutput}>浏览</motion.button>
                  </div>
                </Field>
                <Field label="输出文件名">
                  <div className="row suffix-row">
                    <input value={outputName} onChange={(e) => setOutputName(e.target.value)} placeholder="translated_cad" />
                    <span className="suffix">.dxf</span>
                  </div>
                </Field>
              </section>

              <section className="glass panel">
                <h2>选项</h2>
                <div className="mode-group">
                  {[
                    { v: 'zh_to_fr', l: '中文 → 法语' },
                    { v: 'fr_to_zh', l: '法语 → 中文' },
                  ].map((m) => (
                    <motion.button key={m.v} className={`chip ${mode === m.v ? 'on' : ''}`} whileTap={{ scale: 0.96 }} onClick={() => setMode(m.v)}>
                      {m.l}
                    </motion.button>
                  ))}
                </div>
                <label className="check">
                  <input type="checkbox" checked={translateBlocks} onChange={(e) => setTranslateBlocks(e.target.checked)} />
                  <span>翻译所有块定义（含未使用的符号块）</span>
                </label>
                <p className="hint">图框/标题栏会自动从块引用提取，通常无需勾选</p>
              </section>

              <section className="glass panel">
                <h2>DeepL API</h2>
                <Field label="API Key">
                  <input type="password" value={deeplKey} onChange={(e) => setDeeplKey(e.target.value)} placeholder="输入 DeepL API Key" />
                </Field>
                <motion.button className="btn primary full" disabled={running} whileHover={running ? {} : { scale: 1.02, boxShadow: '0 8px 32px rgba(56,189,248,0.35)' }} whileTap={running ? {} : { scale: 0.98 }} onClick={startTranslate}>
                  {running ? (
                    <span className="loading"><span className="dot" /><span className="dot" /><span className="dot" />翻译中...</span>
                  ) : '开始翻译'}
                </motion.button>
              </section>

              <section className="glass panel log-panel">
                <div className="log-head">
                  <h2>实时日志</h2>
                  <button className="btn ghost" onClick={() => setLogs([])}>清除</button>
                </div>
                <div className="log-box" ref={logRef}>
                  <AnimatePresence initial={false}>
                    {logs.map((line, i) => (
                      <motion.div key={`${i}-${line.slice(0, 24)}`} className="log-line" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2 }}>
                        {line}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {logs.length === 0 && <p className="log-empty">等待任务...</p>}
                </div>
              </section>
            </motion.div>
          ) : (
            <motion.div key="changelog" className="glass panel changelog-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
              <h2>版本更新历史</h2>
              <div className="changelog-list">
                {changelog.map((entry, idx) => (
                  <motion.article key={entry.version} className="changelog-item" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.06 }}>
                    <header>
                      <strong>v{entry.version}</strong>
                      <span>{entry.date}</span>
                      {entry.title && <em>{entry.title}</em>}
                    </header>
                    <ul>
                      {(entry.content || []).filter(Boolean).map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                  </motion.article>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="glass statusbar">
        <motion.span className="status-dot" animate={{ backgroundColor: statusColor }} />
        <span>{statusMsg || '就绪'}</span>
        <span className="footer-meta">Etienne · etn@live.com</span>
      </footer>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}
