"""No-network v1.9.0 language-asset checks."""

import tempfile
from pathlib import Path

from backend.language_assets import LanguageAssets
from backend.translator import CADChineseTranslator


with tempfile.TemporaryDirectory() as tmp:
    assets = LanguageAssets(Path(tmp) / "assets.sqlite3")

    assets.upsert_term("fr_to_zh", "S.A.S", "前室")
    assert assets.lookup_term("s-a-s", "fr_to_zh") == "前室"
    assert assets.lookup_term("S_A_S", "fr_to_zh") == "前室"
    assert assets.lookup_term("SAS", "fr_to_zh") == "前室"
    assets.upsert_term("fr_to_zh", "A-01", "编号")
    assert assets.lookup_term("A01", "fr_to_zh") is None

    assets.upsert_term("zh_to_fr", "控制", "CMD")
    assets.upsert_term("zh_to_fr", "控制", "régulation", profession="hvac")
    assert assets.lookup_term("控制", "zh_to_fr", "hvac") == "régulation"
    assert assets.lookup_term("控制", "zh_to_fr", "electrical") == "CMD"

    assets.record_provider_result("service label", "接口译文", "fr_to_zh", "deepl", "first.dxf")
    assert assets.lookup_record("SERVICE LABEL", "fr_to_zh", "second.dwg") == "接口译文"
    record = assets.list_records("fr_to_zh", search="service")
    assert record["total"] == 1 and set(record["items"][0]["drawings"].split("、")) == {"first.dxf", "second.dwg"}
    record_id = record["items"][0]["id"]
    assets.update_record(record_id, "service label", "人工译文")
    assets.record_provider_result("service label", "接口新译文", "fr_to_zh", "azure", "third.dxf")
    assert assets.lookup_record("service label", "fr_to_zh") == "人工译文"
    assets.promote_record(record_id)
    assert assets.lookup_term("service label", "fr_to_zh") == "人工译文"

    translator = CADChineseTranslator(log_callback=lambda *_args, **_kwargs: None)
    translator.language_assets = assets
    translator.deepl_translator = None
    assert translator.translate_text("service label", "fr_to_zh") == "人工译文"
    assets.upsert_term("fr_to_zh", "service label", "术语覆盖")
    assert translator.translate_text("service label", "fr_to_zh") == "术语覆盖"

    assets.record_provider_result("风机", "ventilateur", "zh_to_fr", "deepl", profession="hvac")
    assets.record_provider_result("风机", "fan", "zh_to_fr", "deepl", profession="electrical")
    assert assets.lookup_record("风机", "zh_to_fr", profession="hvac") == "ventilateur"
    assert assets.lookup_record("风机", "zh_to_fr", profession="plumbing") is None
