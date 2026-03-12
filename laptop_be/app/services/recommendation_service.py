import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from app.utils.ahp import build_ahp

CRITERION_TO_FEATURE = {
    "cpu": "norm_cpu",
    "ram": "norm_ram",
    "gpu": "norm_gpu",
    "screen": "norm_screen",
    "weight": "norm_weight",
    "battery": "norm_battery",
    "durability": "norm_durability",
    "upgradeability": "norm_upgradeability",
}

BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PATHS = {
    "performance": "Train AI/models/Performance_model.pkl",
    "portability": "Train AI/models/Portability_model.pkl",
}

CRITERION_TO_MODEL_GROUP = {
    "cpu": "performance",
    "ram": "performance",
    "gpu": "performance",
    "screen": "portability",
    "weight": "portability",
    "battery": None,
    "durability": None,
    "upgradeability": None,
}

MODEL_INPUT_COLUMNS_7 = [
    "Norm_CPU",
    "Norm_RAM",
    "Norm_GPU",
    "Norm_Screen",
    "Norm_Weight",
    "Norm_Battery",
    "Norm_Durability",
]

_MODEL_CACHE = {}


def _float_or_none(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _fetch_one(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).mappings().first()


def _fetch_all(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).mappings().all()


def _clamp_score_100(value):
    value = float(value or 0)
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return value


def _normalize_prediction_to_score_100(raw_value):
    raw_value = float(raw_value or 0)

    if 0.0 <= raw_value <= 1.0:
        return _clamp_score_100(raw_value * 100.0)

    if 0.0 <= raw_value <= 10.0:
        return _clamp_score_100(raw_value * 10.0)

    return _clamp_score_100(raw_value)


def _resolve_model_path(relative_path):
    return (BASE_DIR / relative_path).resolve()


def _load_model(relative_path):
    full_path = str(_resolve_model_path(relative_path))
    if full_path not in _MODEL_CACHE:
        _MODEL_CACHE[full_path] = joblib.load(full_path)
    return _MODEL_CACHE[full_path]


def _get_model_artifact_for_criterion(conn, criterion_id, criterion_code):
    row = _fetch_one(conn, """
        SELECT id, artifact_path
        FROM ml_models
        WHERE is_active = TRUE
          AND (criterion_id = :criterion_id OR criterion_id IS NULL)
        ORDER BY
            CASE WHEN criterion_id = :criterion_id THEN 0 ELSE 1 END,
            created_at DESC
        LIMIT 1
    """, {
        "criterion_id": criterion_id,
    })

    if row and row["artifact_path"]:
        return row["id"], row["artifact_path"]

    model_group = CRITERION_TO_MODEL_GROUP.get(criterion_code)
    if not model_group:
        return None, None

    return None, DEFAULT_MODEL_PATHS.get(model_group)


def _predict_model_score(model, feature_map):
    df7 = pd.DataFrame([{
        "Norm_CPU": feature_map["Norm_CPU"],
        "Norm_RAM": feature_map["Norm_RAM"],
        "Norm_GPU": feature_map["Norm_GPU"],
        "Norm_Screen": feature_map["Norm_Screen"],
        "Norm_Weight": feature_map["Norm_Weight"],
        "Norm_Battery": feature_map["Norm_Battery"],
        "Norm_Durability": feature_map["Norm_Durability"],
    }])

    arr7 = np.array([[feature_map[col] for col in MODEL_INPUT_COLUMNS_7]], dtype=float)

    attempts = [df7, arr7]
    last_error = None

    for X in attempts:
        try:
            pred = model.predict(X)
            raw_prediction = float(pred[0])
            score_100 = _normalize_prediction_to_score_100(raw_prediction)
            return raw_prediction, score_100
        except Exception as e:
            last_error = e

    raise last_error


def get_form_options(conn):
    usage_profiles = _fetch_all(conn, """
        SELECT code, name
        FROM usage_profiles
        WHERE is_active = TRUE
        ORDER BY id
    """)

    brands = _fetch_all(conn, """
        SELECT code, name
        FROM brands
        ORDER BY name
    """)

    cpus = _fetch_all(conn, """
        SELECT code, display_name, benchmark_score
        FROM cpu_reference
        ORDER BY tier_rank, display_name
    """)

    gpus = _fetch_all(conn, """
        SELECT code, display_name, benchmark_score
        FROM gpu_reference
        ORDER BY tier_rank, display_name
    """)

    return {
        "usageProfiles": [dict(x) for x in usage_profiles],
        "brands": [dict(x) for x in brands],
        "cpuReferences": [
            {
                **dict(x),
                "benchmark_score": _float_or_none(x["benchmark_score"]),
            }
            for x in cpus
        ],
        "gpuReferences": [
            {
                **dict(x),
                "benchmark_score": _float_or_none(x["benchmark_score"]),
            }
            for x in gpus
        ],
    }


def create_session_and_filters(conn, payload, user_id=None):
    usage_code = payload["usageProfile"]
    budget = payload.get("budget", {})
    filters = payload.get("filters", {})
    top_n = payload.get("topN", 10)

    usage_profile = _fetch_one(conn, """
        SELECT id, code, name
        FROM usage_profiles
        WHERE code = :code AND is_active = TRUE
    """, {"code": usage_code})

    if not usage_profile:
        raise ValueError("usageProfile không hợp lệ")

    brand = None
    if filters.get("brandCode"):
        brand = _fetch_one(conn, """
            SELECT id, code, name
            FROM brands
            WHERE code = :code
        """, {"code": filters["brandCode"]})
        if not brand:
            raise ValueError("brandCode không hợp lệ")

    cpu_ref = None
    if filters.get("cpuCode"):
        cpu_ref = _fetch_one(conn, """
            SELECT id, code, display_name, benchmark_score
            FROM cpu_reference
            WHERE code = :code
        """, {"code": filters["cpuCode"]})
        if not cpu_ref:
            raise ValueError("cpuCode không hợp lệ")

    gpu_ref = None
    if filters.get("gpuCode"):
        gpu_ref = _fetch_one(conn, """
            SELECT id, code, display_name, benchmark_score
            FROM gpu_reference
            WHERE code = :code
        """, {"code": filters["gpuCode"]})
        if not gpu_ref:
            raise ValueError("gpuCode không hợp lệ")

    session_row = _fetch_one(conn, """
        INSERT INTO evaluation_sessions (
            user_id,
            usage_profile_id,
            mode,
            request_payload,
            top_n,
            status,
            budget_min,
            budget_max
        )
        VALUES (
            :user_id,
            :usage_profile_id,
            :mode,
            CAST(:request_payload AS JSONB),
            :top_n,
            'created',
            :budget_min,
            :budget_max
        )
        RETURNING id, session_key
    """, {
        "user_id": user_id,
        "usage_profile_id": usage_profile["id"],
        "mode": payload.get("mode", "advanced"),
        "request_payload": json.dumps(payload),
        "top_n": top_n,
        "budget_min": budget.get("min"),
        "budget_max": budget.get("max"),
    })

    conn.execute(text("""
        INSERT INTO evaluation_filters (
            evaluation_session_id,
            brand_id,
            requested_cpu_reference_id,
            requested_gpu_reference_id,
            min_price,
            max_price,
            min_ram_gb,
            min_ssd_gb,
            min_cpu_benchmark_score,
            min_gpu_benchmark_score,
            min_screen_size_inch,
            max_screen_size_inch,
            max_weight_kg,
            min_battery_hours,
            require_in_stock
        )
        VALUES (
            :sid,
            :brand_id,
            :cpu_ref_id,
            :gpu_ref_id,
            :min_price,
            :max_price,
            :min_ram_gb,
            :min_ssd_gb,
            :min_cpu_score,
            :min_gpu_score,
            :screen_min,
            :screen_max,
            :max_weight,
            :min_battery,
            TRUE
        )
    """), {
        "sid": session_row["id"],
        "brand_id": brand["id"] if brand else None,
        "cpu_ref_id": cpu_ref["id"] if cpu_ref else None,
        "gpu_ref_id": gpu_ref["id"] if gpu_ref else None,
        "min_price": budget.get("min"),
        "max_price": budget.get("max"),
        "min_ram_gb": filters.get("minRamGb"),
        "min_ssd_gb": filters.get("minSsdGb"),
        "min_cpu_score": cpu_ref["benchmark_score"] if cpu_ref else None,
        "min_gpu_score": gpu_ref["benchmark_score"] if gpu_ref else None,
        "screen_min": filters.get("screenSizeMin"),
        "screen_max": filters.get("screenSizeMax"),
        "max_weight": filters.get("maxWeightKg"),
        "min_battery": filters.get("minBatteryHours"),
    })

    return {
        "session_id": session_row["id"],
        "session_key": str(session_row["session_key"]),
        "usage_profile": usage_profile,
        "brand": brand,
        "cpu_ref": cpu_ref,
        "gpu_ref": gpu_ref,
    }


def run_hard_filter(conn, session_id):
    filt = _fetch_one(conn, """
        SELECT *
        FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """, {"sid": session_id})

    laptops = _fetch_all(conn, """
        SELECT
            l.id,
            l.name,
            l.price,
            l.ram_gb,
            l.ssd_gb,
            l.cpu_benchmark_score,
            l.gpu_benchmark_score,
            l.screen_size_inch,
            l.weight_kg,
            l.battery_hours,
            l.stock_quantity,
            l.brand_id
        FROM laptops l
        WHERE l.is_active = TRUE
    """)

    total = len(laptops)
    passed_count = 0

    for laptop in laptops:
        failed_rules = []

        if filt["brand_id"] and laptop["brand_id"] != filt["brand_id"]:
            failed_rules.append("brand")
        if filt["min_price"] and laptop["price"] < filt["min_price"]:
            failed_rules.append("min_price")
        if filt["max_price"] and laptop["price"] > filt["max_price"]:
            failed_rules.append("max_price")
        if filt["min_ram_gb"] and laptop["ram_gb"] < filt["min_ram_gb"]:
            failed_rules.append("min_ram_gb")
        if filt["min_ssd_gb"] and laptop["ssd_gb"] < filt["min_ssd_gb"]:
            failed_rules.append("min_ssd_gb")
        if filt["min_cpu_benchmark_score"] and ((laptop["cpu_benchmark_score"] or 0) < filt["min_cpu_benchmark_score"]):
            failed_rules.append("min_cpu_benchmark_score")
        if filt["min_gpu_benchmark_score"] and ((laptop["gpu_benchmark_score"] or 0) < filt["min_gpu_benchmark_score"]):
            failed_rules.append("min_gpu_benchmark_score")
        if filt["min_screen_size_inch"] and ((laptop["screen_size_inch"] or 0) < filt["min_screen_size_inch"]):
            failed_rules.append("min_screen_size_inch")
        if filt["max_screen_size_inch"] and ((laptop["screen_size_inch"] or 999) > filt["max_screen_size_inch"]):
            failed_rules.append("max_screen_size_inch")
        if filt["max_weight_kg"] and ((laptop["weight_kg"] or 999) > filt["max_weight_kg"]):
            failed_rules.append("max_weight_kg")
        if filt["min_battery_hours"] and ((laptop["battery_hours"] or 0) < filt["min_battery_hours"]):
            failed_rules.append("min_battery_hours")
        if filt["require_in_stock"] and (laptop["stock_quantity"] or 0) <= 0:
            failed_rules.append("stock_quantity")

        is_passed = len(failed_rules) == 0
        if is_passed:
            passed_count += 1

        conn.execute(text("""
            INSERT INTO evaluation_candidates (
                evaluation_session_id,
                laptop_id,
                hard_filter_passed,
                failed_rules
            )
            VALUES (
                :sid,
                :laptop_id,
                :passed,
                CAST(:failed_rules AS JSONB)
            )
            ON CONFLICT (evaluation_session_id, laptop_id)
            DO UPDATE SET
                hard_filter_passed = EXCLUDED.hard_filter_passed,
                failed_rules = EXCLUDED.failed_rules
        """), {
            "sid": session_id,
            "laptop_id": laptop["id"],
            "passed": is_passed,
            "failed_rules": json.dumps(failed_rules),
        })

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET
            status = 'filtered',
            hard_filter_total_count = :total,
            hard_filter_pass_count = :passed
        WHERE id = :sid
    """), {"sid": session_id, "total": total, "passed": passed_count})

    return {"total": total, "passed": passed_count}


def infer_priorities(conn, session_id):
    session_row = _fetch_one(conn, """
        SELECT es.id, up.id AS usage_profile_id, up.code AS usage_profile_code
        FROM evaluation_sessions es
        JOIN usage_profiles up ON up.id = es.usage_profile_id
        WHERE es.id = :sid
    """, {"sid": session_id})

    filt = _fetch_one(conn, """
        SELECT *
        FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """, {"sid": session_id})

    rules = _fetch_all(conn, """
        SELECT
            rc.id AS criterion_id,
            rc.code,
            rc.name,
            rc.sort_order,
            upr.base_score,
            upr.explanation_template
        FROM usage_profile_criterion_rules upr
        JOIN recommendation_criteria rc ON rc.id = upr.criterion_id
        WHERE upr.usage_profile_id = :usage_profile_id
        ORDER BY rc.sort_order
    """, {"usage_profile_id": session_row["usage_profile_id"]})

    conn.execute(text("""
        DELETE FROM session_inferred_priorities
        WHERE evaluation_session_id = :sid
    """), {"sid": session_id})

    priorities = {}
    by_code = {}

    for rule in rules:
        priorities[rule["code"]] = float(rule["base_score"])
        by_code[rule["code"]] = rule
        conn.execute(text("""
            INSERT INTO session_inferred_priorities (
                evaluation_session_id, criterion_id, source_type, source_key,
                score_delta, final_score_after, explanation_text
            )
            VALUES (
                :sid, :criterion_id, 'profile', :source_key,
                :score_delta, :final_score_after, :explanation
            )
        """), {
            "sid": session_id,
            "criterion_id": rule["criterion_id"],
            "source_key": session_row["usage_profile_code"],
            "score_delta": float(rule["base_score"]),
            "final_score_after": float(rule["base_score"]),
            "explanation": rule["explanation_template"],
        })

    def add_filter_boost(code, delta, source_key, explanation):
        priorities[code] = priorities.get(code, 0) + delta
        conn.execute(text("""
            INSERT INTO session_inferred_priorities (
                evaluation_session_id, criterion_id, source_type, source_key,
                score_delta, final_score_after, explanation_text
            )
            VALUES (
                :sid, :criterion_id, 'filter', :source_key,
                :score_delta, :final_score_after, :explanation
            )
        """), {
            "sid": session_id,
            "criterion_id": by_code[code]["criterion_id"],
            "source_key": source_key,
            "score_delta": delta,
            "final_score_after": priorities[code],
            "explanation": explanation,
        })

    if filt["min_ram_gb"]:
        if filt["min_ram_gb"] >= 32:
            add_filter_boost("ram", 2.0, "minRamGb", "RAM được tăng vì bạn yêu cầu từ 32GB trở lên.")
        elif filt["min_ram_gb"] >= 16:
            add_filter_boost("ram", 1.0, "minRamGb", "RAM được tăng vì bạn yêu cầu từ 16GB trở lên.")

    if filt["min_cpu_benchmark_score"]:
        add_filter_boost("cpu", 1.5, "cpuCode", "CPU được tăng vì bạn chọn mức CPU tham chiếu cao.")

    if filt["min_gpu_benchmark_score"]:
        add_filter_boost("gpu", 1.5, "gpuCode", "GPU được tăng vì bạn chọn mức GPU tham chiếu cao.")

    if filt["min_screen_size_inch"] and filt["min_screen_size_inch"] >= 15.6:
        add_filter_boost("screen", 1.0, "screenSizeMin", "Màn hình được tăng vì bạn muốn màn hình lớn.")

    if filt["max_weight_kg"] and filt["max_weight_kg"] <= 2.0:
        add_filter_boost("weight", 1.0, "maxWeightKg", "Trọng lượng được tăng vì bạn yêu cầu máy nhẹ.")

    if filt["min_battery_hours"] and filt["min_battery_hours"] >= 6:
        add_filter_boost("battery", 1.0, "minBatteryHours", "Pin được tăng vì bạn yêu cầu pin tối thiểu khá cao.")

    if filt["min_ssd_gb"] and filt["min_ssd_gb"] >= 1000:
        add_filter_boost("upgradeability", 0.5, "minSsdGb", "Khả năng nâng cấp được tăng do nhu cầu lưu trữ cao.")

    for code, score in priorities.items():
        conn.execute(text("""
            INSERT INTO session_inferred_priorities (
                evaluation_session_id, criterion_id, source_type, source_key,
                score_delta, final_score_after, explanation_text
            )
            VALUES (
                :sid, :criterion_id, 'combined', 'final',
                0, :final_score_after, :explanation
            )
        """), {
            "sid": session_id,
            "criterion_id": by_code[code]["criterion_id"],
            "final_score_after": score,
            "explanation": f"Điểm ưu tiên cuối cho {code} là {score:.2f}",
        })

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET status = 'inferred'
        WHERE id = :sid
    """), {"sid": session_id})

    return [
        {"code": code, "score": score}
        for code, score in sorted(priorities.items(), key=lambda x: x[1], reverse=True)
    ]


def calculate_and_store_ahp(conn, session_id):
    rows = _fetch_all(conn, """
        SELECT
            rc.id AS criterion_id,
            rc.code,
            rc.name,
            rc.sort_order,
            sip.final_score_after AS score
        FROM session_inferred_priorities sip
        JOIN recommendation_criteria rc ON rc.id = sip.criterion_id
        WHERE sip.evaluation_session_id = :sid
          AND sip.source_type = 'combined'
          AND sip.source_key = 'final'
        ORDER BY rc.sort_order
    """, {"sid": session_id})

    if not rows:
        raise ValueError("Chưa có inferred priorities để tính AHP")

    ahp = build_ahp([
        {
            "criterion_id": r["criterion_id"],
            "code": r["code"],
            "name": r["name"],
            "score": float(r["score"]),
        }
        for r in rows
    ])

    conn.execute(text("DELETE FROM evaluation_pairwise_matrix WHERE evaluation_session_id = :sid"), {"sid": session_id})
    conn.execute(text("DELETE FROM evaluation_ahp_matrix_cells WHERE evaluation_session_id = :sid"), {"sid": session_id})
    conn.execute(text("DELETE FROM evaluation_weights WHERE evaluation_session_id = :sid"), {"sid": session_id})
    conn.execute(text("DELETE FROM evaluation_ahp_summary WHERE evaluation_session_id = :sid"), {"sid": session_id})

    pairwise = ahp["pairwise_matrix"]
    normalized = ahp["normalized_matrix"]
    weights = ahp["weights"]
    summary = ahp["summary"]

    for i, row_i in enumerate(rows):
        for j, row_j in enumerate(rows):
            if i != j:
                conn.execute(text("""
                    INSERT INTO evaluation_pairwise_matrix (
                        evaluation_session_id, criterion_1_id, criterion_2_id, comparison_value, source_type
                    )
                    VALUES (:sid, :c1, :c2, :val, 'derived')
                    ON CONFLICT (evaluation_session_id, criterion_1_id, criterion_2_id)
                    DO UPDATE SET comparison_value = EXCLUDED.comparison_value
                """), {
                    "sid": session_id,
                    "c1": row_i["criterion_id"],
                    "c2": row_j["criterion_id"],
                    "val": pairwise[i][j],
                })

            conn.execute(text("""
                INSERT INTO evaluation_ahp_matrix_cells (
                    evaluation_session_id, matrix_type, row_criterion_id, col_criterion_id, cell_value
                )
                VALUES (:sid, 'pairwise', :r, :c, :val)
                ON CONFLICT (evaluation_session_id, matrix_type, row_criterion_id, col_criterion_id)
                DO UPDATE SET cell_value = EXCLUDED.cell_value
            """), {
                "sid": session_id,
                "r": row_i["criterion_id"],
                "c": row_j["criterion_id"],
                "val": pairwise[i][j],
            })

            conn.execute(text("""
                INSERT INTO evaluation_ahp_matrix_cells (
                    evaluation_session_id, matrix_type, row_criterion_id, col_criterion_id, cell_value
                )
                VALUES (:sid, 'normalized', :r, :c, :val)
                ON CONFLICT (evaluation_session_id, matrix_type, row_criterion_id, col_criterion_id)
                DO UPDATE SET cell_value = EXCLUDED.cell_value
            """), {
                "sid": session_id,
                "r": row_i["criterion_id"],
                "c": row_j["criterion_id"],
                "val": normalized[i][j],
            })

    for i, row in enumerate(rows):
        conn.execute(text("""
            INSERT INTO evaluation_weights (
                evaluation_session_id, criterion_id, source_score,
                raw_weight, normalized_weight, display_order, explanation_text
            )
            VALUES (
                :sid, :criterion_id, :source_score,
                :raw_weight, :normalized_weight, :display_order, :explanation
            )
            ON CONFLICT (evaluation_session_id, criterion_id)
            DO UPDATE SET
                source_score = EXCLUDED.source_score,
                raw_weight = EXCLUDED.raw_weight,
                normalized_weight = EXCLUDED.normalized_weight,
                display_order = EXCLUDED.display_order,
                explanation_text = EXCLUDED.explanation_text
        """), {
            "sid": session_id,
            "criterion_id": row["criterion_id"],
            "source_score": row["score"],
            "raw_weight": weights[i],
            "normalized_weight": weights[i],
            "display_order": row["sort_order"],
            "explanation": f"{row['name']} có trọng số {weights[i]:.4f}",
        })

    conn.execute(text("""
        INSERT INTO evaluation_ahp_summary (
            evaluation_session_id, criteria_count, lambda_max, ci, ri, cr, is_consistent
        )
        VALUES (
            :sid, :criteria_count, :lambda_max, :ci, :ri, :cr, :is_consistent
        )
        ON CONFLICT (evaluation_session_id)
        DO UPDATE SET
            criteria_count = EXCLUDED.criteria_count,
            lambda_max = EXCLUDED.lambda_max,
            ci = EXCLUDED.ci,
            ri = EXCLUDED.ri,
            cr = EXCLUDED.cr,
            is_consistent = EXCLUDED.is_consistent
    """), {"sid": session_id, **summary})

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET
            status = 'weighted',
            ahp_ci = :ci,
            ahp_cr = :cr,
            ahp_is_consistent = :is_consistent
        WHERE id = :sid
    """), {
        "sid": session_id,
        "ci": summary["ci"],
        "cr": summary["cr"],
        "is_consistent": summary["is_consistent"],
    })

    return {
        "summary": summary,
        "weights": [
            {
                "criterion": rows[i]["code"],
                "weight": weights[i],
            }
            for i in range(len(rows))
        ],
    }


def ai_score_candidates(conn, session_id):
    conn.execute(text("""
        DELETE FROM evaluation_ai_scores
        WHERE evaluation_session_id = :sid
    """), {"sid": session_id})

    candidates = _fetch_all(conn, """
        SELECT
            ec.laptop_id,
            l.price,
            f.norm_cpu, f.norm_ram, f.norm_gpu, f.norm_screen,
            f.norm_weight, f.norm_battery, f.norm_durability, f.norm_upgradeability
        FROM evaluation_candidates ec
        JOIN laptops l ON l.id = ec.laptop_id
        JOIN laptop_ml_features f ON f.laptop_id = ec.laptop_id
        WHERE ec.evaluation_session_id = :sid
          AND ec.hard_filter_passed = TRUE
    """, {"sid": session_id})

    criteria = _fetch_all(conn, """
        SELECT id, code
        FROM recommendation_criteria
        WHERE is_active = TRUE
        ORDER BY sort_order
    """)

    for c in candidates:
        feature_map = {
            "Norm_CPU": float(c["norm_cpu"] or 0),
            "Norm_RAM": float(c["norm_ram"] or 0),
            "Norm_GPU": float(c["norm_gpu"] or 0),
            "Norm_Screen": float(c["norm_screen"] or 0),
            "Norm_Weight": float(c["norm_weight"] or 0),
            "Norm_Battery": float(c["norm_battery"] or 0),
            "Norm_Durability": float(c["norm_durability"] or 0),
            "Norm_Upgrade": float(c["norm_upgradeability"] or 0),
            "Price (VND)": float(c["price"] or 0),
        }

        for criterion in criteria:
            criterion_code = criterion["code"]

            if criterion_code == "battery":
                raw_prediction = feature_map["Norm_Battery"]
                score_100 = _clamp_score_100(raw_prediction * 100.0)
                model_id = None

            elif criterion_code == "durability":
                raw_prediction = feature_map["Norm_Durability"]
                score_100 = _clamp_score_100(raw_prediction * 100.0)
                model_id = None

            elif criterion_code == "upgradeability":
                raw_prediction = feature_map["Norm_Upgrade"]
                score_100 = _clamp_score_100(raw_prediction * 100.0)
                model_id = None

            else:
                feature_name = CRITERION_TO_FEATURE[criterion_code]
                fallback_raw = float(c[feature_name] or 0)
                fallback_score_100 = _clamp_score_100(fallback_raw * 100.0)

                model_id, artifact_path = _get_model_artifact_for_criterion(
                    conn=conn,
                    criterion_id=criterion["id"],
                    criterion_code=criterion_code,
                )

                raw_prediction = fallback_raw
                score_100 = fallback_score_100

                if artifact_path:
                    try:
                        model = _load_model(artifact_path)
                        raw_prediction, score_100 = _predict_model_score(model, feature_map)
                    except Exception:
                        raw_prediction = fallback_raw
                        score_100 = fallback_score_100

            conn.execute(text("""
                INSERT INTO evaluation_ai_scores (
                    evaluation_session_id, laptop_id, criterion_id, model_id,
                    raw_prediction, normalized_prediction, score_100, input_snapshot
                )
                VALUES (
                    :sid, :laptop_id, :criterion_id, :model_id,
                    :raw_prediction, :normalized_prediction, :score_100, CAST(:input_snapshot AS JSONB)
                )
            """), {
                "sid": session_id,
                "laptop_id": c["laptop_id"],
                "criterion_id": criterion["id"],
                "model_id": model_id,
                "raw_prediction": raw_prediction,
                "normalized_prediction": raw_prediction,
                "score_100": score_100,
                "input_snapshot": json.dumps(feature_map),
            })

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET status = 'scored'
        WHERE id = :sid
    """), {"sid": session_id})


def rank_candidates(conn, session_id):
    top_n_row = _fetch_one(conn, """
        SELECT top_n
        FROM evaluation_sessions
        WHERE id = :sid
    """, {"sid": session_id})
    top_n = int(top_n_row["top_n"] or 10)

    conn.execute(text("""
        DELETE FROM evaluation_result_details
        WHERE evaluation_result_id IN (
            SELECT id FROM evaluation_results WHERE evaluation_session_id = :sid
        )
    """), {"sid": session_id})
    conn.execute(text("""
        DELETE FROM evaluation_results
        WHERE evaluation_session_id = :sid
    """), {"sid": session_id})

    weights = {
        row["criterion_id"]: float(row["normalized_weight"])
        for row in _fetch_all(conn, """
            SELECT criterion_id, normalized_weight
            FROM evaluation_weights
            WHERE evaluation_session_id = :sid
        """, {"sid": session_id})
    }

    score_rows = _fetch_all(conn, """
        SELECT laptop_id, criterion_id, score_100
        FROM evaluation_ai_scores
        WHERE evaluation_session_id = :sid
    """, {"sid": session_id})

    grouped = defaultdict(list)
    for row in score_rows:
        grouped[row["laptop_id"]].append(row)

    ranking = []
    for laptop_id, details in grouped.items():
        total = 0.0
        for d in details:
            total += float(d["score_100"]) * weights.get(d["criterion_id"], 0)
        ranking.append({
            "laptop_id": laptop_id,
            "total_score": total,
            "match_percent": min(total, 100.0),
        })

    ranking.sort(key=lambda x: x["total_score"], reverse=True)
    ranking = ranking[:top_n]

    for idx, item in enumerate(ranking, start=1):
        result_row = _fetch_one(conn, """
            INSERT INTO evaluation_results (
                evaluation_session_id, laptop_id, total_score, match_percent, rank_position
            )
            VALUES (:sid, :laptop_id, :total_score, :match_percent, :rank_position)
            RETURNING id
        """, {
            "sid": session_id,
            "laptop_id": item["laptop_id"],
            "total_score": item["total_score"],
            "match_percent": item["match_percent"],
            "rank_position": idx,
        })

        for d in grouped[item["laptop_id"]]:
            w = weights.get(d["criterion_id"], 0)
            weighted_score = float(d["score_100"]) * w
            conn.execute(text("""
                INSERT INTO evaluation_result_details (
                    evaluation_result_id, criterion_id, criterion_weight,
                    ai_score_100, weighted_score, explanation_data
                )
                VALUES (
                    :result_id, :criterion_id, :criterion_weight,
                    :ai_score_100, :weighted_score, CAST(:explanation_data AS JSONB)
                )
            """), {
                "result_id": result_row["id"],
                "criterion_id": d["criterion_id"],
                "criterion_weight": w,
                "ai_score_100": d["score_100"],
                "weighted_score": weighted_score,
                "explanation_data": json.dumps({"formula": "ai_score_100 * criterion_weight"}),
            })

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET status = 'ranked'
        WHERE id = :sid
    """), {"sid": session_id})


def generate_reasons(conn, session_id):
    conn.execute(text("""
        DELETE FROM evaluation_result_reasons
        WHERE evaluation_result_id IN (
            SELECT id FROM evaluation_results WHERE evaluation_session_id = :sid
        )
    """), {"sid": session_id})

    filt = _fetch_one(conn, """
        SELECT * FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """, {"sid": session_id})

    results = _fetch_all(conn, """
        SELECT er.id AS evaluation_result_id, er.laptop_id, l.name, l.ram_gb, l.ssd_gb,
               l.weight_kg, l.battery_hours, l.cpu_benchmark_score, l.gpu_benchmark_score
        FROM evaluation_results er
        JOIN laptops l ON l.id = er.laptop_id
        WHERE er.evaluation_session_id = :sid
        ORDER BY er.rank_position
    """, {"sid": session_id})

    for row in results:
        badges = []

        if filt["min_ram_gb"] and row["ram_gb"] >= filt["min_ram_gb"]:
            badges.append(("ram_match", "RAM đúng nhu cầu", "RAM đáp ứng đúng mức bạn yêu cầu."))
        if filt["min_ssd_gb"] and row["ssd_gb"] >= filt["min_ssd_gb"]:
            badges.append(("ssd_match", "SSD đúng nhu cầu", "SSD đáp ứng mức lưu trữ bạn yêu cầu."))
        if filt["max_weight_kg"] and (row["weight_kg"] or 999) <= filt["max_weight_kg"]:
            badges.append(("lightweight", "Máy nhẹ", "Máy phù hợp với nhu cầu di chuyển."))
        if filt["min_battery_hours"] and (row["battery_hours"] or 0) >= filt["min_battery_hours"]:
            badges.append(("battery_ok", "Pin tốt", "Pin đáp ứng mức tối thiểu bạn yêu cầu."))

        top_details = _fetch_all(conn, """
            SELECT rc.code, rc.name, erd.ai_score_100, erd.criterion_weight
            FROM evaluation_result_details erd
            JOIN recommendation_criteria rc ON rc.id = erd.criterion_id
            WHERE erd.evaluation_result_id = :rid
            ORDER BY erd.weighted_score DESC
            LIMIT 2
        """, {"rid": row["evaluation_result_id"]})

        for d in top_details:
            badges.append((
                f"top_{d['code']}",
                f"Mạnh về {d['name']}",
                f"{d['name']} là một trong các điểm mạnh nổi bật của máy này.",
            ))

        seen = set()
        order = 1
        for code, label, reason in badges:
            if code in seen:
                continue
            seen.add(code)
            conn.execute(text("""
                INSERT INTO evaluation_result_reasons (
                    evaluation_result_id, badge_code, badge_label, reason_text, priority_order
                )
                VALUES (:rid, :badge_code, :badge_label, :reason_text, :priority_order)
            """), {
                "rid": row["evaluation_result_id"],
                "badge_code": code,
                "badge_label": label,
                "reason_text": reason,
                "priority_order": order,
            })
            order += 1

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
        WHERE id = :sid
    """), {"sid": session_id})


def get_dashboard(conn, session_key):
    session_row = _fetch_one(conn, """
        SELECT
            es.id,
            es.session_key,
            es.status,
            es.top_n,
            es.hard_filter_total_count,
            es.hard_filter_pass_count,
            up.code AS usage_profile_code,
            up.name AS usage_profile_name
        FROM evaluation_sessions es
        JOIN usage_profiles up ON up.id = es.usage_profile_id
        WHERE es.session_key::text = :session_key
    """, {"session_key": session_key})

    if not session_row:
        return None

    inferred = _fetch_all(conn, """
        SELECT rc.code AS criterion, rc.name, sip.final_score_after AS score, sip.explanation_text
        FROM session_inferred_priorities sip
        JOIN recommendation_criteria rc ON rc.id = sip.criterion_id
        WHERE sip.evaluation_session_id = :sid
          AND sip.source_type = 'combined'
          AND sip.source_key = 'final'
        ORDER BY sip.final_score_after DESC, rc.sort_order
    """, {"sid": session_row["id"]})

    weights = _fetch_all(conn, """
        SELECT rc.code AS criterion, rc.name, ew.normalized_weight AS weight, ew.explanation_text
        FROM evaluation_weights ew
        JOIN recommendation_criteria rc ON rc.id = ew.criterion_id
        WHERE ew.evaluation_session_id = :sid
        ORDER BY ew.display_order
    """, {"sid": session_row["id"]})

    ahp_summary = _fetch_one(conn, """
        SELECT criteria_count, lambda_max, ci, ri, cr, is_consistent
        FROM evaluation_ahp_summary
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    ahp_pairwise = _fetch_all(conn, """
        SELECT
            row_rc.code AS row_criterion,
            col_rc.code AS col_criterion,
            c.cell_value
        FROM evaluation_ahp_matrix_cells c
        JOIN recommendation_criteria row_rc ON row_rc.id = c.row_criterion_id
        JOIN recommendation_criteria col_rc ON col_rc.id = c.col_criterion_id
        WHERE c.evaluation_session_id = :sid
          AND c.matrix_type = 'pairwise'
        ORDER BY row_rc.sort_order, col_rc.sort_order
    """, {"sid": session_row["id"]})

    ahp_normalized = _fetch_all(conn, """
        SELECT
            row_rc.code AS row_criterion,
            col_rc.code AS col_criterion,
            c.cell_value
        FROM evaluation_ahp_matrix_cells c
        JOIN recommendation_criteria row_rc ON row_rc.id = c.row_criterion_id
        JOIN recommendation_criteria col_rc ON col_rc.id = c.col_criterion_id
        WHERE c.evaluation_session_id = :sid
          AND c.matrix_type = 'normalized'
        ORDER BY row_rc.sort_order, col_rc.sort_order
    """, {"sid": session_row["id"]})

    results = _fetch_all(conn, """
        SELECT
            er.id AS evaluation_result_id,
            er.rank_position,
            er.match_percent,
            l.id AS laptop_id,
            l.name AS laptop_name,
            b.name AS brand_name,
            l.price,
            COALESCE(li.image_url, l.image_url) AS image_url
        FROM evaluation_results er
        JOIN laptops l ON l.id = er.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN LATERAL (
            SELECT image_url
            FROM laptop_images
            WHERE laptop_id = l.id AND is_primary = TRUE
            ORDER BY sort_order, id
            LIMIT 1
        ) li ON TRUE
        WHERE er.evaluation_session_id = :sid
        ORDER BY er.rank_position
    """, {"sid": session_row["id"]})

    final_results = []
    for r in results:
        reasons = _fetch_all(conn, """
            SELECT badge_code, badge_label, reason_text, priority_order
            FROM evaluation_result_reasons
            WHERE evaluation_result_id = :rid
            ORDER BY priority_order
        """, {"rid": r["evaluation_result_id"]})

        detail_scores = _fetch_all(conn, """
            SELECT rc.code AS criterion, erd.ai_score_100
            FROM evaluation_result_details erd
            JOIN recommendation_criteria rc ON rc.id = erd.criterion_id
            WHERE erd.evaluation_result_id = :rid
        """, {"rid": r["evaluation_result_id"]})

        final_results.append({
            "rank": r["rank_position"],
            "laptopId": r["laptop_id"],
            "laptopName": r["laptop_name"],
            "brand": r["brand_name"],
            "price": _float_or_none(r["price"]),
            "imageUrl": r["image_url"],
            "matchPercent": _float_or_none(r["match_percent"]),
            "criteriaScores": {
                d["criterion"]: _float_or_none(d["ai_score_100"])
                for d in detail_scores
            },
            "reasons": [x["badge_label"] for x in reasons],
        })

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "usageProfile": session_row["usage_profile_code"],
            "usageProfileName": session_row["usage_profile_name"],
            "status": session_row["status"],
            "topN": session_row["top_n"],
            "hardFilterTotalCount": session_row["hard_filter_total_count"],
            "hardFilterPassCount": session_row["hard_filter_pass_count"],
        },
        "inferredPriorities": [
            {
                "criterion": x["criterion"],
                "name": x["name"],
                "score": _float_or_none(x["score"]),
                "explanation": x["explanation_text"],
            }
            for x in inferred
        ],
        "ahp": {
            "weights": [
                {
                    "criterion": x["criterion"],
                    "name": x["name"],
                    "weight": _float_or_none(x["weight"]),
                    "explanation": x["explanation_text"],
                }
                for x in weights
            ],
            "pairwiseMatrix": [
                {
                    "row": x["row_criterion"],
                    "col": x["col_criterion"],
                    "value": _float_or_none(x["cell_value"]),
                }
                for x in ahp_pairwise
            ],
            "normalizedMatrix": [
                {
                    "row": x["row_criterion"],
                    "col": x["col_criterion"],
                    "value": _float_or_none(x["cell_value"]),
                }
                for x in ahp_normalized
            ],
            "consistency": {
                "criteriaCount": ahp_summary["criteria_count"] if ahp_summary else None,
                "lambdaMax": _float_or_none(ahp_summary["lambda_max"]) if ahp_summary else None,
                "ci": _float_or_none(ahp_summary["ci"]) if ahp_summary else None,
                "ri": _float_or_none(ahp_summary["ri"]) if ahp_summary else None,
                "cr": _float_or_none(ahp_summary["cr"]) if ahp_summary else None,
                "isConsistent": ahp_summary["is_consistent"] if ahp_summary else None,
            },
        },
        "results": final_results,
    }


def run_full_pipeline(conn, payload, user_id=None):
    created = create_session_and_filters(conn, payload, user_id=user_id)
    session_id = created["session_id"]

    hard_filter = run_hard_filter(conn, session_id)
    infer_priorities(conn, session_id)
    calculate_and_store_ahp(conn, session_id)
    ai_score_candidates(conn, session_id)
    rank_candidates(conn, session_id)
    generate_reasons(conn, session_id)

    dashboard = get_dashboard(conn, created["session_key"])
    dashboard["session"]["hardFilterTotalCount"] = hard_filter["total"]
    dashboard["session"]["hardFilterPassCount"] = hard_filter["passed"]
    return dashboard


def _get_session_by_key(conn, session_key):
    return _fetch_one(conn, """
        SELECT
            es.id,
            es.session_key,
            es.mode,
            es.top_n,
            es.status,
            es.request_payload,
            es.budget_min,
            es.budget_max,
            up.id AS usage_profile_id,
            up.code AS usage_profile_code,
            up.name AS usage_profile_name
        FROM evaluation_sessions es
        JOIN usage_profiles up ON up.id = es.usage_profile_id
        WHERE es.session_key::text = :session_key
    """, {"session_key": session_key})


def create_session_only(conn, payload, user_id=None):
    usage_code = payload["usageProfile"]
    mode = payload.get("mode", "advanced")
    top_n = payload.get("topN", 10)

    usage_profile = _fetch_one(conn, """
        SELECT id, code, name
        FROM usage_profiles
        WHERE code = :code AND is_active = TRUE
    """, {"code": usage_code})

    if not usage_profile:
        raise ValueError("usageProfile không hợp lệ")

    session_row = _fetch_one(conn, """
        INSERT INTO evaluation_sessions (
            user_id,
            usage_profile_id,
            mode,
            request_payload,
            top_n,
            status
        )
        VALUES (
            :user_id,
            :usage_profile_id,
            :mode,
            CAST(:request_payload AS JSONB),
            :top_n,
            'created'
        )
        RETURNING id, session_key
    """, {
        "user_id": user_id,
        "usage_profile_id": usage_profile["id"],
        "mode": mode,
        "request_payload": json.dumps(payload),
        "top_n": top_n,
    })

    return {
        "sessionId": session_row["id"],
        "sessionKey": str(session_row["session_key"]),
        "usageProfile": usage_profile["code"],
        "usageProfileName": usage_profile["name"],
        "status": "created",
        "mode": mode,
        "topN": top_n,
    }


def save_filters_to_session(conn, session_key, payload):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    budget = payload.get("budget", {})
    filters = payload.get("filters", {})

    brand = None
    if filters.get("brandCode"):
        brand = _fetch_one(conn, """
            SELECT id, code, name
            FROM brands
            WHERE code = :code
        """, {"code": filters["brandCode"]})
        if not brand:
            raise ValueError("brandCode không hợp lệ")

    cpu_ref = None
    if filters.get("cpuCode"):
        cpu_ref = _fetch_one(conn, """
            SELECT id, code, display_name, benchmark_score
            FROM cpu_reference
            WHERE code = :code
        """, {"code": filters["cpuCode"]})
        if not cpu_ref:
            raise ValueError("cpuCode không hợp lệ")

    gpu_ref = None
    if filters.get("gpuCode"):
        gpu_ref = _fetch_one(conn, """
            SELECT id, code, display_name, benchmark_score
            FROM gpu_reference
            WHERE code = :code
        """, {"code": filters["gpuCode"]})
        if not gpu_ref:
            raise ValueError("gpuCode không hợp lệ")

    merged_payload = {
        "mode": session_row["mode"],
        "usageProfile": session_row["usage_profile_code"],
        "budget": budget,
        "filters": filters,
        "topN": session_row["top_n"],
    }

    conn.execute(text("""
        UPDATE evaluation_sessions
        SET
            request_payload = CAST(:request_payload AS JSONB),
            budget_min = :budget_min,
            budget_max = :budget_max,
            status = 'created'
        WHERE id = :sid
    """), {
        "sid": session_row["id"],
        "request_payload": json.dumps(merged_payload),
        "budget_min": budget.get("min"),
        "budget_max": budget.get("max"),
    })

    conn.execute(text("""
        DELETE FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """), {"sid": session_row["id"]})

    conn.execute(text("""
        INSERT INTO evaluation_filters (
            evaluation_session_id,
            brand_id,
            requested_cpu_reference_id,
            requested_gpu_reference_id,
            min_price,
            max_price,
            min_ram_gb,
            min_ssd_gb,
            min_cpu_benchmark_score,
            min_gpu_benchmark_score,
            min_screen_size_inch,
            max_screen_size_inch,
            max_weight_kg,
            min_battery_hours,
            require_in_stock
        )
        VALUES (
            :sid,
            :brand_id,
            :cpu_ref_id,
            :gpu_ref_id,
            :min_price,
            :max_price,
            :min_ram_gb,
            :min_ssd_gb,
            :min_cpu_score,
            :min_gpu_score,
            :screen_min,
            :screen_max,
            :max_weight,
            :min_battery,
            TRUE
        )
    """), {
        "sid": session_row["id"],
        "brand_id": brand["id"] if brand else None,
        "cpu_ref_id": cpu_ref["id"] if cpu_ref else None,
        "gpu_ref_id": gpu_ref["id"] if gpu_ref else None,
        "min_price": budget.get("min"),
        "max_price": budget.get("max"),
        "min_ram_gb": filters.get("minRamGb"),
        "min_ssd_gb": filters.get("minSsdGb"),
        "min_cpu_score": cpu_ref["benchmark_score"] if cpu_ref else None,
        "min_gpu_score": gpu_ref["benchmark_score"] if gpu_ref else None,
        "screen_min": filters.get("screenSizeMin"),
        "screen_max": filters.get("screenSizeMax"),
        "max_weight": filters.get("maxWeightKg"),
        "min_battery": filters.get("minBatteryHours"),
    })

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "created",
        "budget": budget,
        "filters": filters,
    }


def get_ahp_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    criteria = _fetch_all(conn, """
        SELECT id, code, name, sort_order
        FROM recommendation_criteria
        WHERE is_active = TRUE
        ORDER BY sort_order
    """)

    weights = _fetch_all(conn, """
        SELECT
            rc.code AS criterion,
            rc.name,
            ew.normalized_weight AS weight,
            ew.explanation_text
        FROM evaluation_weights ew
        JOIN recommendation_criteria rc ON rc.id = ew.criterion_id
        WHERE ew.evaluation_session_id = :sid
        ORDER BY ew.display_order
    """, {"sid": session_row["id"]})

    pairwise = _fetch_all(conn, """
        SELECT
            row_rc.code AS row_criterion,
            col_rc.code AS col_criterion,
            c.cell_value
        FROM evaluation_ahp_matrix_cells c
        JOIN recommendation_criteria row_rc ON row_rc.id = c.row_criterion_id
        JOIN recommendation_criteria col_rc ON col_rc.id = c.col_criterion_id
        WHERE c.evaluation_session_id = :sid
          AND c.matrix_type = 'pairwise'
        ORDER BY row_rc.sort_order, col_rc.sort_order
    """, {"sid": session_row["id"]})

    normalized = _fetch_all(conn, """
        SELECT
            row_rc.code AS row_criterion,
            col_rc.code AS col_criterion,
            c.cell_value
        FROM evaluation_ahp_matrix_cells c
        JOIN recommendation_criteria row_rc ON row_rc.id = c.row_criterion_id
        JOIN recommendation_criteria col_rc ON col_rc.id = c.col_criterion_id
        WHERE c.evaluation_session_id = :sid
          AND c.matrix_type = 'normalized'
        ORDER BY row_rc.sort_order, col_rc.sort_order
    """, {"sid": session_row["id"]})

    summary = _fetch_one(conn, """
        SELECT criteria_count, lambda_max, ci, ri, cr, is_consistent
        FROM evaluation_ahp_summary
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "criteria": [
            {
                "id": x["id"],
                "code": x["code"],
                "name": x["name"],
                "sortOrder": x["sort_order"],
            }
            for x in criteria
        ],
        "weights": [
            {
                "criterion": x["criterion"],
                "name": x["name"],
                "weight": _float_or_none(x["weight"]),
                "explanation": x["explanation_text"],
            }
            for x in weights
        ],
        "pairwiseMatrix": [
            {
                "row": x["row_criterion"],
                "col": x["col_criterion"],
                "value": _float_or_none(x["cell_value"]),
            }
            for x in pairwise
        ],
        "normalizedMatrix": [
            {
                "row": x["row_criterion"],
                "col": x["col_criterion"],
                "value": _float_or_none(x["cell_value"]),
            }
            for x in normalized
        ],
        "consistency": {
            "criteriaCount": summary["criteria_count"] if summary else None,
            "lambdaMax": _float_or_none(summary["lambda_max"]) if summary else None,
            "ci": _float_or_none(summary["ci"]) if summary else None,
            "ri": _float_or_none(summary["ri"]) if summary else None,
            "cr": _float_or_none(summary["cr"]) if summary else None,
            "isConsistent": summary["is_consistent"] if summary else None,
        },
    }


def get_results_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            er.id AS evaluation_result_id,
            er.rank_position,
            er.total_score,
            er.match_percent,
            l.id AS laptop_id,
            l.name AS laptop_name,
            b.name AS brand_name,
            l.price,
            COALESCE(li.image_url, l.image_url) AS image_url
        FROM evaluation_results er
        JOIN laptops l ON l.id = er.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN LATERAL (
            SELECT image_url
            FROM laptop_images
            WHERE laptop_id = l.id AND is_primary = TRUE
            ORDER BY sort_order, id
            LIMIT 1
        ) li ON TRUE
        WHERE er.evaluation_session_id = :sid
        ORDER BY er.rank_position
    """, {"sid": session_row["id"]})

    results = []
    for r in rows:
        details = _fetch_all(conn, """
            SELECT
                rc.code AS criterion,
                rc.name,
                erd.ai_score_100,
                erd.criterion_weight,
                erd.weighted_score
            FROM evaluation_result_details erd
            JOIN recommendation_criteria rc ON rc.id = erd.criterion_id
            WHERE erd.evaluation_result_id = :rid
            ORDER BY rc.sort_order
        """, {"rid": r["evaluation_result_id"]})

        reasons = _fetch_all(conn, """
            SELECT badge_code, badge_label, reason_text, priority_order
            FROM evaluation_result_reasons
            WHERE evaluation_result_id = :rid
            ORDER BY priority_order
        """, {"rid": r["evaluation_result_id"]})

        results.append({
            "rank": r["rank_position"],
            "laptopId": r["laptop_id"],
            "laptopName": r["laptop_name"],
            "brand": r["brand_name"],
            "price": _float_or_none(r["price"]),
            "imageUrl": r["image_url"],
            "totalScore": _float_or_none(r["total_score"]),
            "matchPercent": _float_or_none(r["match_percent"]),
            "details": [
                {
                    "criterion": d["criterion"],
                    "name": d["name"],
                    "aiScore100": _float_or_none(d["ai_score_100"]),
                    "criterionWeight": _float_or_none(d["criterion_weight"]),
                    "weightedScore": _float_or_none(d["weighted_score"]),
                }
                for d in details
            ],
            "reasons": [
                {
                    "badgeCode": x["badge_code"],
                    "badgeLabel": x["badge_label"],
                    "reasonText": x["reason_text"],
                    "priorityOrder": x["priority_order"],
                }
                for x in reasons
            ],
        })

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
            "topN": session_row["top_n"],
        },
        "results": results,
    }


def get_inference_trace_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            rc.code AS criterion,
            rc.name,
            sip.source_type,
            sip.source_key,
            sip.score_delta,
            sip.final_score_after,
            sip.explanation_text,
            sip.created_at
        FROM session_inferred_priorities sip
        JOIN recommendation_criteria rc ON rc.id = sip.criterion_id
        WHERE sip.evaluation_session_id = :sid
        ORDER BY
            CASE sip.source_type
                WHEN 'profile' THEN 1
                WHEN 'filter' THEN 2
                WHEN 'combined' THEN 3
                ELSE 4
            END,
            rc.sort_order,
            sip.created_at
    """, {"sid": session_row["id"]})

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "usageProfile": session_row["usage_profile_code"],
            "usageProfileName": session_row["usage_profile_name"],
            "status": session_row["status"],
        },
        "trace": [
            {
                "criterion": x["criterion"],
                "name": x["name"],
                "sourceType": x["source_type"],
                "sourceKey": x["source_key"],
                "scoreDelta": _float_or_none(x["score_delta"]),
                "finalScoreAfter": _float_or_none(x["final_score_after"]),
                "explanation": x["explanation_text"],
            }
            for x in rows
        ],
    }


def run_hard_filter_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    filt = _fetch_one(conn, """
        SELECT id
        FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    if not filt:
        raise ValueError("Session chưa có filters")

    result = run_hard_filter(conn, session_row["id"])

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "filtered",
        "hardFilterTotalCount": result["total"],
        "hardFilterPassCount": result["passed"],
    }


def get_candidates_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            ec.laptop_id,
            ec.hard_filter_passed,
            ec.failed_rules,
            l.name AS laptop_name,
            b.name AS brand_name,
            l.price,
            l.ram_gb,
            l.ssd_gb,
            l.cpu_benchmark_score,
            l.gpu_benchmark_score,
            l.screen_size_inch,
            l.weight_kg,
            l.battery_hours,
            COALESCE(li.image_url, l.image_url) AS image_url
        FROM evaluation_candidates ec
        JOIN laptops l ON l.id = ec.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN LATERAL (
            SELECT image_url
            FROM laptop_images
            WHERE laptop_id = l.id AND is_primary = TRUE
            ORDER BY sort_order, id
            LIMIT 1
        ) li ON TRUE
        WHERE ec.evaluation_session_id = :sid
        ORDER BY ec.hard_filter_passed DESC, l.price ASC, l.id ASC
    """, {"sid": session_row["id"]})

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "summary": {
            "total": len(rows),
            "passed": sum(1 for r in rows if r["hard_filter_passed"]),
            "failed": sum(1 for r in rows if not r["hard_filter_passed"]),
        },
        "candidates": [
            {
                "laptopId": r["laptop_id"],
                "laptopName": r["laptop_name"],
                "brand": r["brand_name"],
                "price": _float_or_none(r["price"]),
                "ramGb": r["ram_gb"],
                "ssdGb": r["ssd_gb"],
                "cpuBenchmarkScore": _float_or_none(r["cpu_benchmark_score"]),
                "gpuBenchmarkScore": _float_or_none(r["gpu_benchmark_score"]),
                "screenSizeInch": _float_or_none(r["screen_size_inch"]),
                "weightKg": _float_or_none(r["weight_kg"]),
                "batteryHours": _float_or_none(r["battery_hours"]),
                "imageUrl": r["image_url"],
                "hardFilterPassed": r["hard_filter_passed"],
                "failedRules": r["failed_rules"] or [],
            }
            for r in rows
        ],
    }


def infer_priorities_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    filt = _fetch_one(conn, """
        SELECT id
        FROM evaluation_filters
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    if not filt:
        raise ValueError("Session chưa có filters")

    priorities = infer_priorities(conn, session_row["id"])

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "inferred",
        "priorities": priorities,
    }


def calculate_ahp_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    result = calculate_and_store_ahp(conn, session_row["id"])

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "weighted",
        "summary": result["summary"],
        "weights": result["weights"],
    }


def get_weights_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            rc.code AS criterion,
            rc.name,
            ew.source_score,
            ew.raw_weight,
            ew.normalized_weight,
            ew.display_order,
            ew.explanation_text
        FROM evaluation_weights ew
        JOIN recommendation_criteria rc ON rc.id = ew.criterion_id
        WHERE ew.evaluation_session_id = :sid
        ORDER BY ew.display_order, rc.sort_order
    """, {"sid": session_row["id"]})

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "weights": [
            {
                "criterion": r["criterion"],
                "name": r["name"],
                "sourceScore": _float_or_none(r["source_score"]),
                "rawWeight": _float_or_none(r["raw_weight"]),
                "weight": _float_or_none(r["normalized_weight"]),
                "percent": round((_float_or_none(r["normalized_weight"]) or 0) * 100, 2),
                "displayOrder": r["display_order"],
                "explanation": r["explanation_text"],
            }
            for r in rows
        ],
    }


def ai_score_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    weights_exist = _fetch_one(conn, """
        SELECT id
        FROM evaluation_weights
        WHERE evaluation_session_id = :sid
        LIMIT 1
    """, {"sid": session_row["id"]})
    if not weights_exist:
        raise ValueError("Session chưa có trọng số AHP")

    passed_candidate = _fetch_one(conn, """
        SELECT id
        FROM evaluation_candidates
        WHERE evaluation_session_id = :sid
          AND hard_filter_passed = TRUE
        LIMIT 1
    """, {"sid": session_row["id"]})
    if not passed_candidate:
        raise ValueError("Không có candidate pass hard filter")

    ai_score_candidates(conn, session_row["id"])

    scored_count = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM evaluation_ai_scores
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "scored",
        "aiScoreCount": int(scored_count["cnt"] or 0),
    }


def get_ai_scores_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            eas.laptop_id,
            l.name AS laptop_name,
            b.name AS brand_name,
            rc.code AS criterion,
            rc.name AS criterion_name,
            eas.model_id,
            eas.raw_prediction,
            eas.normalized_prediction,
            eas.score_100
        FROM evaluation_ai_scores eas
        JOIN laptops l ON l.id = eas.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        JOIN recommendation_criteria rc ON rc.id = eas.criterion_id
        WHERE eas.evaluation_session_id = :sid
        ORDER BY eas.laptop_id, rc.sort_order
    """, {"sid": session_row["id"]})

    grouped = defaultdict(list)
    laptop_info = {}

    for r in rows:
        laptop_id = r["laptop_id"]
        laptop_info[laptop_id] = {
            "laptopId": laptop_id,
            "laptopName": r["laptop_name"],
            "brand": r["brand_name"],
        }
        grouped[laptop_id].append({
            "criterion": r["criterion"],
            "criterionName": r["criterion_name"],
            "modelId": r["model_id"],
            "rawPrediction": _float_or_none(r["raw_prediction"]),
            "normalizedPrediction": _float_or_none(r["normalized_prediction"]),
            "score100": _float_or_none(r["score_100"]),
        })

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "laptops": [
            {
                **laptop_info[laptop_id],
                "scores": grouped[laptop_id],
            }
            for laptop_id in grouped
        ],
    }


def rank_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    has_weights = _fetch_one(conn, """
        SELECT id
        FROM evaluation_weights
        WHERE evaluation_session_id = :sid
        LIMIT 1
    """, {"sid": session_row["id"]})
    if not has_weights:
        raise ValueError("Session chưa có trọng số AHP")

    has_ai_scores = _fetch_one(conn, """
        SELECT id
        FROM evaluation_ai_scores
        WHERE evaluation_session_id = :sid
        LIMIT 1
    """, {"sid": session_row["id"]})
    if not has_ai_scores:
        raise ValueError("Session chưa có AI scores")

    rank_candidates(conn, session_row["id"])

    ranked_count = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM evaluation_results
        WHERE evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "ranked",
        "resultCount": int(ranked_count["cnt"] or 0),
    }


def get_ranking_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            er.id AS evaluation_result_id,
            er.rank_position,
            er.total_score,
            er.match_percent,
            l.id AS laptop_id,
            l.name AS laptop_name,
            b.name AS brand_name,
            l.price,
            COALESCE(li.image_url, l.image_url) AS image_url
        FROM evaluation_results er
        JOIN laptops l ON l.id = er.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN LATERAL (
            SELECT image_url
            FROM laptop_images
            WHERE laptop_id = l.id AND is_primary = TRUE
            ORDER BY sort_order, id
            LIMIT 1
        ) li ON TRUE
        WHERE er.evaluation_session_id = :sid
        ORDER BY er.rank_position
    """, {"sid": session_row["id"]})

    ranking = []
    for r in rows:
        details = _fetch_all(conn, """
            SELECT
                rc.code AS criterion,
                rc.name AS criterion_name,
                erd.criterion_weight,
                erd.ai_score_100,
                erd.weighted_score
            FROM evaluation_result_details erd
            JOIN recommendation_criteria rc ON rc.id = erd.criterion_id
            WHERE erd.evaluation_result_id = :rid
            ORDER BY rc.sort_order
        """, {"rid": r["evaluation_result_id"]})

        ranking.append({
            "rank": r["rank_position"],
            "laptopId": r["laptop_id"],
            "laptopName": r["laptop_name"],
            "brand": r["brand_name"],
            "price": _float_or_none(r["price"]),
            "imageUrl": r["image_url"],
            "totalScore": _float_or_none(r["total_score"]),
            "matchPercent": _float_or_none(r["match_percent"]),
            "details": [
                {
                    "criterion": d["criterion"],
                    "criterionName": d["criterion_name"],
                    "criterionWeight": _float_or_none(d["criterion_weight"]),
                    "aiScore100": _float_or_none(d["ai_score_100"]),
                    "weightedScore": _float_or_none(d["weighted_score"]),
                }
                for d in details
            ],
        })

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "ranking": ranking,
    }


def generate_reasons_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        raise ValueError("Không tìm thấy session")

    has_results = _fetch_one(conn, """
        SELECT id
        FROM evaluation_results
        WHERE evaluation_session_id = :sid
        LIMIT 1
    """, {"sid": session_row["id"]})
    if not has_results:
        raise ValueError("Session chưa có ranking")

    generate_reasons(conn, session_row["id"])

    reason_count = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM evaluation_result_reasons err
        JOIN evaluation_results er ON er.id = err.evaluation_result_id
        WHERE er.evaluation_session_id = :sid
    """, {"sid": session_row["id"]})

    return {
        "sessionKey": str(session_row["session_key"]),
        "status": "completed",
        "reasonCount": int(reason_count["cnt"] or 0),
    }


def get_reasons_by_session_key(conn, session_key):
    session_row = _get_session_by_key(conn, session_key)
    if not session_row:
        return None

    rows = _fetch_all(conn, """
        SELECT
            er.rank_position,
            l.id AS laptop_id,
            l.name AS laptop_name,
            b.name AS brand_name,
            err.badge_code,
            err.badge_label,
            err.reason_text,
            err.priority_order
        FROM evaluation_results er
        JOIN laptops l ON l.id = er.laptop_id
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN evaluation_result_reasons err ON err.evaluation_result_id = er.id
        WHERE er.evaluation_session_id = :sid
        ORDER BY er.rank_position, err.priority_order NULLS LAST, err.id NULLS LAST
    """, {"sid": session_row["id"]})

    grouped = defaultdict(list)
    laptop_info = {}

    for r in rows:
        rank = r["rank_position"]
        laptop_info[rank] = {
            "rank": rank,
            "laptopId": r["laptop_id"],
            "laptopName": r["laptop_name"],
            "brand": r["brand_name"],
        }

        if r["badge_code"] is not None:
            grouped[rank].append({
                "badgeCode": r["badge_code"],
                "badgeLabel": r["badge_label"],
                "reasonText": r["reason_text"],
                "priorityOrder": r["priority_order"],
            })

    return {
        "session": {
            "sessionKey": str(session_row["session_key"]),
            "status": session_row["status"],
        },
        "reasons": [
            {
                **laptop_info[rank],
                "items": grouped.get(rank, []),
            }
            for rank in sorted(laptop_info.keys())
        ],
    }