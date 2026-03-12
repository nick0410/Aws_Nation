"""
AWS S3 Cost Estimator — Random Forest ML Model
Trains a RandomForestRegressor on synthetic pricing data at startup,
then predicts per-class monthly costs from user inputs.
Pricing reference: ap-south-1 (Mumbai) — 2026
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor

# ─────────────────────────────────────────────────────────────
# S3 Pricing metadata (used for training data generation + display)
# ─────────────────────────────────────────────────────────────

STORAGE_CLASSES = [
    "Standard", "Intelligent-Tiering", "Standard-IA", "One Zone-IA", "Glacier Instant"
]

CLASS_META = {
    "Standard": {
        "label": "S3 Standard", "color": "#FF9900",
        "description": "General-purpose. Frequent access.",
    },
    "Intelligent-Tiering": {
        "label": "S3 Intelligent-Tiering", "color": "#38bdf8",
        "description": "Auto-moves between tiers. Best for unpredictable access.",
    },
    "Standard-IA": {
        "label": "S3 Standard-IA", "color": "#4caf82",
        "description": "Infrequent access. 30-day min storage duration.",
    },
    "One Zone-IA": {
        "label": "S3 One Zone-IA", "color": "#a78bfa",
        "description": "Single AZ. 20% cheaper than IA. Not resilient to AZ failure.",
    },
    "Glacier Instant": {
        "label": "S3 Glacier Instant", "color": "#f97316",
        "description": "Archive. Millisecond retrieval. 90-day min duration.",
    },
}

# Real AWS pricing rates used to generate training samples
_RATES = {
    "Standard":             {"stor": 0.025,  "put1k": 0.0054, "get1k": 0.00043, "xfer": 0.109, "retr": 0.0,  "mon": 0.0},
    "Intelligent-Tiering":  {"stor": 0.025,  "stor_ia": 0.01375, "put1k": 0.0054, "get1k": 0.00043, "xfer": 0.109, "retr": 0.0, "mon": 0.0025},
    "Standard-IA":          {"stor": 0.0138, "put1k": 0.01,   "get1k": 0.001,   "xfer": 0.109, "retr": 0.01, "mon": 0.0},
    "One Zone-IA":          {"stor": 0.011,  "put1k": 0.01,   "get1k": 0.001,   "xfer": 0.109, "retr": 0.01, "mon": 0.0},
    "Glacier Instant":      {"stor": 0.005,  "put1k": 0.02,   "get1k": 0.01,    "xfer": 0.109, "retr": 0.03, "mon": 0.0},
}


# ─────────────────────────────────────────────────────────────
# Synthetic data generation (mirrors the old formula-based logic)
# ─────────────────────────────────────────────────────────────

def _generate_training_data(n_samples: int = 5000):
    """
    Generate synthetic training data.
    Features: [storage_gb, put_per_day, get_per_day, transfer_out, versioning, object_count, class_index]
    Target:   [storage_cost, put_cost, get_cost, transfer_cost, retrieval_cost, monitoring_cost]
    """
    rng = np.random.RandomState(42)

    storage_vals   = rng.uniform(0.1, 5000, n_samples)
    put_vals       = rng.randint(0, 50000, n_samples).astype(float)
    get_vals       = rng.randint(0, 50000, n_samples).astype(float)
    xfer_vals      = rng.uniform(0, 500, n_samples)
    ver_vals       = rng.choice([0.0, 1.0], n_samples)
    obj_vals       = rng.randint(0, 100000, n_samples).astype(float)

    X_all, Y_all = [], []

    for cls_idx, cls_name in enumerate(STORAGE_CLASSES):
        r = _RATES[cls_name]
        for i in range(n_samples):
            stor_gb  = storage_vals[i]
            put_day  = put_vals[i]
            get_day  = get_vals[i]
            xfer     = xfer_vals[i]
            ver      = ver_vals[i]
            obj_cnt  = obj_vals[i]

            eff_stor = stor_gb * (1.5 if ver else 1.0)
            put_mo   = put_day * 30
            get_mo   = get_day * 30

            # storage cost
            if cls_name == "Intelligent-Tiering":
                s_cost = eff_stor * 0.6 * r["stor"] + eff_stor * 0.4 * r["stor_ia"]
            else:
                s_cost = eff_stor * r["stor"]

            p_cost = (put_mo / 1000) * r["put1k"]
            g_cost = (get_mo / 1000) * r["get1k"]
            t_cost = xfer * r["xfer"]

            # retrieval
            retr_cost = 0.0
            if cls_name in ("Standard-IA", "One Zone-IA", "Glacier Instant"):
                avg_obj = (stor_gb / max(obj_cnt, 1)) if obj_cnt > 0 else 0.001
                retr_cost = get_mo * avg_obj * r["retr"]

            # monitoring (Intelligent-Tiering)
            mon_cost = 0.0
            if cls_name == "Intelligent-Tiering" and obj_cnt > 0:
                mon_cost = (obj_cnt / 1000) * r["mon"]

            X_all.append([stor_gb, put_day, get_day, xfer, ver, obj_cnt, float(cls_idx)])
            Y_all.append([s_cost, p_cost, g_cost, t_cost, retr_cost, mon_cost])

    return np.array(X_all), np.array(Y_all)


# ─────────────────────────────────────────────────────────────
# Train Random Forest model at module load
# ─────────────────────────────────────────────────────────────

print("[Cost Service] Training Random Forest model on synthetic S3 pricing data...")
_X_train, _Y_train = _generate_training_data(5000)

_rf_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=20,
    random_state=42,
    n_jobs=-1,
)
_rf_model.fit(_X_train, _Y_train)
print("[Cost Service] Random Forest model ready ✓")


# ─────────────────────────────────────────────────────────────
# Public API — same signature & return shape as before
# ─────────────────────────────────────────────────────────────

def estimate_cost(
    storage_gb: float,
    put_requests_per_day: int,
    get_requests_per_day: int,
    transfer_out_gb_month: float,
    versioning_enabled: bool = False,
    object_count: int = 0,
) -> dict:
    """
    Predict monthly S3 cost across storage classes using a Random Forest model.
    Returns per-class breakdown + recommendation.
    """
    effective_storage = storage_gb * (1.5 if versioning_enabled else 1.0)
    ver_flag = 1.0 if versioning_enabled else 0.0

    results = {}

    for cls_idx, cls_name in enumerate(STORAGE_CLASSES):
        features = np.array([[
            storage_gb,
            float(put_requests_per_day),
            float(get_requests_per_day),
            transfer_out_gb_month,
            ver_flag,
            float(object_count),
            float(cls_idx),
        ]])

        pred = _rf_model.predict(features)[0]
        # pred = [storage_cost, put_cost, get_cost, transfer_cost, retrieval_cost, monitoring_cost]
        pred = np.maximum(pred, 0.0)  # clamp negatives

        s_cost, p_cost, g_cost, t_cost, r_cost, m_cost = pred
        total = s_cost + p_cost + g_cost + t_cost + r_cost + m_cost

        meta = CLASS_META[cls_name]
        results[cls_name] = {
            "class":           meta["label"],
            "color":           meta["color"],
            "description":     meta["description"],
            "storage_cost":    round(float(s_cost), 4),
            "put_cost":        round(float(p_cost), 4),
            "get_cost":        round(float(g_cost), 4),
            "transfer_cost":   round(float(t_cost), 4),
            "retrieval_cost":  round(float(r_cost), 4),
            "monitoring_cost": round(float(m_cost), 4),
            "total":           round(float(total), 4),
            "annual":          round(float(total) * 12, 2),
        }

    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["total"]))

    cheapest_key   = min(results, key=lambda k: results[k]["total"])
    standard_total = results["Standard"]["total"]
    cheapest_total = results[cheapest_key]["total"]
    savings_pct    = round((1 - cheapest_total / max(standard_total, 0.0001)) * 100, 1)

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
        "breakdown":           sorted_results,
        "recommended_class":   rec_key,
        "recommended_label":   CLASS_META[rec_key]["label"],
        "standard_monthly":    round(standard_total, 4),
        "recommended_monthly": round(results[rec_key]["total"], 4),
        "savings_vs_standard": savings_pct,
        "access_pattern":      access_pattern,
        "inputs": {
            "storage_gb":            storage_gb,
            "effective_storage_gb":  round(effective_storage, 2),
            "put_requests_per_day":  put_requests_per_day,
            "get_requests_per_day":  get_requests_per_day,
            "transfer_out_gb_month": transfer_out_gb_month,
            "versioning_enabled":    versioning_enabled,
            "object_count":          object_count,
        },
        "tip": tip,
    }


def _get_tip(access_pattern, versioning, storage_gb, savings_pct, rec_key):
    tips = []
    if access_pattern == "infrequent":
        tips.append(f"Your GET rate is low — {CLASS_META[rec_key]['label']} saves up to {savings_pct}% vs Standard.")
    elif access_pattern == "archive":
        tips.append("Very few reads detected — Glacier Instant can save ~80% on storage costs.")
    else:
        tips.append("High request rate detected — S3 Standard is optimal for your workload.")

    if versioning:
        tips.append("Versioning is ON — effective storage ~1.5x. Set a lifecycle policy to expire old versions.")
    if storage_gb > 100:
        tips.append("For large datasets, consider S3 Intelligent-Tiering to auto-optimize access tiers.")
    if storage_gb < 1:
        tips.append("Small dataset — S3 Standard is fine. Cost differences are negligible at this scale.")

    return " | ".join(tips)
