from __future__ import annotations
import json
from server.utils import normalize_jsonl, canonical_json_string


def test_normalize_jsonl_handles_array_and_lines():
    arr_text = json.dumps([
        {"a": 1},
        {"b": 2},
    ])
    objs = normalize_jsonl(arr_text)
    assert objs == [{"a": 1}, {"b": 2}]

    jsonl_text = "\n".join(["{}", "{\"c\":3}"])
    objs2 = normalize_jsonl(jsonl_text)
    assert objs2 == [{}, {"c": 3}]

    fenced = "```jsonl\n{\"x\":1}\n```"
    objs3 = normalize_jsonl(fenced)
    assert objs3 == [{"x": 1}]


def test_canonical_json_string_stable_ordering():
    a = {"b": 2, "a": 1, "c": {"y": 1, "x": 2}}
    b = {"c": {"x": 2, "y": 1}, "b": 2, "a": 1}
    sa = canonical_json_string(a)
    sb = canonical_json_string(b)
    assert sa == sb

