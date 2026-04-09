from __future__ import annotations

from dataclasses import dataclass

from app.rules_engine.template_schema import DEFAULT_TEMPLATE_BLOCKS

DEFAULT_SEVERITY = "warning"


def deep_merge_defaults(stored: dict, defaults: dict) -> dict:
    result = dict(stored)
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
        elif isinstance(default_val, dict) and isinstance(result[key], dict):
            result[key] = deep_merge_defaults(result[key], default_val)
    return result


def merge_blocks_with_defaults(blocks: list[dict]) -> list[dict]:
    defaults_map = {b.key: b.model_dump() for b in DEFAULT_TEMPLATE_BLOCKS}
    stored_keys: set[str] = set()
    merged = []
    for block in blocks:
        if not isinstance(block, dict):
            merged.append(block)
            continue
        key = block.get("key")
        stored_keys.add(key)
        if key in defaults_map:
            default_params = defaults_map[key].get("params", {})
            stored_params = block.get("params") or {}
            block["params"] = deep_merge_defaults(stored_params, default_params)
        merged.append(block)
    for default_block in DEFAULT_TEMPLATE_BLOCKS:
        if default_block.key not in stored_keys:
            merged.append(default_block.model_dump())
    return merged


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
        blocks = self.raw_rules.get("blocks", [])
        self.raw_rules["blocks"] = merge_blocks_with_defaults(blocks)
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


