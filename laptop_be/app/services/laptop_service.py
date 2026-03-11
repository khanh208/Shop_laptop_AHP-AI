import re
import uuid
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


def _slugify(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or f"brand_{uuid.uuid4().hex[:8]}"


def _ensure_brand(conn, brand_id=None, brand_name=None):
    if brand_id:
        brand = _fetch_one(conn, """
            SELECT id, code, name
            FROM brands
            WHERE id = :id
        """, {"id": brand_id})
        if not brand:
            raise ValueError("brandId không hợp lệ")
        return brand

    if brand_name:
        brand_name = brand_name.strip()
        existing = _fetch_one(conn, """
            SELECT id, code, name
            FROM brands
            WHERE LOWER(name) = LOWER(:name)
        """, {"name": brand_name})
        if existing:
            return existing

        base_code = _slugify(brand_name)
        code = base_code
        counter = 1

        while True:
            used = _fetch_one(conn, """
                SELECT id
                FROM brands
                WHERE code = :code
            """, {"code": code})
            if not used:
                break
            counter += 1
            code = f"{base_code}_{counter}"

        created = _fetch_one(conn, """
            INSERT INTO brands (code, name)
            VALUES (:code, :name)
            RETURNING id, code, name
        """, {
            "code": code,
            "name": brand_name,
        })
        return created

    return None


def _upsert_features(conn, laptop_id, features):
    if not features:
        return

    conn.execute(text("""
        INSERT INTO laptop_ml_features (
            laptop_id,
            norm_cpu,
            norm_ram,
            norm_gpu,
            norm_screen,
            norm_weight,
            norm_battery,
            norm_durability,
            norm_upgradeability
        )
        VALUES (
            :laptop_id,
            :norm_cpu,
            :norm_ram,
            :norm_gpu,
            :norm_screen,
            :norm_weight,
            :norm_battery,
            :norm_durability,
            :norm_upgradeability
        )
        ON CONFLICT (laptop_id)
        DO UPDATE SET
            norm_cpu = EXCLUDED.norm_cpu,
            norm_ram = EXCLUDED.norm_ram,
            norm_gpu = EXCLUDED.norm_gpu,
            norm_screen = EXCLUDED.norm_screen,
            norm_weight = EXCLUDED.norm_weight,
            norm_battery = EXCLUDED.norm_battery,
            norm_durability = EXCLUDED.norm_durability,
            norm_upgradeability = EXCLUDED.norm_upgradeability
    """), {
        "laptop_id": laptop_id,
        "norm_cpu": features.get("normCpu"),
        "norm_ram": features.get("normRam"),
        "norm_gpu": features.get("normGpu"),
        "norm_screen": features.get("normScreen"),
        "norm_weight": features.get("normWeight"),
        "norm_battery": features.get("normBattery"),
        "norm_durability": features.get("normDurability"),
        "norm_upgradeability": features.get("normUpgradeability"),
    })


def list_laptops(conn, page=1, page_size=20, q=None, brand_id=None, is_active=None):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size

    where_parts = []
    params = {
        "limit": page_size,
        "offset": offset,
    }

    if q:
        where_parts.append("(LOWER(l.name) LIKE LOWER(:q) OR LOWER(COALESCE(l.model_code, '')) LIKE LOWER(:q))")
        params["q"] = f"%{q.strip()}%"

    if brand_id:
        where_parts.append("l.brand_id = :brand_id")
        params["brand_id"] = int(brand_id)

    if is_active is not None:
        where_parts.append("l.is_active = :is_active")
        params["is_active"] = bool(is_active)

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    total = _fetch_one(conn, f"""
        SELECT COUNT(*) AS cnt
        FROM laptops l
        {where_sql}
    """, params)

    rows = _fetch_all(conn, f"""
        SELECT
            l.id,
            l.name,
            l.model_code,
            l.cpu_name,
            l.cpu_benchmark_score,
            l.gpu_name,
            l.gpu_benchmark_score,
            l.ram_gb,
            l.ssd_gb,
            l.screen_size_inch,
            l.weight_kg,
            l.battery_hours,
            l.price,
            l.stock_quantity,
            l.is_active,
            b.id AS brand_id,
            b.name AS brand_name,
            COALESCE(li.image_url, l.image_url) AS image_url
        FROM laptops l
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN LATERAL (
            SELECT image_url
            FROM laptop_images
            WHERE laptop_id = l.id AND is_primary = TRUE
            ORDER BY sort_order, id
            LIMIT 1
        ) li ON TRUE
        {where_sql}
        ORDER BY l.id DESC
        LIMIT :limit OFFSET :offset
    """, params)

    return {
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": int(total["cnt"] or 0),
        },
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "modelCode": r["model_code"],
                "brandId": r["brand_id"],
                "brandName": r["brand_name"],
                "cpuName": r["cpu_name"],
                "cpuBenchmarkScore": _float_or_none(r["cpu_benchmark_score"]),
                "gpuName": r["gpu_name"],
                "gpuBenchmarkScore": _float_or_none(r["gpu_benchmark_score"]),
                "ramGb": r["ram_gb"],
                "ssdGb": r["ssd_gb"],
                "screenSizeInch": _float_or_none(r["screen_size_inch"]),
                "weightKg": _float_or_none(r["weight_kg"]),
                "batteryHours": _float_or_none(r["battery_hours"]),
                "price": _float_or_none(r["price"]),
                "stockQuantity": r["stock_quantity"],
                "isActive": r["is_active"],
                "imageUrl": r["image_url"],
            }
            for r in rows
        ],
    }


def get_laptop_detail(conn, laptop_id):
    row = _fetch_one(conn, """
        SELECT
            l.id,
            l.name,
            l.model_code,
            l.cpu_name,
            l.cpu_benchmark_score,
            l.gpu_name,
            l.gpu_benchmark_score,
            l.ram_gb,
            l.ssd_gb,
            l.screen_size_inch,
            l.screen_resolution,
            l.refresh_rate_hz,
            l.weight_kg,
            l.battery_hours,
            l.durability_score,
            l.upgradeability_score,
            l.price,
            l.image_url,
            l.product_url,
            l.description,
            l.stock_quantity,
            l.is_active,
            b.id AS brand_id,
            b.name AS brand_name,
            f.norm_cpu,
            f.norm_ram,
            f.norm_gpu,
            f.norm_screen,
            f.norm_weight,
            f.norm_battery,
            f.norm_durability,
            f.norm_upgradeability
        FROM laptops l
        LEFT JOIN brands b ON b.id = l.brand_id
        LEFT JOIN laptop_ml_features f ON f.laptop_id = l.id
        WHERE l.id = :id
    """, {"id": laptop_id})

    if not row:
        return None

    images = _fetch_all(conn, """
        SELECT id, image_url, is_primary, sort_order
        FROM laptop_images
        WHERE laptop_id = :id
        ORDER BY sort_order, id
    """, {"id": laptop_id})

    return {
        "id": row["id"],
        "name": row["name"],
        "modelCode": row["model_code"],
        "brandId": row["brand_id"],
        "brandName": row["brand_name"],
        "cpuName": row["cpu_name"],
        "cpuBenchmarkScore": _float_or_none(row["cpu_benchmark_score"]),
        "gpuName": row["gpu_name"],
        "gpuBenchmarkScore": _float_or_none(row["gpu_benchmark_score"]),
        "ramGb": row["ram_gb"],
        "ssdGb": row["ssd_gb"],
        "screenSizeInch": _float_or_none(row["screen_size_inch"]),
        "screenResolution": row["screen_resolution"],
        "refreshRateHz": row["refresh_rate_hz"],
        "weightKg": _float_or_none(row["weight_kg"]),
        "batteryHours": _float_or_none(row["battery_hours"]),
        "durabilityScore": _float_or_none(row["durability_score"]),
        "upgradeabilityScore": _float_or_none(row["upgradeability_score"]),
        "price": _float_or_none(row["price"]),
        "imageUrl": row["image_url"],
        "productUrl": row["product_url"],
        "description": row["description"],
        "stockQuantity": row["stock_quantity"],
        "isActive": row["is_active"],
        "features": {
            "normCpu": _float_or_none(row["norm_cpu"]),
            "normRam": _float_or_none(row["norm_ram"]),
            "normGpu": _float_or_none(row["norm_gpu"]),
            "normScreen": _float_or_none(row["norm_screen"]),
            "normWeight": _float_or_none(row["norm_weight"]),
            "normBattery": _float_or_none(row["norm_battery"]),
            "normDurability": _float_or_none(row["norm_durability"]),
            "normUpgradeability": _float_or_none(row["norm_upgradeability"]),
        },
        "images": [
            {
                "id": x["id"],
                "imageUrl": x["image_url"],
                "isPrimary": x["is_primary"],
                "sortOrder": x["sort_order"],
            }
            for x in images
        ],
    }


def create_laptop(conn, payload):
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("Thiếu name")

    brand = _ensure_brand(
        conn,
        brand_id=payload.get("brandId"),
        brand_name=payload.get("brandName"),
    )

    created = _fetch_one(conn, """
        INSERT INTO laptops (
            brand_id,
            name,
            model_code,
            cpu_name,
            cpu_benchmark_score,
            gpu_name,
            gpu_benchmark_score,
            ram_gb,
            ssd_gb,
            screen_size_inch,
            screen_resolution,
            refresh_rate_hz,
            weight_kg,
            battery_hours,
            durability_score,
            upgradeability_score,
            price,
            image_url,
            product_url,
            description,
            stock_quantity,
            is_active
        )
        VALUES (
            :brand_id,
            :name,
            :model_code,
            :cpu_name,
            :cpu_benchmark_score,
            :gpu_name,
            :gpu_benchmark_score,
            :ram_gb,
            :ssd_gb,
            :screen_size_inch,
            :screen_resolution,
            :refresh_rate_hz,
            :weight_kg,
            :battery_hours,
            :durability_score,
            :upgradeability_score,
            :price,
            :image_url,
            :product_url,
            :description,
            :stock_quantity,
            :is_active
        )
        RETURNING id
    """, {
        "brand_id": brand["id"] if brand else None,
        "name": name,
        "model_code": payload.get("modelCode"),
        "cpu_name": payload.get("cpuName"),
        "cpu_benchmark_score": payload.get("cpuBenchmarkScore"),
        "gpu_name": payload.get("gpuName"),
        "gpu_benchmark_score": payload.get("gpuBenchmarkScore"),
        "ram_gb": payload.get("ramGb"),
        "ssd_gb": payload.get("ssdGb"),
        "screen_size_inch": payload.get("screenSizeInch"),
        "screen_resolution": payload.get("screenResolution"),
        "refresh_rate_hz": payload.get("refreshRateHz"),
        "weight_kg": payload.get("weightKg"),
        "battery_hours": payload.get("batteryHours"),
        "durability_score": payload.get("durabilityScore"),
        "upgradeability_score": payload.get("upgradeabilityScore"),
        "price": payload.get("price"),
        "image_url": payload.get("imageUrl"),
        "product_url": payload.get("productUrl"),
        "description": payload.get("description"),
        "stock_quantity": payload.get("stockQuantity", 0),
        "is_active": payload.get("isActive", True),
    })

    _upsert_features(conn, created["id"], payload.get("features"))

    return get_laptop_detail(conn, created["id"])


def update_laptop(conn, laptop_id, payload):
    existing = _fetch_one(conn, """
        SELECT id, brand_id
        FROM laptops
        WHERE id = :id
    """, {"id": laptop_id})
    if not existing:
        raise ValueError("Không tìm thấy laptop")

    brand_id = existing["brand_id"]
    if "brandId" in payload or "brandName" in payload:
        brand = _ensure_brand(
            conn,
            brand_id=payload.get("brandId"),
            brand_name=payload.get("brandName"),
        )
        brand_id = brand["id"] if brand else None

    update_data = {
        "id": laptop_id,
        "brand_id": brand_id,
        "name": payload.get("name"),
        "model_code": payload.get("modelCode"),
        "cpu_name": payload.get("cpuName"),
        "cpu_benchmark_score": payload.get("cpuBenchmarkScore"),
        "gpu_name": payload.get("gpuName"),
        "gpu_benchmark_score": payload.get("gpuBenchmarkScore"),
        "ram_gb": payload.get("ramGb"),
        "ssd_gb": payload.get("ssdGb"),
        "screen_size_inch": payload.get("screenSizeInch"),
        "screen_resolution": payload.get("screenResolution"),
        "refresh_rate_hz": payload.get("refreshRateHz"),
        "weight_kg": payload.get("weightKg"),
        "battery_hours": payload.get("batteryHours"),
        "durability_score": payload.get("durabilityScore"),
        "upgradeability_score": payload.get("upgradeabilityScore"),
        "price": payload.get("price"),
        "image_url": payload.get("imageUrl"),
        "product_url": payload.get("productUrl"),
        "description": payload.get("description"),
        "stock_quantity": payload.get("stockQuantity"),
        "is_active": payload.get("isActive"),
    }

    conn.execute(text("""
        UPDATE laptops
        SET
            brand_id = COALESCE(:brand_id, brand_id),
            name = COALESCE(:name, name),
            model_code = COALESCE(:model_code, model_code),
            cpu_name = COALESCE(:cpu_name, cpu_name),
            cpu_benchmark_score = COALESCE(:cpu_benchmark_score, cpu_benchmark_score),
            gpu_name = COALESCE(:gpu_name, gpu_name),
            gpu_benchmark_score = COALESCE(:gpu_benchmark_score, gpu_benchmark_score),
            ram_gb = COALESCE(:ram_gb, ram_gb),
            ssd_gb = COALESCE(:ssd_gb, ssd_gb),
            screen_size_inch = COALESCE(:screen_size_inch, screen_size_inch),
            screen_resolution = COALESCE(:screen_resolution, screen_resolution),
            refresh_rate_hz = COALESCE(:refresh_rate_hz, refresh_rate_hz),
            weight_kg = COALESCE(:weight_kg, weight_kg),
            battery_hours = COALESCE(:battery_hours, battery_hours),
            durability_score = COALESCE(:durability_score, durability_score),
            upgradeability_score = COALESCE(:upgradeability_score, upgradeability_score),
            price = COALESCE(:price, price),
            image_url = COALESCE(:image_url, image_url),
            product_url = COALESCE(:product_url, product_url),
            description = COALESCE(:description, description),
            stock_quantity = COALESCE(:stock_quantity, stock_quantity),
            is_active = COALESCE(:is_active, is_active),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """), update_data)

    if "features" in payload:
        _upsert_features(conn, laptop_id, payload.get("features") or {})

    return get_laptop_detail(conn, laptop_id)


def delete_laptop(conn, laptop_id):
    existing = _fetch_one(conn, """
        SELECT id
        FROM laptops
        WHERE id = :id
    """, {"id": laptop_id})
    if not existing:
        raise ValueError("Không tìm thấy laptop")

    conn.execute(text("""
        UPDATE laptops
        SET
            is_active = FALSE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """), {"id": laptop_id})

    return {
        "message": "Đã xóa mềm laptop",
        "id": laptop_id,
        "isActive": False,
    }

def _ensure_brand_code_unique(conn, code, exclude_id=None):
    params = {"code": code}
    sql = """
        SELECT id
        FROM brands
        WHERE code = :code
    """
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id

    existing = _fetch_one(conn, sql, params)
    if existing:
        raise ValueError("code của brand đã tồn tại")


def list_brands(conn):
    rows = _fetch_all(conn, """
        SELECT
            b.id,
            b.code,
            b.name,
            b.logo_url,
            COUNT(l.id) AS laptop_count
        FROM brands b
        LEFT JOIN laptops l ON l.brand_id = b.id
        GROUP BY b.id, b.code, b.name, b.logo_url
        ORDER BY b.name
    """)

    return {
        "items": [
            {
                "id": r["id"],
                "code": r["code"],
                "name": r["name"],
                "logoUrl": r["logo_url"],
                "laptopCount": int(r["laptop_count"] or 0),
            }
            for r in rows
        ]
    }


def create_brand(conn, payload):
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("Thiếu name")

    code = (payload.get("code") or "").strip()
    if not code:
        code = _slugify(name)

    existing_name = _fetch_one(conn, """
        SELECT id
        FROM brands
        WHERE LOWER(name) = LOWER(:name)
    """, {"name": name})
    if existing_name:
        raise ValueError("name của brand đã tồn tại")

    _ensure_brand_code_unique(conn, code)

    row = _fetch_one(conn, """
        INSERT INTO brands (code, name, logo_url)
        VALUES (:code, :name, :logo_url)
        RETURNING id, code, name, logo_url
    """, {
        "code": code,
        "name": name,
        "logo_url": payload.get("logoUrl"),
    })

    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "logoUrl": row["logo_url"],
    }


def update_brand(conn, brand_id, payload):
    existing = _fetch_one(conn, """
        SELECT id, code, name, logo_url
        FROM brands
        WHERE id = :id
    """, {"id": brand_id})
    if not existing:
        raise ValueError("Không tìm thấy brand")

    new_name = payload.get("name", existing["name"])
    new_code = payload.get("code", existing["code"])
    new_logo_url = payload.get("logoUrl", existing["logo_url"])

    if new_name is not None:
        new_name = str(new_name).strip()
    if not new_name:
        raise ValueError("Thiếu name")

    if new_code is not None:
        new_code = str(new_code).strip()
    if not new_code:
        new_code = _slugify(new_name)

    duplicate_name = _fetch_one(conn, """
        SELECT id
        FROM brands
        WHERE LOWER(name) = LOWER(:name)
          AND id <> :id
    """, {
        "name": new_name,
        "id": brand_id,
    })
    if duplicate_name:
        raise ValueError("name của brand đã tồn tại")

    _ensure_brand_code_unique(conn, new_code, exclude_id=brand_id)

    row = _fetch_one(conn, """
        UPDATE brands
        SET
            code = :code,
            name = :name,
            logo_url = :logo_url
        WHERE id = :id
        RETURNING id, code, name, logo_url
    """, {
        "id": brand_id,
        "code": new_code,
        "name": new_name,
        "logo_url": new_logo_url,
    })

    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "logoUrl": row["logo_url"],
    }


def delete_brand(conn, brand_id):
    existing = _fetch_one(conn, """
        SELECT id, code, name
        FROM brands
        WHERE id = :id
    """, {"id": brand_id})
    if not existing:
        raise ValueError("Không tìm thấy brand")

    used = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM laptops
        WHERE brand_id = :id
    """, {"id": brand_id})

    if int(used["cnt"] or 0) > 0:
        raise ValueError("Brand đang được dùng bởi laptop, không thể xóa")

    conn.execute(text("""
        DELETE FROM brands
        WHERE id = :id
    """), {"id": brand_id})

    return {
        "message": "Đã xóa brand",
        "id": brand_id,
        "code": existing["code"],
        "name": existing["name"],
    }


def create_laptop_image(conn, laptop_id, payload):
    laptop = _fetch_one(conn, """
        SELECT id
        FROM laptops
        WHERE id = :id
    """, {"id": laptop_id})
    if not laptop:
        raise ValueError("Không tìm thấy laptop")

    image_url = (payload.get("imageUrl") or "").strip()
    if not image_url:
        raise ValueError("Thiếu imageUrl")

    alt_text = payload.get("altText")
    is_primary = bool(payload.get("isPrimary", False))
    sort_order = int(payload.get("sortOrder", 1) or 1)

    if is_primary:
        conn.execute(text("""
            UPDATE laptop_images
            SET is_primary = FALSE
            WHERE laptop_id = :laptop_id
        """), {"laptop_id": laptop_id})

    row = _fetch_one(conn, """
        INSERT INTO laptop_images (
            laptop_id,
            image_url,
            alt_text,
            is_primary,
            sort_order
        )
        VALUES (
            :laptop_id,
            :image_url,
            :alt_text,
            :is_primary,
            :sort_order
        )
        RETURNING id, laptop_id, image_url, alt_text, is_primary, sort_order
    """, {
        "laptop_id": laptop_id,
        "image_url": image_url,
        "alt_text": alt_text,
        "is_primary": is_primary,
        "sort_order": sort_order,
    })

    return {
        "id": row["id"],
        "laptopId": row["laptop_id"],
        "imageUrl": row["image_url"],
        "altText": row["alt_text"],
        "isPrimary": row["is_primary"],
        "sortOrder": row["sort_order"],
    }


def delete_laptop_image(conn, image_id):
    existing = _fetch_one(conn, """
        SELECT id, laptop_id, image_url, is_primary
        FROM laptop_images
        WHERE id = :id
    """, {"id": image_id})
    if not existing:
        raise ValueError("Không tìm thấy ảnh")

    conn.execute(text("""
        DELETE FROM laptop_images
        WHERE id = :id
    """), {"id": image_id})

    return {
        "message": "Đã xóa ảnh laptop",
        "id": image_id,
        "laptopId": existing["laptop_id"],
        "imageUrl": existing["image_url"],
    }