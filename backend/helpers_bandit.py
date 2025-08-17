import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple


POLICY_STATS_PATH = Path("backend/policy_stats.json")


DEFAULT_VARIANTS: Dict[str, Dict[str, Dict[str, int]]] = {
    "brainstorm": {
        "format_10_strict": {"alpha": 1, "beta": 1},
        "format_10_2lines": {"alpha": 1, "beta": 1},
        "diversity_high": {"alpha": 1, "beta": 1},
    },
    "coding": {
        "bash_min": {"alpha": 1, "beta": 1},
        "bash_plus_alt": {"alpha": 1, "beta": 1},
        "with_checks": {"alpha": 1, "beta": 1},
    },
}


def ensure_stats_initialized() -> None:
    """Create policy_stats.json if missing and ensure all default variants exist."""
    POLICY_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not POLICY_STATS_PATH.exists():
        with POLICY_STATS_PATH.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_VARIANTS, f, ensure_ascii=False, indent=2)
        return

    # Merge defaults with existing
    data = load_stats()
    changed = False
    for intent, variants in DEFAULT_VARIANTS.items():
        if intent not in data:
            data[intent] = {}
            changed = True
        for vid, ab in variants.items():
            if vid not in data[intent]:
                data[intent][vid] = {"alpha": 1, "beta": 1}
                changed = True
            else:
                # Ensure fields exist
                if "alpha" not in data[intent][vid] or "beta" not in data[intent][vid]:
                    data[intent][vid] = {"alpha": 1, "beta": 1}
                    changed = True
    if changed:
        save_stats(data)


def load_stats() -> Dict[str, Dict[str, Dict[str, int]]]:
    if not POLICY_STATS_PATH.exists():
        return json.loads(json.dumps(DEFAULT_VARIANTS))
    try:
        with POLICY_STATS_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # On parse error, reset to defaults
        return json.loads(json.dumps(DEFAULT_VARIANTS))


def save_stats(data: Dict[str, Dict[str, Dict[str, int]]]) -> None:
    with POLICY_STATS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pick_variant(intent: str, variants: List[str], epsilon: float = 0.12) -> str:
    """
    Thompson Sampling with minimum epsilon-greedy exploration.
    - intent: "brainstorm" | "coding"
    - variants: list of variant_ids available
    Returns chosen variant_id.
    """
    stats = load_stats()
    intent_stats = stats.get(intent, {})
    if not variants:
        return ""

    # Ensure variants exist in stats
    changed = False
    for vid in variants:
        if vid not in intent_stats:
            intent_stats[vid] = {"alpha": 1, "beta": 1}
            changed = True
    if changed:
        stats[intent] = intent_stats
        save_stats(stats)

    # Epsilon exploration
    if random.random() < max(0.10, min(epsilon, 0.15)):
        return random.choice(variants)

    # Thompson sampling: draw from Beta(alpha, beta) and pick argmax
    best_vid = None
    best_draw = -1.0
    for vid in variants:
        ab = intent_stats.get(vid, {"alpha": 1, "beta": 1})
        a = max(1, int(ab.get("alpha", 1)))
        b = max(1, int(ab.get("beta", 1)))
        draw = random.betavariate(a, b)
        if draw > best_draw:
            best_draw = draw
            best_vid = vid
    return best_vid or variants[0]


def update_variant(intent: str, variant_id: str, success: bool) -> None:
    data = load_stats()
    if intent not in data:
        data[intent] = {}
    if variant_id not in data[intent]:
        data[intent][variant_id] = {"alpha": 1, "beta": 1}
    if success:
        data[intent][variant_id]["alpha"] = int(data[intent][variant_id]["alpha"]) + 1
    else:
        data[intent][variant_id]["beta"] = int(data[intent][variant_id]["beta"]) + 1
    save_stats(data)


def get_stats_summary() -> Dict[str, Any]:
    data = load_stats()
    summary: Dict[str, Any] = {}
    for intent, variants in data.items():
        summary[intent] = {}
        for vid, ab in variants.items():
            a = int(ab.get("alpha", 1))
            b = int(ab.get("beta", 1))
            total = a + b - 2  # since both start at 1
            mean = a / (a + b) if (a + b) > 0 else 0.0
            summary[intent][vid] = {
                "alpha": a,
                "beta": b,
                "samples": total,
                "success_rate_mean": round(mean, 4),
            }
    return summary
