import json
from decimal import Decimal
from sqlalchemy import text


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


def list_ml_models(conn):
    rows = _fetch_all(conn, """
        SELECT
            m.id,
            m.code,
            m.criterion_id,
            rc.code AS criterion_code,
            rc.name AS criterion_name,
            m.model_type,
            m.algorithm_name,
            m.version,
            m.artifact_path,
            m.metadata,
            m.is_active,
            m.created_at
        FROM ml_models m
        LEFT JOIN recommendation_criteria rc ON rc.id = m.criterion_id
        ORDER BY m.created_at DESC, m.id DESC
    """)

    return {
        "items": [
            {
                "id": r["id"],
                "code": r["code"],
                "criterionId": r["criterion_id"],
                "criterionCode": r["criterion_code"],
                "criterionName": r["criterion_name"],
                "modelType": r["model_type"],
                "algorithmName": r["algorithm_name"],
                "version": r["version"],
                "artifactPath": r["artifact_path"],
                "metadata": r["metadata"],
                "isActive": r["is_active"],
                "createdAt": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in rows
        ]
    }


def _resolve_criterion_id(conn, criterion_id=None, criterion_code=None):
    if criterion_id:
        row = _fetch_one(conn, """
            SELECT id, code, name
            FROM recommendation_criteria
            WHERE id = :id
        """, {"id": criterion_id})
        if not row:
            raise ValueError("criterionId không hợp lệ")
        return row["id"]

    if criterion_code:
        row = _fetch_one(conn, """
            SELECT id, code, name
            FROM recommendation_criteria
            WHERE code = :code
        """, {"code": criterion_code})
        if not row:
            raise ValueError("criterionCode không hợp lệ")
        return row["id"]

    return None


def create_ml_model(conn, payload):
    code = (payload.get("code") or "").strip()
    if not code:
        raise ValueError("Thiếu code")

    model_type = (payload.get("modelType") or "").strip()
    if not model_type:
        raise ValueError("Thiếu modelType")

    algorithm_name = (payload.get("algorithmName") or "").strip()
    if not algorithm_name:
        raise ValueError("Thiếu algorithmName")

    version = (payload.get("version") or "").strip()
    if not version:
        raise ValueError("Thiếu version")

    existing = _fetch_one(conn, """
        SELECT id
        FROM ml_models
        WHERE code = :code
    """, {"code": code})
    if existing:
        raise ValueError("code model đã tồn tại")

    criterion_id = _resolve_criterion_id(
        conn,
        criterion_id=payload.get("criterionId"),
        criterion_code=payload.get("criterionCode"),
    )

    metadata = payload.get("metadata")
    if metadata is None:
        metadata_json = json.dumps({})
    else:
        metadata_json = json.dumps(metadata, ensure_ascii=False)

    is_active = bool(payload.get("isActive", True))

    # nếu tạo model active thì tắt các model active khác cùng criterion
    if is_active:
        if criterion_id is None:
            conn.execute(text("""
                UPDATE ml_models
                SET is_active = FALSE
                WHERE criterion_id IS NULL
            """))
        else:
            conn.execute(text("""
                UPDATE ml_models
                SET is_active = FALSE
                WHERE criterion_id = :criterion_id
            """), {"criterion_id": criterion_id})

    row = _fetch_one(conn, """
        INSERT INTO ml_models (
            code,
            criterion_id,
            model_type,
            algorithm_name,
            version,
            artifact_path,
            metadata,
            is_active
        )
        VALUES (
            :code,
            :criterion_id,
            :model_type,
            :algorithm_name,
            :version,
            :artifact_path,
            CAST(:metadata AS JSONB),
            :is_active
        )
        RETURNING id
    """, {
        "code": code,
        "criterion_id": criterion_id,
        "model_type": model_type,
        "algorithm_name": algorithm_name,
        "version": version,
        "artifact_path": payload.get("artifactPath"),
        "metadata": metadata_json,
        "is_active": is_active,
    })

    created = _fetch_one(conn, """
        SELECT
            m.id,
            m.code,
            m.criterion_id,
            rc.code AS criterion_code,
            rc.name AS criterion_name,
            m.model_type,
            m.algorithm_name,
            m.version,
            m.artifact_path,
            m.metadata,
            m.is_active,
            m.created_at
        FROM ml_models m
        LEFT JOIN recommendation_criteria rc ON rc.id = m.criterion_id
        WHERE m.id = :id
    """, {"id": row["id"]})

    return {
        "id": created["id"],
        "code": created["code"],
        "criterionId": created["criterion_id"],
        "criterionCode": created["criterion_code"],
        "criterionName": created["criterion_name"],
        "modelType": created["model_type"],
        "algorithmName": created["algorithm_name"],
        "version": created["version"],
        "artifactPath": created["artifact_path"],
        "metadata": created["metadata"],
        "isActive": created["is_active"],
        "createdAt": str(created["created_at"]) if created["created_at"] else None,
    }


def activate_ml_model(conn, model_id):
    row = _fetch_one(conn, """
        SELECT id, criterion_id, code
        FROM ml_models
        WHERE id = :id
    """, {"id": model_id})
    if not row:
        raise ValueError("Không tìm thấy model")

    criterion_id = row["criterion_id"]

    if criterion_id is None:
        conn.execute(text("""
            UPDATE ml_models
            SET is_active = FALSE
            WHERE criterion_id IS NULL
        """))
    else:
        conn.execute(text("""
            UPDATE ml_models
            SET is_active = FALSE
            WHERE criterion_id = :criterion_id
        """), {"criterion_id": criterion_id})

    conn.execute(text("""
        UPDATE ml_models
        SET is_active = TRUE
        WHERE id = :id
    """), {"id": model_id})

    activated = _fetch_one(conn, """
        SELECT
            m.id,
            m.code,
            m.criterion_id,
            rc.code AS criterion_code,
            rc.name AS criterion_name,
            m.model_type,
            m.algorithm_name,
            m.version,
            m.artifact_path,
            m.metadata,
            m.is_active,
            m.created_at
        FROM ml_models m
        LEFT JOIN recommendation_criteria rc ON rc.id = m.criterion_id
        WHERE m.id = :id
    """, {"id": model_id})

    return {
        "message": "Đã kích hoạt model",
        "id": activated["id"],
        "code": activated["code"],
        "criterionId": activated["criterion_id"],
        "criterionCode": activated["criterion_code"],
        "criterionName": activated["criterion_name"],
        "isActive": activated["is_active"],
    }


def export_training_data(conn, limit=200, label_name=None):
    limit = max(1, min(5000, int(limit or 200)))

    params = {"limit": limit}
    label_where = ""
    if label_name:
        label_where = "WHERE ltl.label_name = :label_name"
        params["label_name"] = label_name

    rows = _fetch_all(conn, f"""
        SELECT
            v.laptop_id,
            v.laptop_name,
            v."Norm_CPU",
            v."Norm_RAM",
            v."Norm_GPU",
            v."Norm_Screen",
            v."Norm_Weight",
            v."Norm_Battery",
            v."Norm_Durability",
            v."Norm_Upgrade",
            v."Price (VND)",
            ltl.label_name,
            ltl.label_value,
            ltl.source_file_name
        FROM v_ml_export_laptop_data v
        LEFT JOIN laptop_training_labels ltl ON ltl.laptop_id = v.laptop_id
        {label_where}
        ORDER BY v.laptop_id, ltl.label_name
        LIMIT :limit
    """, params)

    grouped = {}
    for r in rows:
        laptop_id = r["laptop_id"]
        if laptop_id not in grouped:
            grouped[laptop_id] = {
                "laptopId": laptop_id,
                "laptopName": r["laptop_name"],
                "features": {
                    "Norm_CPU": _float_or_none(r["Norm_CPU"]),
                    "Norm_RAM": _float_or_none(r["Norm_RAM"]),
                    "Norm_GPU": _float_or_none(r["Norm_GPU"]),
                    "Norm_Screen": _float_or_none(r["Norm_Screen"]),
                    "Norm_Weight": _float_or_none(r["Norm_Weight"]),
                    "Norm_Battery": _float_or_none(r["Norm_Battery"]),
                    "Norm_Durability": _float_or_none(r["Norm_Durability"]),
                    "Norm_Upgrade": _float_or_none(r["Norm_Upgrade"]),
                    "Price (VND)": _float_or_none(r["Price (VND)"]),
                },
                "labels": [],
            }

        if r["label_name"] is not None:
            grouped[laptop_id]["labels"].append({
                "labelName": r["label_name"],
                "labelValue": _float_or_none(r["label_value"]),
                "sourceFileName": r["source_file_name"],
            })

    total_rows = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM v_ml_export_laptop_data
    """)

    return {
        "summary": {
            "totalRecommendationReadyLaptops": int(total_rows["cnt"] or 0),
            "returnedItems": len(grouped),
            "limit": limit,
            "labelFilter": label_name,
        },
        "items": list(grouped.values()),
    }