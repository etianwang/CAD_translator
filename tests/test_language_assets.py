"""No-network checks for the local language asset precedence and storage."""

import tempfile
from pathlib import Path

from backend.language_assets import LanguageAssets
from backend.translator import CADChineseTranslator


with tempfile.TemporaryDirectory() as tmp:
    assets = LanguageAssets(Path(tmp) / "assets.sqlite3")
    project_path = Path(tmp) / "project.hcterms.json"
    assets.create_project(project_path, "Test project")

    assets.upsert_term("global", "fr_to_zh", "service label", "全局译文")
    assets.upsert_term("project", "fr_to_zh", "service label", "项目译文", project_path=str(project_path))
    assert assets.lookup_term("SERVICE LABEL", "fr_to_zh", project_path=str(project_path)) == "项目译文"
    assert assets.lookup_term("SERVICE LABEL", "fr_to_zh") == "全局译文"

    assets.record_memory("memory label", "接口译文", "fr_to_zh", "ELEC", "deepl")
    assert assets.lookup_memory("MEMORY LABEL", "fr_to_zh", "ELEC") == "接口译文"
    assets.upsert_memory("fr_to_zh", "memory label", "人工译文", "ELEC")
    assets.record_memory("memory label", "接口新译文", "fr_to_zh", "ELEC", "azure")
    assert assets.lookup_memory("memory label", "fr_to_zh", "ELEC") == "人工译文"

    translator = CADChineseTranslator(log_callback=lambda *_args, **_kwargs: None)
    translator.language_assets = assets
    translator.configure_language_assets(str(project_path))
    assert translator.translate_text("service label", "fr_to_zh") == "项目译文"
    assert translator.translate_text("memory label", "fr_to_zh", "ELEC") == "人工译文"

    assets.record_usage("azure", 123)
    usage = assets.usage()
    assert usage["azure"]["characters"] == 123 and usage["azure"]["remaining"] == 2_000_000 - 123
    assert len(assets.list_terms(str(project_path))) == 2
    assert project_path.is_file()
