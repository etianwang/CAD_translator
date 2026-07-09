"""DWG/DXF conversion via ezdxf odafc addon (ODA File Converter)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

WORK_DXF_VERSION = "R2010"

# 安装包推荐目录结构（与主程序 exe 同级）：
#   Honsen_CAD_Translator_v2.2.exe
#   ODAFileConverter/
#     ODAFileConverter.exe
#     *.dll ...
ODA_BUNDLE_DIR = "ODAFileConverter"
ODA_BUNDLE_EXE = "ODAFileConverter.exe"
ODA_SYSTEM_EXE = r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"

# DWG 文件头 6 字节版本签名 → ODA File Converter 版本参数
ACAD_SIG_TO_ODA: dict[str, str] = {
    "AC1012": "ACAD13",
    "AC1014": "ACAD14",
    "AC1015": "ACAD2000",
    "AC1018": "ACAD2004",
    "AC1021": "ACAD2007",
    "AC1024": "ACAD2010",
    "AC1027": "ACAD2013",
    "AC1032": "ACAD2018",
}

LogFn = Optional[Callable[[str], None]]
_odafc_configured = False


@dataclass
class SourceCadMeta:
    original_path: str
    source_ext: str
    acad_sig: str = ""
    oda_version: str = "ACAD2010"

    @property
    def is_dwg(self) -> bool:
        return self.source_ext.lower() == ".dwg"

    @property
    def output_ext(self) -> str:
        return self.source_ext.lower()


def get_app_dir() -> Path:
    """打包后为主 exe 所在目录；开发环境为项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _log(fn: LogFn, message: str) -> None:
    if fn:
        fn(message)


def odafc_candidate_paths() -> list[Path]:
    app_dir = get_app_dir()
    custom = os.environ.get("CAD_ODA_EXEC", "").strip()
    paths: list[Path] = []
    if custom:
        paths.append(Path(custom))
    paths.extend(
        [
            app_dir / ODA_BUNDLE_DIR / ODA_BUNDLE_EXE,
            app_dir / ODA_BUNDLE_EXE,
            Path(ODA_SYSTEM_EXE),
        ]
    )
    return paths


def resolve_odafc_path() -> Optional[str]:
    for path in odafc_candidate_paths():
        if path.is_file():
            return str(path.resolve())
    return None


def configure_odafc() -> Optional[str]:
    """优先使用与主程序同目录的 ODA File Converter。"""
    global _odafc_configured
    path = resolve_odafc_path()
    if path:
        import ezdxf

        ezdxf.options.set("odafc-addon", "win_exec_path", path)
        _odafc_configured = True
    return path


def dwg_unavailable_message() -> str:
    app_dir = get_app_dir()
    bundled = app_dir / ODA_BUNDLE_DIR / ODA_BUNDLE_EXE
    return (
        "未检测到 ODA File Converter，无法自动处理 DWG。\n"
        f"- 请确认已安装 ODA（推荐路径：{bundled}）\n"
        "- 或在 AutoCAD 中将图纸「另存为 DXF」后，直接选择 .dxf 文件翻译"
    )


def dwg_unavailable_short() -> str:
    return "未检测到 ODA，无法处理 DWG；请安装 ODA 或将 DWG 另存为 DXF"


def odafc_status() -> dict:
    path = configure_odafc() or resolve_odafc_path()
    if not path:
        return {
            "installed": False,
            "path": "",
            "source": "",
            "message": dwg_unavailable_message(),
        }

    app_dir = get_app_dir()
    p = Path(path)
    if p.parent == app_dir or p.parent == app_dir / ODA_BUNDLE_DIR:
        source = "bundled"
    elif os.environ.get("CAD_ODA_EXEC"):
        source = "env"
    else:
        source = "system"
    return {"installed": True, "path": path, "source": source}


def odafc_available() -> bool:
    try:
        configure_odafc()
        from ezdxf.addons import odafc

        return odafc.is_installed()
    except Exception:
        return bool(resolve_odafc_path())


def require_odafc(log: LogFn = None) -> None:
    path = configure_odafc()
    if not path or not odafc_available():
        raise RuntimeError(dwg_unavailable_message())
    _log(log, f"ODA File Converter 已就绪 ({path})")


def read_dwg_acad_signature(path: str) -> str:
    with open(path, "rb") as f:
        return f.read(6).decode("ascii", errors="ignore").strip("\x00")


def analyze_source(path: str) -> SourceCadMeta:
    ext = Path(path).suffix.lower()
    if ext not in (".dxf", ".dwg"):
        raise ValueError(f"不支持的文件格式: {ext}")

    meta = SourceCadMeta(original_path=path, source_ext=ext)
    if meta.is_dwg:
        sig = read_dwg_acad_signature(path)
        meta.acad_sig = sig
        meta.oda_version = ACAD_SIG_TO_ODA.get(sig, "ACAD2010")
    return meta


def output_path_for(meta: SourceCadMeta, output_dir: str, output_name: str) -> str:
    name = output_name.strip()
    return os.path.join(output_dir, name + meta.output_ext)


def dwg_to_work_dxf(dwg_path: str, work_dxf_path: str, log: LogFn = None) -> None:
    from ezdxf.addons import odafc

    require_odafc(log)
    _log(log, f"DWG → DXF {WORK_DXF_VERSION}（工作副本）...")
    odafc.convert(dwg_path, work_dxf_path, version=WORK_DXF_VERSION, audit=True, replace=True)
    _log(log, "DWG 已转换为 DXF 中间文件")


def work_dxf_to_dwg(
    work_dxf_path: str,
    dwg_path: str,
    meta: SourceCadMeta,
    log: LogFn = None,
) -> None:
    from ezdxf.addons import odafc

    require_odafc(log)
    _log(log, f"DXF → DWG {meta.oda_version}（还原原版本 {meta.acad_sig or '未知'}）...")
    odafc.convert(work_dxf_path, dwg_path, version=meta.oda_version, audit=True, replace=True)
    _log(log, f"已输出 DWG: {dwg_path}")


class CadConversionSession:
    """管理 DWG 往返转换的临时目录。"""

    def __init__(self, input_file: str, log: LogFn = None):
        self.meta = analyze_source(input_file)
        self.log = log
        self._tmp: Optional[str] = None
        self.work_input: str = input_file

    def __enter__(self) -> CadConversionSession:
        if self.meta.is_dwg:
            require_odafc(self.log)
            self._tmp = tempfile.mkdtemp(prefix="cad_tr_")
            self.work_input = os.path.join(self._tmp, "work_input.dxf")
            _log(
                self.log,
                f"检测到 DWG：{self.meta.acad_sig} → 将按 {self.meta.oda_version} 还原",
            )
            dwg_to_work_dxf(self.meta.original_path, self.work_input, self.log)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._tmp and os.path.isdir(self._tmp):
            shutil.rmtree(self._tmp, ignore_errors=True)

    def work_output_path(self) -> str:
        if self._tmp:
            return os.path.join(self._tmp, "work_output.dxf")
        return ""

    def finalize(self, translated_dxf: str, final_output: str) -> None:
        if self.meta.is_dwg:
            work_dxf_to_dwg(translated_dxf, final_output, self.meta, self.log)
        elif os.path.abspath(translated_dxf) != os.path.abspath(final_output):
            shutil.copy2(translated_dxf, final_output)
