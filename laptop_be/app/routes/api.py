import os
import tempfile
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.services.recommendation_service import (
    get_form_options,
    run_full_pipeline,
    get_dashboard,
    get_ahp_by_session_key,
    get_results_by_session_key,
    get_inference_trace_by_session_key,
    create_session_only,
    save_filters_to_session,
    run_hard_filter_by_session_key,
    get_candidates_by_session_key,
    infer_priorities_by_session_key,
    calculate_ahp_by_session_key,
    get_weights_by_session_key,
    ai_score_by_session_key,
    get_ai_scores_by_session_key,
    rank_by_session_key,
    get_ranking_by_session_key,
    generate_reasons_by_session_key,
    get_reasons_by_session_key,
)
from app.services.import_service import (
    stage_laptop_file,
    preview_staging,
    commit_staging,
    clear_staging,
)
from app.services.ml_model_service import (
    list_ml_models,
    create_ml_model,
    activate_ml_model,
    export_training_data,
)
from app.services.auth_service import (
    register_user,
    login_user,
    get_optional_current_user,
    require_current_user,
    require_admin,
    get_my_recommendations,
)
from app.services.laptop_service import (
    list_laptops,
    get_laptop_detail,
    create_laptop,
    update_laptop,
    delete_laptop,
    list_brands,
    create_brand,
    update_brand,
    delete_brand,
    create_laptop_image,
    delete_laptop_image,
)
api_bp = Blueprint("api", __name__)

@api_bp.get("/form-options")
def form_options():
    with db.engine.begin() as conn:
        data = get_form_options(conn)
        return jsonify(data), 200

@api_bp.post("/recommendations/run")
def run_recommendation():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            current_user = get_optional_current_user(conn, request.headers.get("Authorization"))
            result = run_full_pipeline(
                conn,
                payload,
                user_id=current_user["id"] if current_user else None,
            )
            return jsonify(result), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.get("/recommendations/<session_key>/dashboard")
def recommendation_dashboard(session_key):
    with db.engine.begin() as conn:
        data = get_dashboard(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200
    

@api_bp.get("/recommendations/<session_key>/ahp")
def recommendation_ahp(session_key):
    with db.engine.begin() as conn:
        data = get_ahp_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.get("/recommendations/<session_key>/results")
def recommendation_results(session_key):
    with db.engine.begin() as conn:
        data = get_results_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.get("/recommendations/<session_key>/inference-trace")
def recommendation_inference_trace(session_key):
    with db.engine.begin() as conn:
        data = get_inference_trace_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.post("/recommendations/sessions")
def recommendation_create_session():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            current_user = get_optional_current_user(conn, request.headers.get("Authorization"))
            data = create_session_only(
                conn,
                payload,
                user_id=current_user["id"] if current_user else None,
            )
            return jsonify(data), 201
    except KeyError:
        return jsonify({"message": "Thiếu trường usageProfile"}), 400
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.post("/recommendations/<session_key>/filters")
def recommendation_save_filters(session_key):
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            data = save_filters_to_session(conn, session_key, payload)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
    
@api_bp.post("/recommendations/<session_key>/hard-filter")
def recommendation_hard_filter(session_key):
    try:
        with db.engine.begin() as conn:
            data = run_hard_filter_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/recommendations/<session_key>/candidates")
def recommendation_candidates(session_key):
    with db.engine.begin() as conn:
        data = get_candidates_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.post("/recommendations/<session_key>/infer-priorities")
def recommendation_infer_priorities(session_key):
    try:
        with db.engine.begin() as conn:
            data = infer_priorities_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.post("/recommendations/<session_key>/ahp")
def recommendation_calculate_ahp(session_key):
    try:
        with db.engine.begin() as conn:
            data = calculate_ahp_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/recommendations/<session_key>/weights")
def recommendation_weights(session_key):
    with db.engine.begin() as conn:
        data = get_weights_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200
    
@api_bp.post("/recommendations/<session_key>/ai-score")
def recommendation_ai_score(session_key):
    try:
        with db.engine.begin() as conn:
            data = ai_score_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/recommendations/<session_key>/ai-scores")
def recommendation_ai_scores(session_key):
    with db.engine.begin() as conn:
        data = get_ai_scores_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.post("/recommendations/<session_key>/rank")
def recommendation_rank(session_key):
    try:
        with db.engine.begin() as conn:
            data = rank_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/recommendations/<session_key>/ranking")
def recommendation_ranking(session_key):
    with db.engine.begin() as conn:
        data = get_ranking_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.post("/recommendations/<session_key>/reasons")
def recommendation_reasons_generate(session_key):
    try:
        with db.engine.begin() as conn:
            data = generate_reasons_by_session_key(conn, session_key)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
    
@api_bp.post("/admin/imports/laptop-data")
def admin_import_laptop_data():
    if "file" not in request.files:
        return jsonify({"message": "Thiếu file upload"}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"message": "File không hợp lệ"}), 400

    sheet_name = request.form.get("sheetName", "Laptop_Data")
    replace_staging = str(request.form.get("replaceStaging", "false")).lower() in ("true", "1", "yes", "on")
    auto_commit = str(request.form.get("autoCommit", "false")).lower() in ("true", "1", "yes", "on")

    safe_name = secure_filename(uploaded_file.filename)
    suffix = Path(safe_name).suffix or ".tmp"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            uploaded_file.save(tmp.name)
            temp_path = tmp.name

        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))

            staged = stage_laptop_file(
                conn=conn,
                file_path=temp_path,
                original_filename=safe_name,
                sheet_name=sheet_name,
                replace_staging=replace_staging,
            )

            response = {
                **staged,
                "autoCommitted": False,
            }

            if auto_commit:
                committed = commit_staging(conn)
                response["autoCommitted"] = True
                response["commitResult"] = committed

            return jsonify(response), 201

    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@api_bp.get("/admin/imports/laptop-data/preview")
def admin_preview_laptop_data():
    batch_id = request.args.get("batchId")
    limit = request.args.get("limit", 50)

    try:
        limit = int(limit)
    except Exception:
        limit = 50

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = preview_staging(conn, batch_id=batch_id, limit=limit)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.post("/admin/imports/laptop-data/commit")
def admin_commit_laptop_data():
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = commit_staging(conn)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.delete("/admin/imports/laptop-data/staging")
def admin_clear_laptop_staging():
    batch_id = request.args.get("batchId")

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = clear_staging(conn, batch_id=batch_id)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
        
@api_bp.get("/recommendations/<session_key>/reasons")
def recommendation_reasons(session_key):
    with db.engine.begin() as conn:
        data = get_reasons_by_session_key(conn, session_key)
        if not data:
            return jsonify({"message": "Không tìm thấy session"}), 404
        return jsonify(data), 200


@api_bp.get("/laptops")
def laptops_list():
    page = request.args.get("page", 1)
    page_size = request.args.get("pageSize", 20)
    q = request.args.get("q")
    brand_id = request.args.get("brandId")
    is_active_raw = request.args.get("isActive")

    is_active = None
    if is_active_raw is not None:
        is_active = str(is_active_raw).lower() in ("true", "1", "yes", "on")

    with db.engine.begin() as conn:
        data = list_laptops(
            conn,
            page=page,
            page_size=page_size,
            q=q,
            brand_id=brand_id,
            is_active=is_active,
        )
        return jsonify(data), 200


@api_bp.get("/laptops/<int:laptop_id>")
def laptop_detail(laptop_id):
    with db.engine.begin() as conn:
        data = get_laptop_detail(conn, laptop_id)
        if not data:
            return jsonify({"message": "Không tìm thấy laptop"}), 404
        return jsonify(data), 200


@api_bp.post("/admin/laptops")
def admin_create_laptop():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = create_laptop(conn, payload)
            return jsonify(data), 201
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.put("/admin/laptops/<int:laptop_id>")
def admin_update_laptop(laptop_id):
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = update_laptop(conn, laptop_id, payload)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
    
@api_bp.delete("/admin/laptops/<int:laptop_id>")
def admin_delete_laptop(laptop_id):
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = delete_laptop(conn, laptop_id)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500    
    
@api_bp.post("/admin/laptops/<int:laptop_id>/images")
def admin_create_laptop_image(laptop_id):
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = create_laptop_image(conn, laptop_id, payload)
            return jsonify(data), 201
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.delete("/admin/laptop-images/<int:image_id>")
def admin_delete_laptop_image(image_id):
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = delete_laptop_image(conn, image_id)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500

@api_bp.get("/brands")
def brands_list():
    with db.engine.begin() as conn:
        data = list_brands(conn)
        return jsonify(data), 200


@api_bp.post("/admin/brands")
def admin_create_brand():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = create_brand(conn, payload)
            return jsonify(data), 201
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500
    
@api_bp.put("/admin/brands/<int:brand_id>")
def admin_update_brand(brand_id):
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = update_brand(conn, brand_id, payload)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.delete("/admin/brands/<int:brand_id>")
def admin_delete_brand(brand_id):
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = delete_brand(conn, brand_id)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        if "Không tìm thấy brand" in str(e):
            return jsonify({"message": str(e)}), 404
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500    
    
@api_bp.get("/admin/ml-models")
def admin_ml_models():
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = list_ml_models(conn)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403


@api_bp.post("/admin/ml-models")
def admin_create_ml_model():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = create_ml_model(conn, payload)
            return jsonify(data), 201
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.put("/admin/ml-models/<int:model_id>/activate")
def admin_activate_ml_model(model_id):
    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = activate_ml_model(conn, model_id)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/admin/training-data/export")
def admin_export_training_data():
    limit = request.args.get("limit", 200)
    label_name = request.args.get("labelName")

    try:
        limit = int(limit)
    except Exception:
        limit = 200

    try:
        with db.engine.begin() as conn:
            require_admin(conn, request.headers.get("Authorization"))
            data = export_training_data(conn, limit=limit, label_name=label_name)
            return jsonify(data), 200
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500    

@api_bp.post("/auth/register")
def auth_register():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            data = register_user(conn, payload)
            return jsonify(data), 201
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.post("/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}

    try:
        with db.engine.begin() as conn:
            data = login_user(conn, payload)
            return jsonify(data), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500


@api_bp.get("/users/me/recommendations")
def users_me_recommendations():
    page = request.args.get("page", 1)
    page_size = request.args.get("pageSize", 20)

    try:
        page = int(page)
    except Exception:
        page = 1

    try:
        page_size = int(page_size)
    except Exception:
        page_size = 20

    try:
        with db.engine.begin() as conn:
            current_user = require_current_user(conn, request.headers.get("Authorization"))
            data = get_my_recommendations(
                conn,
                user_id=current_user["id"],
                page=page,
                page_size=page_size,
            )
            return jsonify(data), 200
    except ValueError as e:
        msg = str(e)
        if "token" in msg.lower() or "Bearer" in msg:
            return jsonify({"message": msg}), 401
        return jsonify({"message": msg}), 400
    except Exception as e:
        return jsonify({"message": "Lỗi backend", "detail": str(e)}), 500