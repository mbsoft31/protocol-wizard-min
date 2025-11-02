from __future__ import annotations
import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jsonschema import Draft7Validator


def deep_sort(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: deep_sort(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [deep_sort(x) for x in obj]
    return obj


def canonical_json_string(obj: Any) -> str:
    return json.dumps(deep_sort(obj), ensure_ascii=False, separators=(",", ":"))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def strip_code_fences(text: str) -> str:
    t = text
    t = t.replace("```json", "").replace("```jsonl", "").replace("```", "")
    return t.strip()


def normalize_jsonl(raw: str) -> List[Dict[str, Any]]:
    """
    Accept JSONL text or a single JSON array and return a list of objects.
    Ignore empty lines and code fences.
    """
    cleaned = strip_code_fences(raw)
    try:
        arr = json.loads(cleaned)
        if isinstance(arr, list):
            return [x for x in arr if isinstance(x, dict)]
    except Exception:
        pass
    objs: List[Dict[str, Any]] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                objs.append(obj)
        except Exception:
            continue
    return objs


def utc_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def load_protocol_schema() -> Tuple[Dict[str, Any], Draft7Validator]:
    schema_path = Path("schemas/protocol.schema.json")
    schema = json.loads(load_text(schema_path))
    validator = Draft7Validator(schema)
    return schema, validator


def validate_against_schema(obj: Dict[str, Any]) -> Dict[str, Any]:
    _, validator = load_protocol_schema()
    errors = [
        {"path": "/" + "/".join(map(str, e.path)), "message": e.message}
        for e in validator.iter_errors(obj)
    ]
    return {"valid": len(errors) == 0, "errors": errors}

