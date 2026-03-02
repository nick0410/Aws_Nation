"""
AWS S3 Cost Estimator
Real pricing data for ap-south-1 (Mumbai) — updated 2026
"""

# ─────────────────────────────────────────────────────────────
# S3 Pricing — ap-south-1 (Mumbai)
# ─────────────────────────────────────────────────────────────

PRICING = {
    "Standard": {
        "label":        "S3 Standard",
        "storage":      0.025,       # $/GB/month (first 50TB)
        "put_per_1k":   0.0054,      # $/1000 PUT/COPY/POST
        "get_per_1k":   0.00043,     # $/1000 GET/SELECT
        "transfer_out": 0.109,       # $/GB transferred out
        "color":        "#FF9900",
        "description":  "General-purpose. Frequent access.",
        "min_storage":  0,
        "retrieval":    0,
    },
    "Intelligent-Tiering": {
        "label":        "S3 Intelligent-Tiering",
        "storage":      0.025,       # frequent tier
        "storage_ia":   0.01375,     # infrequent tier (after 30 days)
        "monitoring":   0.0025,      # $/1000 objects/month
        "put_per_1k":   0.0054,
        "get_per_1k":   0.00043,
        "transfer_out": 0.109,
        "color":        "#38bdf8",
        "description":  "Auto-moves between tiers. Best for unpredictable access.",
        "min_storage":  0,
        "retrieval":    0,
    },
    "Standard-IA": {
        "label":        "S3 Standard-IA",
        "storage":      0.0138,      # $/GB/month
        "put_per_1k":   0.01,
        "get_per_1k":   0.001,
        "transfer_out": 0.109,
        "retrieval":    0.01,        # $/GB retrieved
        "color":        "#4caf82",
        "description":  "Infrequent access. 30-day min storage duration.",
        "min_storage":  128,         # KB min object size
    },
    "One Zone-IA": {
        "label":        "S3 One Zone-IA",
        "storage":      0.011,
        "put_per_1k":   0.01,
        "get_per_1k":   0.001,
        "transfer_out": 0.109,
        "retrieval":    0.01,
        "color":        "#a78bfa",
        "description":  "Single AZ. 20% cheaper than IA. Not resilient to AZ failure.",
        "min_storage":  128,
    },
    "Glacier Instant": {
        "label":        "S3 Glacier Instant",
        "storage":      0.005,
        "put_per_1k":   0.02,
        "get_per_1k":   0.01,
        "transfer_out": 0.109,
        "retrieval":    0.03,        # $/GB
        "color":        "#f97316",
        "description":  "Archive. Millisecond retrieval. 90-day min duration.",
        "min_storage":  128,
    },
}


def estimate_cost(
    storage_gb: float,
    put_requests_per_day: int,
    get_requests_per_day: int,
    transfer_out_gb_month: float,
    versioning_enabled: bool = False,
    object_count: int = 0,
) -> dict:
    """
    Estimate monthly S3 cost across storage classes.
    Returns per-class breakdown + recommendation.
    """
    put_per_month = put_requests_per_day * 30
    get_per_month = get_requests_per_day * 30

    # If versioning is on, effective storage doubles on average (rough estimate)
    effective_storage = storage_gb * (1.5 if versioning_enabled else 1.0)

    results = {}

    for key, p in PRICING.items():
        storage_cost = effective_storage * p["storage"]
        put_cost     = (put_per_month / 1000) * p["put_per_1k"]
        get_cost     = (get_per_month / 1000) * p["get_per_1k"]
        transfer_cost = transfer_out_gb_month * p["transfer_out"]
        retrieval_cost = 0.0
        monitoring_cost = 0.0

        if key == "Intelligent-Tiering":
            # Assume 60% stays in frequent, 40% moves to IA after 30 days
            storage_cost = (effective_storage * 0.6 * p["storage"]) + \
                           (effective_storage * 0.4 * p["storage_ia"])
            if object_count > 0:
                monitoring_cost = (object_count / 1000) * p["monitoring"]

        if key in ("Standard-IA", "One Zone-IA", "Glacier Instant"):
            # Retrieval cost on GET requests
            # Assume avg object size = storage_gb / max(object_count, 1) in GB
            avg_obj_gb = (storage_gb / max(object_count, 1)) if object_count > 0 else 0.001
            retrieval_cost = get_per_month * avg_obj_gb * p["retrieval"]

        total = storage_cost + put_cost + get_cost + transfer_cost + retrieval_cost + monitoring_cost

        results[key] = {
            "class":           p["label"],
            "color":           p["color"],
            "description":     p["description"],
            "storage_cost":    round(storage_cost, 4),
            "put_cost":        round(put_cost, 4),
            "get_cost":        round(get_cost, 4),
            "transfer_cost":   round(transfer_cost, 4),
            "retrieval_cost":  round(retrieval_cost, 4),
            "monitoring_cost": round(monitoring_cost, 4),
            "total":           round(total, 4),
            "annual":          round(total * 12, 2),
        }

    # Sort by total cost
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["total"]))

    # Build recommendation
    cheapest_key = min(results, key=lambda k: results[k]["total"])
    standard_total = results["Standard"]["total"]
    cheapest_total  = results[cheapest_key]["total"]
    savings_pct     = round((1 - cheapest_total / max(standard_total, 0.0001)) * 100, 1)

    access_pattern = "frequent"
    if get_requests_per_day < 100:
        access_pattern = "infrequent"
    if get_requests_per_day < 10:
        access_pattern = "archive"

    rec_key = "Standard"
    if access_pattern == "infrequent":
        rec_key = "Standard-IA"
    if access_pattern == "archive":
        rec_key = "Glacier Instant"
    if versioning_enabled and access_pattern == "frequent":
        rec_key = "Intelligent-Tiering"

    tip = _get_tip(access_pattern, versioning_enabled, storage_gb, savings_pct, rec_key)

    return {
        "breakdown":          sorted_results,
        "recommended_class":  rec_key,
        "recommended_label":  PRICING[rec_key]["label"],
        "standard_monthly":   round(standard_total, 4),
        "recommended_monthly": round(results[rec_key]["total"], 4),
        "savings_vs_standard": savings_pct,
        "access_pattern":     access_pattern,
        "inputs": {
            "storage_gb":              storage_gb,
            "effective_storage_gb":    round(effective_storage, 2),
            "put_requests_per_day":    put_requests_per_day,
            "get_requests_per_day":    get_requests_per_day,
            "transfer_out_gb_month":   transfer_out_gb_month,
            "versioning_enabled":      versioning_enabled,
            "object_count":            object_count,
        },
        "tip": tip,
    }


def _get_tip(access_pattern, versioning, storage_gb, savings_pct, rec_key):
    tips = []
    if access_pattern == "infrequent":
        tips.append(f"Your GET rate is low — {PRICING[rec_key]['label']} saves up to {savings_pct}% vs Standard.")
    elif access_pattern == "archive":
        tips.append(f"Very few reads detected — Glacier Instant can save ~80% on storage costs.")
    else:
        tips.append("High request rate detected — S3 Standard is optimal for your workload.")

    if versioning:
        tips.append("Versioning is ON — effective storage ~1.5x. Set a lifecycle policy to expire old versions.")
    if storage_gb > 100:
        tips.append("For large datasets, consider S3 Intelligent-Tiering to auto-optimize access tiers.")
    if storage_gb < 1:
        tips.append("Small dataset — S3 Standard is fine. Cost differences are negligible at this scale.")

    return " | ".join(tips)
