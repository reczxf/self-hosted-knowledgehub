from __future__ import annotations

import base64
import json
from pathlib import Path

from app.storage import LocalAssetStore


def test_store_json_creates_expected_file(tmp_path: Path) -> None:
    store = LocalAssetStore(tmp_path)
    store.ensure_directories()

    stored = store.store_json(
        category="captures",
        suggested_name="envelope.json",
        payload={"hello": "world"},
    )

    target = tmp_path / stored.relative_path
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"hello": "world"}
    assert stored.size_bytes > 0


def test_decode_asset_content_supports_base64() -> None:
    store = LocalAssetStore(Path("/tmp/unused"))
    raw = b"pkos"
    encoded = base64.b64encode(raw).decode("ascii")

    assert store.decode_asset_content(content_base64=encoded, text_content=None) == raw
