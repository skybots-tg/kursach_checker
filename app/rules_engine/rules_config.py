from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SEVERITY = "warning"


@dataclass(slots=True)
class BlockConfig:
    key: str
    title: str
    enabled: bool
    severity: str
    params: dict


class RulesConfig:
    def __init__(self, raw_rules: dict | None):
        self.raw_rules = raw_rules or {}
        self._blocks = self._parse_blocks(self.raw_rules)

    @staticmethod
    def _parse_blocks(raw_rules: dict) -> dict[str, BlockConfig]:
        blocks: dict[str, BlockConfig] = {}
        for item in raw_rules.get("blocks", []):
            key = str(item.get("key", "")).strip()
            if not key:
                continue
            blocks[key] = BlockConfig(
                key=key,
                title=str(item.get("title") or key),
                enabled=bool(item.get("enabled", True)),
                severity=str(item.get("severity", DEFAULT_SEVERITY)),
                params=item.get("params") or {},
            )
        return blocks

    def has(self, key: str) -> bool:
        block = self._blocks.get(key)
        return bool(block and block.enabled)

    def severity(self, key: str, default: str = DEFAULT_SEVERITY) -> str:
        block = self._blocks.get(key)
        if not block:
            return default
        return block.severity or default

    def params(self, key: str) -> dict:
        block = self._blocks.get(key)
        if not block:
            return {}
        return block.params

    def blocks_count(self) -> int:
        return len(self._blocks)

