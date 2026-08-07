import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Iridescence from "./components/Iridescence";
import "./App.css";
const IRIDESCENCE_COLOR = [0.22, 0.38, 0.92];
const versions = [
  ["", "保持默认"],
  ["ACAD9", "AutoCAD R9"],
  ["ACAD10", "AutoCAD R10"],
  ["ACAD12", "AutoCAD R12"],
  ["ACAD13", "AutoCAD R13"],
  ["ACAD14", "AutoCAD R14"],
  ["ACAD2000", "AutoCAD 2000"],
  ["ACAD2004", "AutoCAD 2004"],
  ["ACAD2007", "AutoCAD 2007"],
  ["ACAD2010", "AutoCAD 2010"],
  ["ACAD2013", "AutoCAD 2013"],
  ["ACAD2018", "AutoCAD 2018"],
];
const modes = [
  ["zh_to_fr", "中文 → 法语"],
  ["fr_to_zh", "法语 → 中文"],
  ["zh_to_en", "中文 → 英语"],
  ["en_to_zh", "英语 → 中文"],
];
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.12 },
  },
};
const itemVariants = {
  hidden: { opacity: 0, y: 22, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 260, damping: 22 },
  },
};
async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok)
    throw new Error(
      (await res.json().catch(() => ({}))).detail || res.statusText,
    );
  return res.json();
}
function usePywebview() {
  return typeof window !== "undefined" && window.pywebview?.api;
}
function Field({ label, children }) {
  return (
    <div className="field">
      <span>{label}</span>
      {children}
    </div>
  );
}
function SelectMenu({ value, onChange, options }) {
  const selected = options.find(([optionValue]) => optionValue === value)?.[1];
  return (
    <details className="select-menu">
      <summary>{selected}<span aria-hidden="true">⌄</span></summary>
      <div className="select-options" role="listbox">
        {options.map(([optionValue, optionLabel]) => (
          <button
            type="button"
            className={optionValue === value ? "selected" : ""}
            key={optionValue}
            onClick={(event) => {
              onChange(optionValue);
              event.currentTarget.closest("details").removeAttribute("open");
            }}
          >
            {optionLabel}
          </button>
        ))}
      </div>
    </details>
  );
}
export default function App() {
  const pyApi = usePywebview();
  const [batch, setBatch] = useState({
    tasks: [],
    progress: 0,
    paused: false,
    started: false,
    resumable: false,
  });
  const [logs, setLogs] = useState([]);
  const [outputDir, setOutputDir] = useState("");
  const [mode, setMode] = useState("zh_to_fr");
  const [format, setFormat] = useState("source");
  const [version, setVersion] = useState("");
  const [blocks, setBlocks] = useState(false);
  const [key, setKey] = useState("");
  const logRef = useRef();
  const refresh = useCallback(
    () =>
      api("/api/batch")
        .then(setBatch)
        .catch(() => {}),
    [],
  );
  useEffect(() => {
    api("/api/config")
      .then((c) => {
        setKey(c.deepl_key || "");
        setOutputDir(c.output_dir || "");
      })
      .catch(() => {});
    refresh();
    const t = setInterval(refresh, 1000);
    return () => clearInterval(t);
  }, [refresh]);
  useEffect(() => {
    const es = new EventSource("/api/logs/stream");
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "log") setLogs((p) => [...p.slice(-499), d.message]);
      } catch {}
    };
    return () => es.close();
  }, []);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);
  const action = async (path, body) => {
    try {
      await api(path, {
        method: "POST",
        ...(body && { body: JSON.stringify(body) }),
      });
      refresh();
    } catch (e) {
      setLogs((p) => [...p, `ERROR: ${e.message}`]);
    }
  };
  const settings = () => ({
    output_dir: outputDir,
    translation_mode: mode,
    translate_blocks: blocks,
    output_format: format,
    output_version: version,
    deepl_key: key,
  });
  const chooseFiles = async () => {
    const r = await pyApi?.pick_cad_files?.();
    if (r?.paths?.length)
      action("/api/batch/add", { files: r.paths, ...settings() });
  };
  const chooseOutput = async () => {
    const r = await pyApi?.pick_output_dir?.();
    if (r?.path) {
      setOutputDir(r.path);
      api("/api/config", {
        method: "POST",
        body: JSON.stringify({ deepl_key: key, output_dir: r.path }),
      }).catch(() => {});
    }
  };
  const toggle = () =>
    batch.started
      ? action(`/api/batch/pause?paused=${!batch.paused}`)
      : action("/api/batch/start", settings());
  const canStart = batch.tasks.some((t) =>
    ["queued", "retrying", "cancelled"].includes(t.status),
  );
  const canClear =
    !batch.started && !batch.tasks.some((t) => t.status === "running");
  const mainLabel = !batch.started
    ? batch.resumable
      ? "继续"
      : "开始翻译"
    : batch.paused
      ? "继续"
      : "暂停";
  const status = batch.tasks.some((t) => t.status === "running")
    ? "running"
    : batch.tasks.some((t) => t.status === "failed")
      ? "error"
      : "idle";
  const statusColor = { idle: "#94a3b8", running: "#38bdf8", error: "#f87171" }[
    status
  ];
  return (
    <div className="app-shell">
      <Iridescence
        color={IRIDESCENCE_COLOR}
        speed={0.85}
        amplitude={0.14}
        mouseReact
      />
      <div className="bg-vignette" />
      <div className="bg-noise" />
      <motion.header
        className="glass topbar"
        initial={{ y: -28, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
      >
        <div className="topbar-inner pywebview-drag-region">
          <div className="brand">
            <motion.span
              className="brand-icon"
              animate={{ rotate: 360 }}
              transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
            >
              ⬡
            </motion.span>
            <div className="brand-text">
              <h1>
                Honsen CAD <span className="brand-accent">中法英互译</span>
              </h1>
            </div>
          </div>
          <div className="topbar-spacer" />
          {pyApi ? (
            <div className="window-controls">
              <button
                className="win-btn"
                onClick={() => pyApi.minimize_window?.()}
              >
                <img src="/icons/minimize.png" alt="" />
              </button>
              <button
                className="win-btn win-btn-close"
                onClick={() => pyApi.close_window?.()}
              >
                <img src="/icons/close.png" alt="" />
              </button>
            </div>
          ) : (
            <div className="window-controls-spacer" />
          )}
        </div>
      </motion.header>
      <main className="main-area">
        <motion.div
          className="batch-layout"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          <motion.section className="glass queue-panel" variants={itemVariants}>
            <div className="panel-head">
              <div>
                <h2>翻译队列</h2>
                <p>
                  总体进度 {batch.progress}% · {batch.tasks.length} 个文件
                </p>
              </div>
              <div>
                <button
                  className="btn secondary"
                  disabled={!canClear}
                  onClick={() => action("/api/batch/clear")}
                >
                  清空列表
                </button>
                <button className="btn primary" onClick={chooseFiles}>
                  添加文件
                </button>
              </div>
            </div>
            <div className="progress">
              <i style={{ width: `${batch.progress}%` }} />
            </div>
            <div className="queue-list">
              <AnimatePresence initial={false}>
                {batch.tasks.map((t) => (
                  <motion.article
                    className="queue-item"
                    key={t.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                  >
                    <div>
                      <strong>{t.input_file.split(/[\\/]/).pop()}</strong>
                      <small>
                        {t.status} · 进度 {t.progress}% · {t.message}
                      </small>
                      <div className="task-progress">
                        <i style={{ width: `${t.progress}%` }} />
                      </div>
                      {t.output_file && <small>输出：{t.output_file}</small>}
                    </div>
                    <div className="item-actions">
                      {!["running", "queued", "retrying"].includes(
                        t.status,
                      ) && (
                        <button
                          className="btn ghost"
                          onClick={() => action(`/api/batch/${t.id}/retry`)}
                        >
                          重翻
                        </button>
                      )}
                      {t.status !== "running" && (
                        <button
                          className="btn ghost"
                          onClick={() => action(`/api/batch/${t.id}/remove`)}
                        >
                          移除
                        </button>
                      )}
                    </div>
                  </motion.article>
                ))}
              </AnimatePresence>
            </div>
          </motion.section>
          <motion.section className="glass log-panel" variants={itemVariants}>
            <div className="log-head">
              <div>
                <h2>实时日志</h2>
                <p className="log-sub">翻译进度与结果输出</p>
              </div>
              <button className="btn ghost" onClick={() => setLogs([])}>
                清除
              </button>
            </div>
            <div className="log-box" ref={logRef}>
              {logs.map((line, i) => (
                <motion.div
                  className="log-line"
                  key={`${i}-${line.slice(0, 32)}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  {line}
                </motion.div>
              ))}
              {!logs.length && <p className="log-empty">等待任务...</p>}
            </div>
          </motion.section>
          <motion.aside
            className="glass settings-panel"
            variants={itemVariants}
          >
            <h2>翻译设置</h2>
            <Field label="输出目录">
              <div className="row">
                <input
                  readOnly
                  value={outputDir}
                  placeholder="选择输出文件夹"
                />
                <button className="btn secondary" onClick={chooseOutput}>
                  浏览
                </button>
              </div>
            </Field>
            <div className="field">
              <span>统一翻译方向</span>
              <div className="mode-group mode-group-grid">
                {modes.map(([v, label]) => (
                  <button
                    className={`chip ${mode === v ? "on" : ""}`}
                    key={v}
                    onClick={() => setMode(v)}
                  >
                    {mode === v && (
                      <motion.span layoutId="mode-glow" className="chip-glow" />
                    )}
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            </div>
            <Field label="输出格式">
              <SelectMenu
                value={format}
                onChange={setFormat}
                options={[["source", "保持源格式"], ["dxf", "DXF"], ["dwg", "DWG"]]}
              />
            </Field>
            <Field label="输出版本（ODA）">
              <SelectMenu
                value={version}
                onChange={setVersion}
                options={versions}
              />
            </Field>
            <label className="check">
              <input
                type="checkbox"
                checked={blocks}
                onChange={(e) => setBlocks(e.target.checked)}
              />
              <span>翻译块定义中的文字</span>
            </label>
            <p className="hint">图框/标题栏会自动从块引用提取，通常无需勾选</p>
            <Field label="DeepL API Key">
              <input
                type="password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="输入 DeepL API Key"
              />
            </Field>
            <div className="queue-controls">
              <button
                className="btn primary"
                disabled={!batch.started && !canStart}
                onClick={toggle}
              >
                {mainLabel}
              </button>
              <button
                className="btn secondary"
                disabled={!batch.started}
                onClick={() => action("/api/batch/stop")}
              >
                停止
              </button>
            </div>
          </motion.aside>
        </motion.div>
      </main>
      <motion.footer className="glass statusbar">
        <motion.span
          className="status-dot"
          animate={{ backgroundColor: statusColor }}
        />
        <span>
          {batch.paused
            ? "队列已暂停"
            : status === "running"
              ? "翻译队列运行中"
              : "就绪"}
        </span>
        <span className="footer-meta">v1.7.0 · Etienne · etn@live.com</span>
      </motion.footer>
    </div>
  );
}
