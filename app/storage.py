"""Local filesystem asset storage."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StoredAsset:
    """Metadata about a stored file."""

    relative_path: str
    sha256: str
    size_bytes: int


class LocalAssetStore:
    """Persist assets under a configurable data directory."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def ensure_directories(self) -> None:
        """Create required storage directories."""
        for relative_dir in ("blobs", "captures", "imports", "derived"):
            (self.root_dir / relative_dir).mkdir(parents=True, exist_ok=True)

    def store_bytes(
        self,
        *,
        category: str,
        suggested_name: str,
        content: bytes,
    ) -> StoredAsset:
        """Write bytes to disk and return storage metadata."""
        sha256 = hashlib.sha256(content).hexdigest()
        target_dir = self.root_dir / category / sha256[:2] / sha256[2:4]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{sha256}-{suggested_name}"
        target_path.write_bytes(content)
        return StoredAsset(
            relative_path=str(target_path.relative_to(self.root_dir)),
            sha256=sha256,
            size_bytes=len(content),
        )

    def store_json(
        self,
        *,
        category: str,
        suggested_name: str,
        payload: dict[str, Any],
    ) -> StoredAsset:
        """Serialize and store JSON."""
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        return self.store_bytes(category=category, suggested_name=suggested_name, content=content)

    def decode_asset_content(self, *, content_base64: str | None, text_content: str | None) -> bytes:
        """Convert inline request content into bytes."""
        if content_base64 is not None:
            return base64.b64decode(content_base64)
        if text_content is not None:
            return text_content.encode("utf-8")
        raise ValueError("asset payload requires either content_base64 or text_content")

