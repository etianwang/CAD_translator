import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Iridescence from "./components/Iridescence";
import "./App.css";
const THEMES = {
  system: { label: "果冻", color: [0.56, 0.56, 0.58] },
  magenta: { label: "紫", color: [0.68, 0.12, 0.5] },
  forest: { label: "绿", color: [0.05, 0.42, 0.37] },
};
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
  const [theme, setTheme] = useState("system");
  const [systemAccent, setSystemAccent] = useState(THEMES.system.color);
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
  const [provider, setProvider] = useState("deepl");
  const [deeplKey, setDeeplKey] = useState("");
  const [azureKey, setAzureKey] = useState("");
  const [azureRegion, setAzureRegion] = useState("");
  const [projectPackagePath, setProjectPackagePath] = useState("");
  const [showAssets, setShowAssets] = useState(false);
  const [assetTab, setAssetTab] = useState("terms");
  const [assets, setAssets] = useState({ terms: [], builtin_terms: [], memory: [], usage: {} });
  const [assetSearch, setAssetSearch] = useState("");
  const [termForm, setTermForm] = useState({ scope: "global", mode: "zh_to_fr", source: "", target: "", layer_contains: "", id: null });
  const [memoryForm, setMemoryForm] = useState({ mode: "zh_to_fr", source: "", target: "", layer_contains: "", id: null });
  const [license, setLicense] = useState({ checking: true, usable: false });
  const [activationCode, setActivationCode] = useState("");
  const [activationError, setActivationError] = useState("");
  const [support, setSupport] = useState({ licensing_enabled: false });
  const [showSupport, setShowSupport] = useState(false);
  const [draggingFiles, setDraggingFiles] = useState(false);
  const logRef = useRef();
  const refresh = useCallback(
    () =>
      api("/api/batch")
        .then(setBatch)
        .catch(() => {}),
    [],
  );
  useEffect(() => {
    const checkLicense = () => api("/api/license/status").then(setLicense).catch((error) => setLicense({ usable: false, message: error.message }));
    checkLicense();
    const timer = setInterval(checkLicense, 300000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    api("/api/support").then(setSupport).catch(() => {});
  }, []);
  useEffect(() => {
    api("/api/system-theme")
      .then((result) => {
        if (Array.isArray(result.color) && result.color.length === 3) setSystemAccent(result.color);
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (support.licensing_enabled && !license.checking && !license.usable) setShowSupport(true);
  }, [license.checking, license.usable, support.licensing_enabled]);
  useEffect(() => {
    if (!license.usable) return;
    api("/api/config")
      .then((c) => {
        setProvider(c.provider || "deepl");
        setDeeplKey(c.deepl_key || "");
        setAzureKey(c.azure_key || "");
        setAzureRegion(c.azure_region || "");
        setOutputDir(c.output_dir || "");
        setProjectPackagePath(c.project_package_path || "");
      })
      .catch(() => {});
    refresh();
    const t = setInterval(refresh, 1000);
    return () => clearInterval(t);
  }, [license.usable, refresh]);
  useEffect(() => {
    if (!license.usable) return;
    const es = new EventSource("/api/logs/stream");
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "log") setLogs((p) => [...p.slice(-499), d.message]);
      } catch {}
    };
    return () => es.close();
  }, [license.usable]);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);
  const action = async (path, body) => {
    if (!license.usable) return;
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
  const activate = async () => {
    setActivationError("");
    try {
      const status = await api("/api/license/activate", { method: "POST", body: JSON.stringify({ code: activationCode }) });
      setLicense(status);
      setActivationCode("");
      setShowSupport(false);
    } catch (error) {
      setActivationError(error.message);
    }
  };
  const closeSupport = () => {
    setShowSupport(false);
    if (support.licensing_enabled && !license.usable) pyApi?.close_window?.() || window.close();
  };
  const settings = () => ({
    output_dir: outputDir,
    translation_mode: mode,
    translate_blocks: blocks,
    output_format: format,
    output_version: version,
    provider,
    deepl_key: deeplKey,
    azure_key: azureKey,
    azure_region: azureRegion,
    project_package_path: projectPackagePath,
  });
  const refreshAssets = async () => {
    const result = await api("/api/language-assets");
    setAssets(result);
    setProjectPackagePath(result.project?.path || "");
  };
  const openAssets = async (tab = "terms") => {
    setAssetTab(tab);
    setShowAssets(true);
    try {
      await refreshAssets();
      if (tab === "usage") {
        const usage = await api("/api/language-assets/usage", { method: "POST", body: JSON.stringify({ deepl_key: deeplKey }) });
        setAssets((old) => ({ ...old, usage: usage.local, deepl_remote: usage.deepl_remote }));
      }
    } catch (error) { setLogs((p) => [...p, `ERROR: ${error.message}`]); }
  };
  const saveTerm = async () => {
    await api("/api/language-assets/terms", { method: "POST", body: JSON.stringify({ ...termForm, project_package_path: projectPackagePath }) });
    setTermForm({ scope: termForm.scope, mode: termForm.mode, source: "", target: "", layer_contains: "", id: null });
    await refreshAssets();
  };
  const saveMemory = async () => {
    await api("/api/language-assets/memory", { method: "POST", body: JSON.stringify(memoryForm) });
    setMemoryForm({ mode: memoryForm.mode, source: "", target: "", layer_contains: "", id: null });
    await refreshAssets();
  };
  const chooseProjectPackage = async (create = false) => {
    const result = create ? await pyApi?.save_term_package?.() : await pyApi?.pick_term_package?.();
    const path = result?.path || projectPackagePath;
    if (!path) return;
    const project = await api("/api/language-assets/project", { method: "POST", body: JSON.stringify({ path, create }) });
    setProjectPackagePath(project.path);
    await refreshAssets();
  };
  const chooseFiles = async () => {
    const r = await pyApi?.pick_cad_files?.();
    if (r?.paths?.length)
      action("/api/batch/add", { files: r.paths });
  };
  const dropFiles = async (event) => {
    event.preventDefault();
    setDraggingFiles(false);
    const files = [...event.dataTransfer.files].filter((file) => /\.(dxf|dwg)$/i.test(file.name));
    if (!files.length) {
      setLogs((p) => [...p, "ERROR: 请拖入 DXF 或 DWG 文件"]);
      return;
    }
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    try {
      const response = await fetch("/api/batch/drop", { method: "POST", body });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || response.statusText);
      refresh();
    } catch (error) {
      setLogs((p) => [...p, `ERROR: ${error.message}`]);
    }
  };
  const chooseOutput = async () => {
    const r = await pyApi?.pick_output_dir?.();
    if (r?.path) {
      setOutputDir(r.path);
      api("/api/config", {
        method: "POST",
        body: JSON.stringify({ ...settings(), output_dir: r.path }),
      }).catch(() => {});
    }
  };
  const exportLogs = async () => {
    if (pyApi?.export_logs) {
      const result = await pyApi.export_logs();
      if (result?.path) setLogs((p) => [...p, `日志已导出: ${result.path}`]);
      return;
    }
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([logs.join("\n")], { type: "text/plain;charset=utf-8" }));
    link.download = "Honsen_CAD_Translator_log.txt";
    link.click();
    URL.revokeObjectURL(link.href);
  };
  const clearLogs = () => {
    setLogs([]);
    action("/api/logs/clear");
  };
  const revealOutput = async (path) => {
    const result = await pyApi?.reveal_file?.(path);
    if (result?.error) setLogs((p) => [...p, `ERROR: ${result.error}`]);
    else if (!result) setLogs((p) => [...p, "ERROR: 定位文件仅支持桌面应用"]);
  };
  const toggle = () =>
    batch.started
      ? action(`/api/batch/pause?paused=${!batch.paused}`)
      : action("/api/batch/start", settings());
  const canStart = batch.tasks.some((t) =>
    ["queued", "retrying", "cancelled", "failed"].includes(t.status),
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
  const activeTheme = theme === "system" ? { ...THEMES.system, color: systemAccent } : THEMES[theme];
  const systemRgb = systemAccent.map((channel) => Math.round(Math.max(0, Math.min(1, channel)) * 255));
  const systemThemeStyle = theme === "system" ? {
    "--accent": `rgb(${systemRgb.join(" ")})`,
    "--accent-strong": `color-mix(in srgb, rgb(${systemRgb.join(" ")}) 72%, white)`,
    "--accent-soft": `rgb(${systemRgb.join(" ")} / 0.30)`,
  } : undefined;
  return (
    <div className={`app-shell theme-${theme}`} style={systemThemeStyle}>
      <Iridescence
        color={activeTheme.color}
        speed={0.85}
        amplitude={0.14}
        mouseReact
      />
      <div className="bg-vignette" />
      <div className="bg-noise" />
      {showAssets && (
        <div className="support-overlay" onClick={() => setShowAssets(false)}>
          <div className="asset-card" onClick={(event) => event.stopPropagation()}>
            <button className="support-close" onClick={() => setShowAssets(false)}>×</button>
            <h2>语言资产</h2>
            <div className="asset-tabs">
              <button className={assetTab === "terms" ? "active" : ""} onClick={() => setAssetTab("terms")}>术语表</button>
              <button className={assetTab === "builtins" ? "active" : ""} onClick={() => setAssetTab("builtins")}>内置术语</button>
              <button className={assetTab === "memory" ? "active" : ""} onClick={() => setAssetTab("memory")}>翻译记忆</button>
              <button className={assetTab === "usage" ? "active" : ""} onClick={() => { setAssetTab("usage"); api("/api/language-assets/usage", { method: "POST", body: JSON.stringify({ deepl_key: deeplKey }) }).then((result) => setAssets((old) => ({ ...old, usage: result.local, deepl_remote: result.deepl_remote }))).catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`])); }}>服务用量</button>
            </div>
            {assetTab === "terms" && <>
              <div className="asset-project">
                <input value={projectPackagePath} onChange={(event) => setProjectPackagePath(event.target.value)} placeholder="项目术语包 .hcterms.json" />
                <button className="btn ghost" onClick={() => chooseProjectPackage(false).catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>选择</button>
                <button className="btn ghost" onClick={() => chooseProjectPackage(true).catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>新建</button>
              </div>
              <div className="asset-form">
                <select value={termForm.scope} onChange={(event) => setTermForm((form) => ({ ...form, scope: event.target.value, id: null }))}><option value="global">我的术语</option><option value="project">项目术语</option></select>
                <select value={termForm.mode} onChange={(event) => setTermForm((form) => ({ ...form, mode: event.target.value }))}>{modes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                <input value={termForm.source} onChange={(event) => setTermForm((form) => ({ ...form, source: event.target.value }))} placeholder="原文（完整匹配）" />
                <input value={termForm.target} onChange={(event) => setTermForm((form) => ({ ...form, target: event.target.value }))} placeholder="译文" />
                <input value={termForm.layer_contains} onChange={(event) => setTermForm((form) => ({ ...form, layer_contains: event.target.value }))} placeholder="图层包含（可选）" />
                <button className="btn primary" onClick={() => saveTerm().catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>{termForm.id === null ? "添加术语" : "保存术语"}</button>
              </div>
              <input className="asset-search" value={assetSearch} onChange={(event) => setAssetSearch(event.target.value)} placeholder="搜索术语" />
              <div className="asset-list">
                {assets.terms.filter((term) => `${term.source} ${term.target}`.toLowerCase().includes(assetSearch.toLowerCase())).map((term) => <div className="asset-row" key={`${term.scope}-${term.id}`}><div><b>{term.source}</b> → {term.target}<small>{term.scope === "project" ? "项目术语" : "我的术语"} · {term.mode}{term.layer_contains ? ` · 图层:${term.layer_contains}` : ""}</small></div><button className="btn ghost" onClick={() => setTermForm({ ...term })}>编辑</button><button className="btn ghost" onClick={() => api("/api/language-assets/terms/delete", { method: "POST", body: JSON.stringify({ scope: term.scope, id: term.id, project_package_path: projectPackagePath }) }).then(refreshAssets).catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>删除</button></div>)}
              </div>
            </>}
            {assetTab === "builtins" && <>
              <p className="hint">以下为随软件发布的四个 YAML 术语表，只读且始终参与翻译。复制后可在“术语表”中改为项目或我的覆盖词。</p>
              <input className="asset-search" value={assetSearch} onChange={(event) => setAssetSearch(event.target.value)} placeholder="搜索内置术语" />
              <div className="asset-list">
                {assets.builtin_terms.filter((term) => `${term.source} ${term.target}`.toLowerCase().includes(assetSearch.toLowerCase())).map((term) => <div className="asset-row" key={term.id}><div><b>{term.source}</b> → {term.target}<small>内置术语 · {term.mode}</small></div><button className="btn ghost" onClick={() => { setTermForm({ scope: "global", mode: term.mode, source: term.source, target: term.target, layer_contains: "", id: null }); setAssetTab("terms"); }}>复制到我的术语</button><button className="btn ghost" onClick={() => { setTermForm({ scope: "project", mode: term.mode, source: term.source, target: term.target, layer_contains: "", id: null }); setAssetTab("terms"); }}>复制到项目</button></div>)}
              </div>
            </>}
            {assetTab === "memory" && <>
              <div className="asset-form">
                <select value={memoryForm.mode} onChange={(event) => setMemoryForm((form) => ({ ...form, mode: event.target.value }))}>{modes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                <input value={memoryForm.source} onChange={(event) => setMemoryForm((form) => ({ ...form, source: event.target.value }))} placeholder="原文" />
                <input value={memoryForm.target} onChange={(event) => setMemoryForm((form) => ({ ...form, target: event.target.value }))} placeholder="译文" />
                <input value={memoryForm.layer_contains} onChange={(event) => setMemoryForm((form) => ({ ...form, layer_contains: event.target.value }))} placeholder="精确图层（可选）" />
                <button className="btn primary" onClick={() => saveMemory().catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>{memoryForm.id === null ? "添加记忆" : "保存记忆"}</button>
              </div>
              <div className="asset-list">
                {assets.memory.map((entry) => <div className="asset-row" key={entry.id}><div><b>{entry.source}</b> → {entry.target}<small>{entry.mode} · {entry.origin === "manual" ? "人工" : entry.provider} · 命中 {entry.hit_count} 次</small></div><button className="btn ghost" onClick={() => setMemoryForm({ mode: entry.mode, source: entry.source, target: entry.target, layer_contains: entry.layer_key, id: entry.id })}>编辑</button><button className="btn ghost" onClick={() => { setTermForm({ scope: "global", mode: entry.mode, source: entry.source, target: entry.target, layer_contains: entry.layer_key, id: null }); setAssetTab("terms"); }}>升为术语</button><button className="btn ghost" onClick={() => api("/api/language-assets/memory/delete", { method: "POST", body: JSON.stringify({ id: entry.id }) }).then(refreshAssets).catch((error) => setLogs((p) => [...p, `ERROR: ${error.message}`]))}>删除</button></div>)}
              </div>
            </>}
            {assetTab === "usage" && <div className="usage-grid">
              <section><h3>DeepL</h3>{assets.deepl_remote?.available ? <p>{assets.deepl_remote.characters.toLocaleString()} / {assets.deepl_remote.limit.toLocaleString()} 字符</p> : <p>{assets.deepl_remote?.message || "点击此页自动读取"}</p>}<small>本软件本月：{(assets.usage?.deepl?.characters || 0).toLocaleString()} 字符，{assets.usage?.deepl?.requests || 0} 次请求</small></section>
              <section><h3>Azure Translator F0</h3><p>{(assets.usage?.azure?.characters || 0).toLocaleString()} / {(assets.usage?.azure?.limit || 2000000).toLocaleString()} 字符</p><small>估算剩余 {(assets.usage?.azure?.remaining || 2000000).toLocaleString()}；{assets.usage?.azure?.requests || 0} 次请求{assets.usage?.azure?.quota_exceeded ? "；已收到额度超额信号" : ""}</small></section>
              <p className="hint">Azure 为本软件本机发送字符统计；DeepL 数值来自当前 Key 的官方用量接口。</p>
            </div>}
          </div>
        </div>
      )}
      {showSupport && (
        <div className="support-overlay" onClick={closeSupport}>
          <div className="support-card" onClick={(event) => event.stopPropagation()}>
            <button className="support-close" onClick={closeSupport}>×</button>
            <h2>{support.licensing_enabled ? "购买许可" : "赞助作者"}</h2>
            {support.licensing_enabled ? (
              <>
                <p>{license.message || "正在校验授权…"}</p>
                {license.expires_on && <p>到期日：{license.expires_on}</p>}
                {license.plan && <p>套餐：{license.plan}</p>}
                <input value={activationCode} onChange={(event) => setActivationCode(event.target.value)} placeholder="输入激活码，可用于续期" />
                <button className="btn primary" disabled={license.checking || !activationCode.trim()} onClick={activate}>激活软件</button>
                {activationError && <small>{activationError}</small>}
              </>
            ) : support.wechat_qr_url || support.alipay_qr_url ? (
              <div className="support-qrs">
                {support.wechat_qr_url && <figure><img src="/api/support/qrcode/wechat" alt="微信收款码" /><figcaption>微信收款码</figcaption></figure>}
                {support.alipay_qr_url && <figure><img src="/api/support/qrcode/alipay" alt="支付宝商家收款码" /><figcaption>支付宝商家收款码</figcaption></figure>}
              </div>
            ) : <p>请在 <code>backend/licensing.py</code> 配置两个外部收款码链接。</p>}
          </div>
        </div>
      )}
      {support.licensing_enabled && license.checking && (
        <div className="license-overlay">
          <div className="license-card">
            <h2>正在校验授权</h2>
            <p>正在联网同步时间…</p>
          </div>
        </div>
      )}
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
          <button className="support-button" onClick={() => setShowSupport(true)}>
            {support.licensing_enabled ? "购买许可" : "赞助作者"}
          </button>
          <div className="theme-switcher" aria-label="主题切换">
            {Object.entries(THEMES).map(([name, item]) => (
              <button type="button" className={`theme-swatch theme-swatch-${name} ${theme === name ? "active" : ""}`} aria-label={`${item.label}主题`} title={`${item.label}主题`} key={name} onClick={() => setTheme(name)} />
            ))}
          </div>
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
          <motion.section
            className={`glass queue-panel${draggingFiles ? " drop-active" : ""}`}
            variants={itemVariants}
            onDragEnter={(event) => { event.preventDefault(); setDraggingFiles(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setDraggingFiles(false);
            }}
            onDrop={dropFiles}
          >
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
                      {t.status === "succeeded" && t.output_file && (
                        <button className="btn ghost" onClick={() => revealOutput(t.output_file)}>
                          定位文件
                        </button>
                      )}
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
              <div className="log-actions">
              <button className="btn ghost" onClick={exportLogs}>
                导出日志
              </button>
              <button className="btn ghost" onClick={clearLogs}>
                清除
              </button>
            </div>
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
            <Field label="翻译服务">
              <SelectMenu
                value={provider}
                onChange={setProvider}
                options={[["deepl", "DeepL"], ["azure", "Azure Translator（F0）"]]}
              />
            </Field>
            <div className="asset-actions">
              <button className="btn secondary" onClick={() => openAssets("terms")}>术语与记忆</button>
              <button className="btn secondary" onClick={() => openAssets("usage")}>服务用量</button>
            </div>
            {provider === "azure" ? (
              <>
                <Field label="Azure Translator Key">
                  <input type="password" value={azureKey} onChange={(e) => setAzureKey(e.target.value)} placeholder="输入 Azure Translator Key" />
                </Field>
                <Field label="Azure Region（可选）">
                  <input value={azureRegion} onChange={(e) => setAzureRegion(e.target.value)} placeholder="全局资源留空；区域资源如 eastus" />
                </Field>
                <p className="hint">F0 免费额度用尽后将停止请求，等待下月额度重置。</p>
              </>
            ) : (
              <Field label="DeepL API Key">
                <input type="password" value={deeplKey} onChange={(e) => setDeeplKey(e.target.value)} placeholder="输入 DeepL API Key" />
              </Field>
            )}
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
        <span className="footer-meta">v1.8.8 · <a href="https://github.com/etianwang" target="_blank" rel="noreferrer">Etienne</a></span>
      </motion.footer>
    </div>
  );
}
