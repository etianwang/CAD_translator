import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Iridescence from './components/Iridescence'
import './App.css'

const API = ''

const IRIDESCENCE_COLOR = [0.22, 0.38, 0.92]

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.12 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 22, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 260, damping: 22 },
  },
}

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

function modeOutputPrefix(mode) {
  return mode === 'zh_to_fr' ? 'fr' : 'zh'
}

function swapOutputNamePrefix(name, mode) {
  if (!name?.trim()) return name
  const target = modeOutputPrefix(mode)
  const opposite = mode === 'zh_to_fr' ? 'zh' : 'fr'
  if (name.startsWith(`${opposite}_`)) {
    return `${target}_${name.slice(opposite.length + 1)}`
  }
  if (name.startsWith(`${target}_`)) {
    return name
  }
  return name
}

export default function App() {
  const pyApi = usePywebview()
  const logRef = useRef(null)
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('idle')
  const [statusMsg, setStatusMsg] = useState('就绪')
  const [running, setRunning] = useState(false)

  const [inputFile, setInputFile] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [outputName, setOutputName] = useState('')
  const [deeplKey, setDeeplKey] = useState('')
  const [mode, setMode] = useState('zh_to_fr')
  const [translateBlocks, setTranslateBlocks] = useState(false)

  useEffect(() => {
    api('/api/config').then((c) => setDeeplKey(c.deepl_key || '')).catch(() => {})
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
        const prefix = modeOutputPrefix(mode)
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

  const selectMode = useCallback((nextMode) => {
    if (nextMode === mode) return
    setMode(nextMode)
    setOutputName((prev) => swapOutputNamePrefix(prev, nextMode))
  }, [mode])

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
      <Iridescence
        color={IRIDESCENCE_COLOR}
        speed={0.85}
        amplitude={0.14}
        mouseReact
      />
      <div className="bg-vignette" aria-hidden />
      <div className="bg-noise" aria-hidden />

      <motion.header
        className="glass topbar"
        initial={{ y: -28, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 24, delay: 0.05 }}
      >
        <div className="topbar-inner pywebview-drag-region">
          <div className="brand">
            <motion.span
              className="brand-icon"
              animate={{ rotate: 360, scale: [1, 1.06, 1] }}
              transition={{ rotate: { duration: 18, repeat: Infinity, ease: 'linear' }, scale: { duration: 3, repeat: Infinity } }}
            >
              ⬡
            </motion.span>
            <div className="brand-text">
              <h1>Honsen CAD <span className="brand-accent">中法互译</span></h1>
            </div>
          </div>
          <div className="topbar-spacer" aria-hidden />
          {pyApi ? (
            <div className="window-controls">
              <button type="button" className="win-btn" title="最小化" onClick={() => pyApi.minimize_window?.()}>
                <img src="/icons/minimize.png" alt="" draggable={false} />
              </button>
              <button type="button" className="win-btn win-btn-close" title="关闭" onClick={() => pyApi.close_window?.()}>
                <img src="/icons/close.png" alt="" draggable={false} />
              </button>
            </div>
          ) : (
            <div className="window-controls-spacer" aria-hidden />
          )}
        </div>
      </motion.header>

      <main className="main-area">
        <motion.div
          className="workspace-layout"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
              <motion.aside className="glass workspace-side" variants={itemVariants}>
                <div className="workspace-side-body">
                  <div className="workspace-section">
                    <h2>文件</h2>
                    <Field label="DXF 输入">
                      <div className="row">
                        <input readOnly value={inputFile} placeholder="选择 .dxf 文件" />
                        <motion.button type="button" className="btn secondary" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }} onClick={pickInput}>浏览</motion.button>
                      </div>
                    </Field>
                    <Field label="输出目录">
                      <div className="row">
                        <input readOnly value={outputDir} placeholder="选择输出文件夹" />
                        <motion.button type="button" className="btn secondary" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }} onClick={pickOutput}>浏览</motion.button>
                      </div>
                    </Field>
                    <Field label="输出文件名">
                      <div className="row suffix-row">
                        <input value={outputName} onChange={(e) => setOutputName(e.target.value)} placeholder="translated_cad" />
                        <span className="suffix">.dxf</span>
                      </div>
                    </Field>
                  </div>

                  <div className="workspace-section">
                    <h2>翻译设置</h2>
                    <div className="mode-group mode-group-stack">
                      {[
                        { v: 'zh_to_fr', l: '中文 → 法语' },
                        { v: 'fr_to_zh', l: '法语 → 中文' },
                      ].map((m) => (
                        <motion.button
                          key={m.v}
                          type="button"
                          className={`chip ${mode === m.v ? 'on' : ''}`}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => selectMode(m.v)}
                        >
                          {mode === m.v && <motion.span layoutId="mode-glow" className="chip-glow" transition={{ type: 'spring', stiffness: 400, damping: 28 }} />}
                          <span>{m.l}</span>
                        </motion.button>
                      ))}
                    </div>
                    <label className="check">
                      <input type="checkbox" checked={translateBlocks} onChange={(e) => setTranslateBlocks(e.target.checked)} />
                      <span>翻译所有块定义（含未使用的符号块）</span>
                    </label>
                    <p className="hint">图框/标题栏会自动从块引用提取，通常无需勾选</p>
                  </div>

                  <div className="workspace-section">
                    <h2>DeepL API</h2>
                    <Field label="API Key">
                      <input type="password" value={deeplKey} onChange={(e) => setDeeplKey(e.target.value)} placeholder="输入 DeepL API Key" />
                    </Field>
                  </div>
                </div>

                <div className="workspace-side-foot">
                  <motion.button
                    type="button"
                    className={`btn primary full ${running ? 'is-running' : ''}`}
                    disabled={running}
                    whileHover={running ? {} : { scale: 1.02, y: -1 }}
                    whileTap={running ? {} : { scale: 0.98 }}
                    onClick={startTranslate}
                  >
                    {running ? (
                      <span className="loading"><span className="dot" /><span className="dot" /><span className="dot" />翻译中...</span>
                    ) : '开始翻译'}
                  </motion.button>
                </div>
              </motion.aside>

              <motion.section className="glass workspace-log" variants={itemVariants}>
                <div className="log-head">
                  <div>
                    <h2>实时日志</h2>
                    <p className="log-sub">翻译进度与结果输出</p>
                  </div>
                  <button type="button" className="btn ghost" onClick={() => setLogs([])}>清除</button>
                </div>
                <div className="log-box" ref={logRef}>
                  <AnimatePresence initial={false}>
                    {logs.map((line, i) => (
                      <motion.div
                        key={`${i}-${line.slice(0, 32)}`}
                        className="log-line"
                        initial={{ opacity: 0, x: -12, filter: 'blur(4px)' }}
                        animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                        transition={{ duration: 0.28 }}
                      >
                        {line}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {logs.length === 0 && <p className="log-empty">等待任务...</p>}
                </div>
              </motion.section>
        </motion.div>
      </main>

      <motion.footer
        className="glass statusbar"
        initial={{ y: 24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 240, damping: 22 }}
      >
        <motion.span className="status-dot" animate={{ backgroundColor: statusColor, boxShadow: `0 0 12px ${statusColor}` }} />
        <span>{statusMsg || '就绪'}</span>
        <span className="footer-meta">Etienne · etn@live.com</span>
      </motion.footer>
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
