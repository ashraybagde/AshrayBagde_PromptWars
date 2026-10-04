"""No-verdict filter: detect and strip directive language."""
import re
from typing import Any

from pydantic import BaseModel

_PATTERNS = [re.compile(p, re.I) for p in (
    r"\byou (should|must|ought to|need to|had better)\b", r"\bi (recommend|suggest|advise)\b",
    r"\b(the )?best (choice|option|decision)\b", r"\bis (clearly )?(better|the winner)\b",
    r"\bmy (advice|verdict|recommendation)\b", r"\bwinner\b",
    r"\bi would (choose|pick|go)\b", r"\bit would be (wise|best) to\b",
)]


def has_verdict(text: str) -> bool:
    """Return True if text contains directive or verdict language."""
    return any(p.search(text) for p in _PATTERNS)


def _clean(node: Any) -> Any:
    if isinstance(node, str):
        return "" if has_verdict(node) else node
    if isinstance(node, list):
        cleaned = [_clean(i) for i in node]
        return [i for i in cleaned if i not in ("", {}, None)]
    if isinstance(node, dict):
        if any(isinstance(v, str) and has_verdict(v) for v in node.values()):
            return {}
        return {k: _clean(v) for k, v in node.items()}
    return node


def find_violations(model: BaseModel) -> bool:
    """Return True if any string in the model is directive."""
    return _clean(model.model_dump()) != model.model_dump()


def sanitize(model: BaseModel) -> BaseModel:
    """Drop offending items, blanking offending scalar strings."""
    return type(model).model_validate(_clean(model.model_dump()))
