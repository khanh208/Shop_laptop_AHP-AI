from decimal import Decimal

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash


TOKEN_SALT = "laptop-be-auth"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 ngày


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


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _build_user_payload(row):
    return {
        "id": row["id"],
        "fullName": row["full_name"],
        "email": row["email"],
        "phoneNumber": row["phone_number"],
        "role": row["role"],
        "createdAt": str(row["created_at"]) if row["created_at"] else None,
    }


def _issue_token(user_row):
    s = _serializer()
    token = s.dumps(
        {
            "user_id": user_row["id"],
            "email": user_row["email"],
            "role": user_row["role"],
        },
        salt=TOKEN_SALT,
    )
    return token


def _parse_bearer_token(auth_header):
    if not auth_header:
        return None
    auth_header = str(auth_header).strip()
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def verify_token(token):
    s = _serializer()
    try:
        payload = s.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS)
        return payload
    except SignatureExpired:
        raise ValueError("Token đã hết hạn")
    except BadSignature:
        raise ValueError("Token không hợp lệ")


def get_optional_current_user(conn, auth_header):
    token = _parse_bearer_token(auth_header)
    if not token:
        return None

    payload = verify_token(token)

    user_row = _fetch_one(conn, """
        SELECT id, full_name, email, phone_number, role, created_at
        FROM users
        WHERE id = :id
    """, {"id": payload["user_id"]})

    if not user_row:
        raise ValueError("Người dùng không tồn tại")

    return _build_user_payload(user_row)


def require_current_user(conn, auth_header):
    user = get_optional_current_user(conn, auth_header)
    if not user:
        raise ValueError("Thiếu Bearer token")
    return user


def register_user(conn, payload):
    full_name = (payload.get("fullName") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    phone_number = (payload.get("phoneNumber") or "").strip() or None

    if not full_name:
        raise ValueError("Thiếu fullName")
    if not email:
        raise ValueError("Thiếu email")
    if not password:
        raise ValueError("Thiếu password")
    if len(password) < 6:
        raise ValueError("password phải có ít nhất 6 ký tự")

    existing = _fetch_one(conn, """
        SELECT id
        FROM users
        WHERE LOWER(email) = LOWER(:email)
    """, {"email": email})
    if existing:
        raise ValueError("Email đã tồn tại")

    row = _fetch_one(conn, """
        INSERT INTO users (
            full_name,
            email,
            password_hash,
            phone_number,
            role
        )
        VALUES (
            :full_name,
            :email,
            :password_hash,
            :phone_number,
            'user'
        )
        RETURNING id, full_name, email, phone_number, role, created_at
    """, {
        "full_name": full_name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "phone_number": phone_number,
    })

    token = _issue_token(row)

    return {
        "message": "Đăng ký thành công",
        "accessToken": token,
        "tokenType": "Bearer",
        "user": _build_user_payload(row),
    }


def login_user(conn, payload):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email:
        raise ValueError("Thiếu email")
    if not password:
        raise ValueError("Thiếu password")

    row = _fetch_one(conn, """
        SELECT id, full_name, email, phone_number, role, password_hash, created_at
        FROM users
        WHERE LOWER(email) = LOWER(:email)
    """, {"email": email})

    if not row or not check_password_hash(row["password_hash"], password):
        raise ValueError("Email hoặc mật khẩu không đúng")

    token = _issue_token(row)

    return {
        "message": "Đăng nhập thành công",
        "accessToken": token,
        "tokenType": "Bearer",
        "user": {
            "id": row["id"],
            "fullName": row["full_name"],
            "email": row["email"],
            "phoneNumber": row["phone_number"],
            "role": row["role"],
            "createdAt": str(row["created_at"]) if row["created_at"] else None,
        },
    }


def get_my_recommendations(conn, user_id, page=1, page_size=20):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size

    total = _fetch_one(conn, """
        SELECT COUNT(*) AS cnt
        FROM evaluation_sessions
        WHERE user_id = :user_id
    """, {"user_id": user_id})

    rows = _fetch_all(conn, """
        SELECT
            es.id,
            es.session_key,
            es.mode,
            es.status,
            es.top_n,
            es.budget_min,
            es.budget_max,
            es.hard_filter_total_count,
            es.hard_filter_pass_count,
            es.created_at,
            up.code AS usage_profile_code,
            up.name AS usage_profile_name,
            COUNT(er.id) AS result_count,
            MAX(CASE WHEN er.rank_position = 1 THEN l.name END) AS top_laptop_name,
            MAX(CASE WHEN er.rank_position = 1 THEN er.match_percent END) AS top_match_percent
        FROM evaluation_sessions es
        JOIN usage_profiles up ON up.id = es.usage_profile_id
        LEFT JOIN evaluation_results er ON er.evaluation_session_id = es.id
        LEFT JOIN laptops l ON l.id = er.laptop_id
        WHERE es.user_id = :user_id
        GROUP BY
            es.id, es.session_key, es.mode, es.status, es.top_n,
            es.budget_min, es.budget_max,
            es.hard_filter_total_count, es.hard_filter_pass_count,
            es.created_at,
            up.code, up.name
        ORDER BY es.created_at DESC, es.id DESC
        LIMIT :limit OFFSET :offset
    """, {
        "user_id": user_id,
        "limit": page_size,
        "offset": offset,
    })

    return {
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": int(total["cnt"] or 0),
        },
        "items": [
            {
                "sessionId": r["id"],
                "sessionKey": str(r["session_key"]),
                "mode": r["mode"],
                "status": r["status"],
                "topN": r["top_n"],
                "usageProfile": r["usage_profile_code"],
                "usageProfileName": r["usage_profile_name"],
                "budgetMin": _float_or_none(r["budget_min"]),
                "budgetMax": _float_or_none(r["budget_max"]),
                "hardFilterTotalCount": r["hard_filter_total_count"],
                "hardFilterPassCount": r["hard_filter_pass_count"],
                "resultCount": int(r["result_count"] or 0),
                "topLaptopName": r["top_laptop_name"],
                "topMatchPercent": _float_or_none(r["top_match_percent"]),
                "createdAt": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in rows
        ],
    }

def require_admin(conn, auth_header):
    user = require_current_user(conn, auth_header)

    if str(user.get("role") or "").lower() != "admin":
        raise PermissionError("Bạn không có quyền admin")

    return user