-- =========================================================
-- LAPTOP RECOMMENDER DATABASE - FINAL FULL SCHEMA
-- PostgreSQL
-- =========================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 0) HELPER FUNCTION
-- =========================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- 1) USERS
-- =========================================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone_number VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'user'
        CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- 2) RECOMMENDATION CRITERIA
-- 8 tiêu chí FE hiển thị + AHP + AI scoring
-- =========================================================
CREATE TABLE recommendation_criteria (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    direction VARCHAR(20) NOT NULL DEFAULT 'benefit'
        CHECK (direction IN ('benefit', 'cost')),
    sort_order SMALLINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO recommendation_criteria (code, name, description, direction, sort_order)
VALUES
('cpu', 'CPU', 'Hiệu năng bộ xử lý cho tác vụ học tập, văn phòng, lập trình, xử lý nặng', 'benefit', 1),
('ram', 'RAM', 'Dung lượng bộ nhớ cho đa nhiệm, file lớn, IDE, nhiều tab', 'benefit', 2),
('gpu', 'GPU', 'Sức mạnh đồ họa cho game, AI, thiết kế, dựng video', 'benefit', 3),
('screen', 'Màn hình', 'Kích thước, độ phân giải, chất lượng hiển thị, tần số quét', 'benefit', 4),
('weight', 'Trọng lượng', 'Máy càng nhẹ càng dễ mang theo', 'cost', 5),
('battery', 'Pin', 'Thời lượng pin khi không cắm sạc', 'benefit', 6),
('durability', 'Độ bền', 'Độ bền tổng thể và độ ổn định lâu dài', 'benefit', 7),
('upgradeability', 'Nâng cấp', 'Khả năng nâng cấp RAM/SSD trong tương lai', 'benefit', 8)
ON CONFLICT (code) DO NOTHING;

-- =========================================================
-- 3) USAGE PROFILES
-- User chỉ chọn mục đích sử dụng
-- =========================================================
CREATE TABLE usage_profiles (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO usage_profiles (code, name, description)
VALUES
('general', 'Phổ thông', 'Nhu cầu chung, lướt web, học tập, văn phòng nhẹ'),
('accountant', 'Kế toán', 'Excel nặng, phần mềm kế toán, nhiều tab, làm việc văn phòng'),
('programmer', 'Lập trình', 'IDE, Docker, máy ảo, backend/frontend, compile'),
('student_it', 'Sinh viên CNTT', 'Lập trình, Docker, thuật toán, cần RAM và CPU mạnh, nâng cấp dễ'),
('student_economics', 'Sinh viên Kinh tế', 'Làm slide, Word, Excel, chạy deadline di động, ưu tiên mỏng nhẹ pin trâu'),
('student_design', 'Sinh viên Đồ họa', 'Photoshop, Premiere, render 3D, màn chuẩn màu, GPU/VGA mạnh'),
('student_engineering', 'Sinh viên Cơ khí', 'AutoCAD, SolidWorks, MATLAB, mô phỏng nặng, ưu tiên CPU/GPU tản nhiệt tốt'),
('gamer', 'Chơi game', 'Game online/offline, ưu tiên GPU/CPU/màn hình'),
('designer', 'Thiết kế', 'Photoshop, Figma, Illustrator, Premiere, hiển thị đẹp'),
('office', 'Văn phòng', 'Word, Excel, trình chiếu, họp online')
ON CONFLICT (code) DO NOTHING;

-- =========================================================
-- 4) USAGE PROFILE -> CRITERION RULES
-- Điểm nền theo mục đích sử dụng
-- =========================================================
CREATE TABLE usage_profile_criterion_rules (
    id BIGSERIAL PRIMARY KEY,
    usage_profile_id BIGINT NOT NULL REFERENCES usage_profiles(id) ON DELETE CASCADE,
    criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    base_score NUMERIC(10,4) NOT NULL DEFAULT 0 CHECK (base_score >= 0),
    explanation_template TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usage_profile_id, criterion_id)
);

WITH rule_seed(profile_code, criterion_code, base_score, explanation_template) AS (
    VALUES
    -- general
    ('general', 'cpu', 1.5, 'Nhu cầu phổ thông vẫn cần CPU ổn định.'),
    ('general', 'ram', 1.5, 'Nhu cầu phổ thông cần RAM đủ để đa nhiệm cơ bản.'),
    ('general', 'gpu', 0.5, 'GPU không phải ưu tiên chính cho nhu cầu phổ thông.'),
    ('general', 'screen', 1.0, 'Màn hình ở mức vừa đủ cho nhu cầu hằng ngày.'),
    ('general', 'weight', 1.0, 'Máy gọn nhẹ ở mức vừa phải là phù hợp.'),
    ('general', 'battery', 1.2, 'Pin khá là một lợi thế cho nhu cầu hằng ngày.'),
    ('general', 'durability', 1.2, 'Độ bền ổn định có ích cho người dùng phổ thông.'),
    ('general', 'upgradeability', 1.0, 'Khả năng nâng cấp ở mức trung bình là hợp lý.'),

    -- accountant
    ('accountant', 'cpu', 2.5, 'Kế toán thường xử lý Excel và phần mềm nghiệp vụ nên CPU quan trọng.'),
    ('accountant', 'ram', 3.0, 'Kế toán thường mở nhiều file và nhiều tab nên RAM rất quan trọng.'),
    ('accountant', 'gpu', 0.5, 'GPU ít quan trọng với nhu cầu kế toán.'),
    ('accountant', 'screen', 1.0, 'Màn hình cần đủ dễ nhìn cho số liệu và bảng biểu.'),
    ('accountant', 'weight', 1.0, 'Trọng lượng có ích nhưng không phải yếu tố chính.'),
    ('accountant', 'battery', 2.0, 'Pin khá tốt giúp làm việc linh hoạt.'),
    ('accountant', 'durability', 2.0, 'Độ bền và ổn định quan trọng cho môi trường công việc.'),
    ('accountant', 'upgradeability', 1.5, 'Dễ nâng cấp giúp dùng lâu dài hơn.'),

    -- programmer
    ('programmer', 'cpu', 3.0, 'Lập trình cần CPU mạnh để chạy IDE, compile, Docker và VM.'),
    ('programmer', 'ram', 3.0, 'Lập trình thường đa nhiệm nặng nên RAM rất quan trọng.'),
    ('programmer', 'gpu', 1.0, 'GPU có ích trong một số trường hợp nhưng không phải lúc nào cũng chính.'),
    ('programmer', 'screen', 1.0, 'Màn hình đủ tốt giúp làm việc lâu thoải mái hơn.'),
    ('programmer', 'weight', 1.5, 'Máy gọn nhẹ là lợi thế khi mang đi học hoặc làm việc.'),
    ('programmer', 'battery', 1.5, 'Pin ổn giúp linh hoạt khi học và làm việc.'),
    ('programmer', 'durability', 1.0, 'Độ bền quan trọng ở mức vừa phải.'),
    ('programmer', 'upgradeability', 2.0, 'Khả năng nâng cấp có ích cho nhu cầu dài hạn.'),

    -- student_it
    ('student_it', 'cpu', 2.8, 'Sinh viên CNTT cần CPU đa nhân để code, compile, chạy máy ảo.'),
    ('student_it', 'ram', 3.0, 'RAM là yếu tố cốt lõi để chạy các IDE nặng và Docker.'),
    ('student_it', 'gpu', 1.0, 'GPU rời có thể cần nếu học môn AI/Game, máy ảo hóa nhẹ.'),
    ('student_it', 'screen', 1.5, 'Màn hình đủ lớn và dịu mắt giúp code thoải mái dài hạn.'),
    ('student_it', 'weight', 1.8, 'Trọng lượng nhẹ giúp dễ mang máy lên PC lab và giảng đường.'),
    ('student_it', 'battery', 1.8, 'Pin khá giúp làm việc nhóm không phụ thuộc quá nhiều vào ổ cắm.'),
    ('student_it', 'durability', 1.5, 'Độ bền giúp máy gắn bó suốt 4 năm học.'),
    ('student_it', 'upgradeability', 2.5, 'Khả năng nấp cấp RAM, SSD về sau là cực kỳ quan trọng cho CNTT.'),

    -- student_economics
    ('student_economics', 'cpu', 1.5, 'CPU đủ dùng để chạy mượt Office, SPSS, đa phương tiện.'),
    ('student_economics', 'ram', 1.8, 'RAM cần ở mức vừa phải để mở nhiều tab tìm tài liệu.'),
    ('student_economics', 'gpu', 0.5, 'Sinh viên kinh tế thường không bắt buộc có GPU rới.'),
    ('student_economics', 'screen', 1.8, 'Cần màn hình đẹp để thuyết trình, làm slide, xem nội dung rõ nét.'),
    ('student_economics', 'weight', 3.0, 'Di chuyển cực nhiều, trọng lượng nhẹ là tối ưu nhất.'),
    ('student_economics', 'battery', 3.0, 'Pin trâu là yếu tố sống còn để học trên thư viện, quán cafe dài giờ.'),
    ('student_economics', 'durability', 1.5, 'Thiết kế bền bỉ và đẹp nhẹ là ưu thế.'),
    ('student_economics', 'upgradeability', 1.0, 'Ít khi cần chọc vào phần cứng nâng cấp.'),

    -- student_design
    ('student_design', 'cpu', 2.5, 'CPU xung lớn, đa nhân giúp xử lý tác vụ media, render hiệu quả.'),
    ('student_design', 'ram', 2.5, 'RAM tối thiểu 16GB để mở mượt mà Lightroom, Illustrator, Photoshop.'),
    ('student_design', 'gpu', 3.0, 'Bắt buộc cần GPU / card đồ họa khỏe để tăng tốc đồ họa, dựng video 3D.'),
    ('student_design', 'screen', 3.0, 'Màn hình chuẩn màu, sáng, màu sắc nịnh là cốt lõi dân thiết kế.'),
    ('student_design', 'weight', 1.0, 'Thường phải đánh đổi mang máy to dày để có cấu hình mạnh tản nhiệt tốt.'),
    ('student_design', 'battery', 1.0, 'Cấu hình cao ngốn điện, đa số cần cắm sạc khi render.'),
    ('student_design', 'durability', 1.5, 'Cần dàn tản nhiệt tốt, khung máy chắc chắn chịu nhiệt lâu.'),
    ('student_design', 'upgradeability', 1.5, 'Linh hoạt thêm ổ cứng để chứa kho file ảnh video thô đồ sộ.'),

    -- student_engineering
    ('student_engineering', 'cpu', 3.0, 'Mô phỏng AutoCAD, SolidWorks, MATLAB yêu cầu CPU cực kỳ trâu bò.'),
    ('student_engineering', 'ram', 2.5, 'Cần mức RAM lớn để xử lý bản vẽ lắp ráp phức tạp.'),
    ('student_engineering', 'gpu', 2.5, 'Rất cần GPU rời mạnh để xoay, render mô hình CAD 3D mượt mà.'),
    ('student_engineering', 'screen', 2.0, 'Màn hình kích thước đủ lớn dễ quan sát bản vẽ chi tiết.'),
    ('student_engineering', 'weight', 1.0, 'Dòng workstation / gaming phục vụ mô phỏng thường rất nặng.'),
    ('student_engineering', 'battery', 1.0, 'Pin hao rất nhanh khi dùng app CAD, thường xuyên cần cắm điện.'),
    ('student_engineering', 'durability', 2.0, 'Độ bền khung nhôm, tản nhiệt buồng hơi rất quan trọng cho vận hành.'),
    ('student_engineering', 'upgradeability', 1.5, 'Thêm tùy chọn gắn ổ rộng rãi phục vụ lưu phần mềm mô phỏng nặng.'),

    -- gamer
    ('gamer', 'cpu', 2.5, 'Chơi game cần CPU tốt để hỗ trợ hiệu năng ổn định.'),
    ('gamer', 'ram', 2.0, 'RAM đủ lớn giúp game và đa nhiệm mượt hơn.'),
    ('gamer', 'gpu', 3.0, 'GPU là tiêu chí quan trọng nhất cho game.'),
    ('gamer', 'screen', 2.0, 'Màn hình tốt và tần số quét cao giúp trải nghiệm game tốt hơn.'),
    ('gamer', 'weight', 0.5, 'Trọng lượng ít quan trọng hơn với gaming laptop.'),
    ('gamer', 'battery', 0.5, 'Pin thường không phải ưu tiên chính khi chơi game.'),
    ('gamer', 'durability', 1.2, 'Độ bền vẫn quan trọng cho sử dụng lâu dài.'),
    ('gamer', 'upgradeability', 1.2, 'Khả năng nâng cấp là điểm cộng cho game lâu dài.'),

    -- designer
    ('designer', 'cpu', 2.0, 'Thiết kế và media vẫn cần CPU tốt.'),
    ('designer', 'ram', 2.5, 'Thiết kế thường cần RAM khá cao cho đa nhiệm và file nặng.'),
    ('designer', 'gpu', 2.5, 'GPU quan trọng cho đồ họa và media.'),
    ('designer', 'screen', 3.0, 'Màn hình là tiêu chí rất quan trọng cho thiết kế.'),
    ('designer', 'weight', 1.0, 'Trọng lượng là lợi thế nhưng không phải số 1.'),
    ('designer', 'battery', 1.0, 'Pin ở mức vừa phải.'),
    ('designer', 'durability', 1.0, 'Độ bền ở mức vừa phải.'),
    ('designer', 'upgradeability', 1.0, 'Dễ nâng cấp là điểm cộng.'),

    -- office
    ('office', 'cpu', 1.8, 'Văn phòng cần CPU khá cho công việc hằng ngày.'),
    ('office', 'ram', 2.0, 'RAM khá quan trọng để mở nhiều tab và nhiều file cùng lúc.'),
    ('office', 'gpu', 0.3, 'GPU hầu như không phải yếu tố chính cho văn phòng.'),
    ('office', 'screen', 1.0, 'Màn hình đủ dùng là hợp lý.'),
    ('office', 'weight', 1.5, 'Máy gọn nhẹ là lợi thế cho làm việc linh hoạt.'),
    ('office', 'battery', 1.8, 'Pin khá là một điểm cộng quan trọng.'),
    ('office', 'durability', 1.5, 'Độ bền ổn định phù hợp môi trường làm việc.'),
    ('office', 'upgradeability', 1.0, 'Khả năng nâng cấp ở mức vừa phải.')
)
INSERT INTO usage_profile_criterion_rules (usage_profile_id, criterion_id, base_score, explanation_template)
SELECT up.id, rc.id, rs.base_score, rs.explanation_template
FROM rule_seed rs
JOIN usage_profiles up ON up.code = rs.profile_code
JOIN recommendation_criteria rc ON rc.code = rs.criterion_code
ON CONFLICT (usage_profile_id, criterion_id) DO NOTHING;

-- =========================================================
-- 5) BRANDS
-- =========================================================
CREATE TABLE brands (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    logo_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 6) CPU / GPU REFERENCE
-- User filter theo CPU/GPU code, backend map ra benchmark
-- =========================================================
CREATE TABLE cpu_reference (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(80) UNIQUE NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    benchmark_score NUMERIC(10,2),
    tier_rank INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO cpu_reference (code, display_name, benchmark_score, tier_rank)
VALUES
('intel_i5_1240p', 'Intel Core i5-1240P', 14500, 5),
('intel_i7_13620h', 'Intel Core i7-13620H', 21000, 7),
('intel_ultra_7_155h', 'Intel Core Ultra 7 155H', 23500, 8),
('ryzen_5_7535hs', 'AMD Ryzen 5 7535HS', 18500, 6),
('ryzen_7_7840hs', 'AMD Ryzen 7 7840HS', 24000, 8)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE gpu_reference (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(80) UNIQUE NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    benchmark_score NUMERIC(10,2),
    tier_rank INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO gpu_reference (code, display_name, benchmark_score, tier_rank)
VALUES
('intel_iris_xe', 'Intel Iris Xe', 2500, 1),
('radeon_780m', 'AMD Radeon 780M', 4500, 2),
('gtx_1080', 'NVIDIA GTX 1080', 9000, 5),
('rtx_2050', 'NVIDIA RTX 2050', 6500, 4),
('rtx_3050', 'NVIDIA RTX 3050 Laptop', 9500, 5),
('rtx_4050', 'NVIDIA RTX 4050 Laptop', 13500, 6),
('rtx_4060', 'NVIDIA RTX 4060 Laptop', 16500, 7)
ON CONFLICT (code) DO NOTHING;

-- =========================================================
-- 7) LAPTOPS
-- =========================================================
CREATE TABLE laptops (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT REFERENCES brands(id) ON DELETE SET NULL,

    sku VARCHAR(80) UNIQUE,
    name VARCHAR(255) NOT NULL,
    model_code VARCHAR(120) NOT NULL DEFAULT '',

    cpu_name VARCHAR(180) NOT NULL,
    cpu_benchmark_score NUMERIC(10,2),
    gpu_name VARCHAR(180),
    gpu_benchmark_score NUMERIC(10,2),

    ram_gb INTEGER NOT NULL CHECK (ram_gb >= 0),
    ram_type VARCHAR(50),
    ram_speed_mhz INTEGER,
    ram_slots_total SMALLINT,
    ram_slots_free SMALLINT,

    ssd_gb INTEGER NOT NULL CHECK (ssd_gb >= 0),
    ssd_type VARCHAR(30),
    ssd_slots_total SMALLINT,
    ssd_slots_free SMALLINT,

    screen_size_inch NUMERIC(4,1),
    screen_resolution VARCHAR(50),
    screen_panel VARCHAR(50),
    refresh_rate_hz SMALLINT,

    weight_kg NUMERIC(5,2),
    battery_hours NUMERIC(5,2),
    battery_wh NUMERIC(6,2),

    durability_score NUMERIC(6,2),
    upgradeability_score NUMERIC(6,2),

    has_dedicated_gpu BOOLEAN DEFAULT FALSE,
    has_usb_c BOOLEAN DEFAULT FALSE,
    has_hdmi BOOLEAN DEFAULT FALSE,
    has_thunderbolt BOOLEAN DEFAULT FALSE,

    os_name VARCHAR(50),
    condition_status VARCHAR(20) NOT NULL DEFAULT 'new'
        CHECK (condition_status IN ('new', 'used', 'refurbished')),

    release_year INTEGER,
    warranty_months SMALLINT,

    price NUMERIC(15,2) NOT NULL CHECK (price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),

    image_url TEXT,
    product_url TEXT,
    description TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_laptops_name_model UNIQUE (name, model_code)
);

CREATE TRIGGER trg_laptops_updated_at
BEFORE UPDATE ON laptops
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_laptops_brand_id ON laptops(brand_id);
CREATE INDEX idx_laptops_price ON laptops(price);
CREATE INDEX idx_laptops_ram_gb ON laptops(ram_gb);
CREATE INDEX idx_laptops_ssd_gb ON laptops(ssd_gb);
CREATE INDEX idx_laptops_cpu_benchmark ON laptops(cpu_benchmark_score);
CREATE INDEX idx_laptops_gpu_benchmark ON laptops(gpu_benchmark_score);
CREATE INDEX idx_laptops_weight_kg ON laptops(weight_kg);
CREATE INDEX idx_laptops_battery_hours ON laptops(battery_hours);
CREATE INDEX idx_laptops_active_stock ON laptops(is_active, stock_quantity);

-- =========================================================
-- 8) LAPTOP IMAGES
-- =========================================================
CREATE TABLE laptop_images (
    id BIGSERIAL PRIMARY KEY,
    laptop_id BIGINT NOT NULL REFERENCES laptops(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    alt_text VARCHAR(255),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_laptop_images_laptop_id ON laptop_images(laptop_id);
CREATE INDEX idx_laptop_images_primary ON laptop_images(laptop_id, is_primary);

-- =========================================================
-- 9) STAGING TABLE - IMPORT DATA
-- =========================================================
CREATE TABLE stg_laptop_data (
    id BIGSERIAL PRIMARY KEY,
    import_batch VARCHAR(50) NOT NULL DEFAULT 'batch_1',
    source_file_name VARCHAR(255),

    brand_name VARCHAR(100),
    laptop_name VARCHAR(255),
    model_code VARCHAR(120) DEFAULT '',

    cpu_name VARCHAR(180),
    cpu_benchmark_score NUMERIC(10,2),
    gpu_name VARCHAR(180),
    gpu_benchmark_score NUMERIC(10,2),

    ram_gb INTEGER,
    ssd_gb INTEGER,
    screen_size_inch NUMERIC(4,1),
    screen_resolution VARCHAR(50),
    refresh_rate_hz SMALLINT,
    weight_kg NUMERIC(5,2),
    battery_hours NUMERIC(5,2),

    durability_score NUMERIC(6,2),
    upgradeability_score NUMERIC(6,2),

    price NUMERIC(15,2),
    image_url TEXT,
    product_url TEXT,
    description TEXT,

    "Norm_CPU" NUMERIC(12,6),
    "Norm_RAM" NUMERIC(12,6),
    "Norm_GPU" NUMERIC(12,6),
    "Norm_Screen" NUMERIC(12,6),
    "Norm_Weight" NUMERIC(12,6),
    "Norm_Battery" NUMERIC(12,6),
    "Norm_Durability" NUMERIC(12,6),
    "Norm_Upgrade" NUMERIC(12,6),
    "Price (VND)" NUMERIC(15,2),
    "AHP Score" NUMERIC(12,6),

    raw_row JSONB,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stg_laptop_data_batch ON stg_laptop_data(import_batch);

-- =========================================================
-- 10) LAPTOP ML FEATURES
-- =========================================================
CREATE TABLE laptop_ml_features (
    id BIGSERIAL PRIMARY KEY,
    laptop_id BIGINT NOT NULL UNIQUE REFERENCES laptops(id) ON DELETE CASCADE,

    norm_cpu NUMERIC(12,6),
    norm_ram NUMERIC(12,6),
    norm_gpu NUMERIC(12,6),
    norm_screen NUMERIC(12,6),
    norm_weight NUMERIC(12,6),
    norm_battery NUMERIC(12,6),
    norm_durability NUMERIC(12,6),
    norm_upgradeability NUMERIC(12,6),

    feature_vector JSONB,
    features_version VARCHAR(50) NOT NULL DEFAULT 'v1',
    prepared_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_norm_cpu CHECK (norm_cpu IS NULL OR (norm_cpu >= 0 AND norm_cpu <= 1)),
    CONSTRAINT chk_norm_ram CHECK (norm_ram IS NULL OR (norm_ram >= 0 AND norm_ram <= 1)),
    CONSTRAINT chk_norm_gpu CHECK (norm_gpu IS NULL OR (norm_gpu >= 0 AND norm_gpu <= 1)),
    CONSTRAINT chk_norm_screen CHECK (norm_screen IS NULL OR (norm_screen >= 0 AND norm_screen <= 1)),
    CONSTRAINT chk_norm_weight CHECK (norm_weight IS NULL OR (norm_weight >= 0 AND norm_weight <= 1)),
    CONSTRAINT chk_norm_battery CHECK (norm_battery IS NULL OR (norm_battery >= 0 AND norm_battery <= 1)),
    CONSTRAINT chk_norm_durability CHECK (norm_durability IS NULL OR (norm_durability >= 0 AND norm_durability <= 1)),
    CONSTRAINT chk_norm_upgradeability CHECK (norm_upgradeability IS NULL OR (norm_upgradeability >= 0 AND norm_upgradeability <= 1))
);

CREATE INDEX idx_laptop_ml_features_version ON laptop_ml_features(features_version);

-- =========================================================
-- 11) TRAINING LABELS
-- =========================================================
CREATE TABLE laptop_training_labels (
    id BIGSERIAL PRIMARY KEY,
    laptop_id BIGINT NOT NULL REFERENCES laptops(id) ON DELETE CASCADE,
    label_name VARCHAR(100) NOT NULL,
    label_value NUMERIC(12,6) NOT NULL,
    source_file_name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (laptop_id, label_name)
);

-- =========================================================
-- 12) MODEL REGISTRY
-- =========================================================
CREATE TABLE ml_models (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(80) UNIQUE NOT NULL,
    criterion_id BIGINT REFERENCES recommendation_criteria(id) ON DELETE SET NULL,
    model_type VARCHAR(30) NOT NULL
        CHECK (model_type IN ('regression', 'classification', 'ranking', 'hybrid', 'heuristic')),
    algorithm_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    artifact_path TEXT,
    metadata JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ml_models_active ON ml_models(is_active);
CREATE INDEX idx_ml_models_criterion ON ml_models(criterion_id);

-- =========================================================
-- 13) EVALUATION SESSIONS
-- 1 dòng = 1 lần user yêu cầu recommend
-- =========================================================
CREATE TABLE evaluation_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_key UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,

    mode VARCHAR(20) NOT NULL DEFAULT 'basic'
        CHECK (mode IN ('basic', 'advanced')),
    usage_profile_id BIGINT NOT NULL REFERENCES usage_profiles(id) ON DELETE RESTRICT,

    request_payload JSONB NOT NULL,
    top_n INTEGER NOT NULL DEFAULT 10 CHECK (top_n > 0),

    status VARCHAR(20) NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'filtered', 'inferred', 'weighted', 'scored', 'ranked', 'completed', 'failed')),

    budget_min NUMERIC(15,2),
    budget_max NUMERIC(15,2),

    hard_filter_total_count INTEGER,
    hard_filter_pass_count INTEGER,

    ahp_ci NUMERIC(18,8),
    ahp_cr NUMERIC(18,8),
    ahp_is_consistent BOOLEAN,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TRIGGER trg_evaluation_sessions_updated_at
BEFORE UPDATE ON evaluation_sessions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_evaluation_sessions_user_id ON evaluation_sessions(user_id);
CREATE INDEX idx_evaluation_sessions_usage_profile_id ON evaluation_sessions(usage_profile_id);
CREATE INDEX idx_evaluation_sessions_status ON evaluation_sessions(status);
CREATE INDEX idx_evaluation_sessions_created_at ON evaluation_sessions(created_at DESC);

-- =========================================================
-- 14) FILTERS USER NHẬP
-- =========================================================
CREATE TABLE evaluation_filters (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL UNIQUE REFERENCES evaluation_sessions(id) ON DELETE CASCADE,

    brand_id BIGINT REFERENCES brands(id) ON DELETE SET NULL,
    requested_cpu_reference_id BIGINT REFERENCES cpu_reference(id) ON DELETE SET NULL,
    requested_gpu_reference_id BIGINT REFERENCES gpu_reference(id) ON DELETE SET NULL,

    min_price NUMERIC(15,2),
    max_price NUMERIC(15,2),

    min_ram_gb INTEGER,
    min_ssd_gb INTEGER,

    min_cpu_benchmark_score NUMERIC(10,2),
    min_gpu_benchmark_score NUMERIC(10,2),

    min_screen_size_inch NUMERIC(4,1),
    max_screen_size_inch NUMERIC(4,1),

    max_weight_kg NUMERIC(5,2),
    min_battery_hours NUMERIC(5,2),

    require_in_stock BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_eval_filter_price_range
        CHECK (min_price IS NULL OR max_price IS NULL OR min_price <= max_price),
    CONSTRAINT chk_eval_filter_screen_range
        CHECK (min_screen_size_inch IS NULL OR max_screen_size_inch IS NULL OR min_screen_size_inch <= max_screen_size_inch)
);

-- =========================================================
-- 15) INFERRED PRIORITIES
-- Backend tự suy ra priority từ usage profile + filter
-- =========================================================
CREATE TABLE session_inferred_priorities (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,

    source_type VARCHAR(20) NOT NULL
        CHECK (source_type IN ('profile', 'filter', 'combined')),
    source_key VARCHAR(100) NOT NULL,

    score_delta NUMERIC(10,4) NOT NULL DEFAULT 0,
    final_score_after NUMERIC(10,4),
    explanation_text TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (evaluation_session_id, criterion_id, source_type, source_key)
);

CREATE INDEX idx_session_inferred_priorities_session
ON session_inferred_priorities(evaluation_session_id);

CREATE INDEX idx_session_inferred_priorities_criterion
ON session_inferred_priorities(criterion_id);

-- =========================================================
-- 16) HARD FILTER CANDIDATES
-- =========================================================
CREATE TABLE evaluation_candidates (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    laptop_id BIGINT NOT NULL REFERENCES laptops(id) ON DELETE CASCADE,
    hard_filter_passed BOOLEAN NOT NULL,
    failed_rules JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_session_id, laptop_id)
);

CREATE INDEX idx_evaluation_candidates_session_passed
ON evaluation_candidates(evaluation_session_id, hard_filter_passed);

-- =========================================================
-- 17) AHP PAIRWISE MATRIX
-- =========================================================
CREATE TABLE evaluation_pairwise_matrix (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    criterion_1_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    criterion_2_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    comparison_value NUMERIC(18,8) NOT NULL CHECK (comparison_value > 0),
    source_type VARCHAR(20) NOT NULL DEFAULT 'derived'
        CHECK (source_type IN ('derived', 'manual', 'adjusted')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_session_id, criterion_1_id, criterion_2_id),
    CONSTRAINT chk_pairwise_not_same CHECK (criterion_1_id <> criterion_2_id)
);

-- =========================================================
-- 18) AHP MATRIX CELLS
-- pairwise / normalized / weighted
-- =========================================================
CREATE TABLE evaluation_ahp_matrix_cells (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    matrix_type VARCHAR(30) NOT NULL
        CHECK (matrix_type IN ('pairwise', 'normalized', 'weighted')),
    row_criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    col_criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    cell_value NUMERIC(18,8) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_session_id, matrix_type, row_criterion_id, col_criterion_id)
);

CREATE INDEX idx_evaluation_ahp_matrix_cells_session
ON evaluation_ahp_matrix_cells(evaluation_session_id, matrix_type);

-- =========================================================
-- 19) AHP SUMMARY
-- =========================================================
CREATE TABLE evaluation_ahp_summary (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL UNIQUE REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    criteria_count INTEGER NOT NULL CHECK (criteria_count > 0),
    lambda_max NUMERIC(18,8),
    ci NUMERIC(18,8),
    ri NUMERIC(18,8),
    cr NUMERIC(18,8),
    is_consistent BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 20) FINAL WEIGHTS
-- =========================================================
CREATE TABLE evaluation_weights (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,

    source_score NUMERIC(12,6),
    raw_weight NUMERIC(18,8),
    normalized_weight NUMERIC(18,8) NOT NULL
        CHECK (normalized_weight >= 0 AND normalized_weight <= 1),

    display_order SMALLINT,
    explanation_text TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (evaluation_session_id, criterion_id)
);

CREATE INDEX idx_evaluation_weights_session_id
ON evaluation_weights(evaluation_session_id);

-- =========================================================
-- 21) AI SCORES
-- =========================================================
CREATE TABLE evaluation_ai_scores (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    laptop_id BIGINT NOT NULL REFERENCES laptops(id) ON DELETE CASCADE,
    criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    model_id BIGINT REFERENCES ml_models(id) ON DELETE SET NULL,

    raw_prediction NUMERIC(18,8) NOT NULL,
    normalized_prediction NUMERIC(18,8),
    score_100 NUMERIC(12,6) NOT NULL CHECK (score_100 >= 0 AND score_100 <= 100),
    input_snapshot JSONB,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (evaluation_session_id, laptop_id, criterion_id)
);

CREATE INDEX idx_evaluation_ai_scores_session_laptop
ON evaluation_ai_scores(evaluation_session_id, laptop_id);

CREATE INDEX idx_evaluation_ai_scores_criterion
ON evaluation_ai_scores(criterion_id);

-- =========================================================
-- 22) FINAL RESULTS / RANKING
-- =========================================================
CREATE TABLE evaluation_results (
    id BIGSERIAL PRIMARY KEY,
    evaluation_session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    laptop_id BIGINT NOT NULL REFERENCES laptops(id) ON DELETE CASCADE,
    total_score NUMERIC(18,8) NOT NULL,
    match_percent NUMERIC(6,2) CHECK (match_percent >= 0 AND match_percent <= 100),
    rank_position INTEGER NOT NULL CHECK (rank_position > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_session_id, laptop_id),
    UNIQUE (evaluation_session_id, rank_position)
);

CREATE INDEX idx_evaluation_results_session_rank
ON evaluation_results(evaluation_session_id, rank_position);

CREATE TABLE evaluation_result_details (
    id BIGSERIAL PRIMARY KEY,
    evaluation_result_id BIGINT NOT NULL REFERENCES evaluation_results(id) ON DELETE CASCADE,
    criterion_id BIGINT NOT NULL REFERENCES recommendation_criteria(id) ON DELETE CASCADE,
    criterion_weight NUMERIC(18,8) NOT NULL CHECK (criterion_weight >= 0 AND criterion_weight <= 1),
    ai_score_100 NUMERIC(12,6) NOT NULL CHECK (ai_score_100 >= 0 AND ai_score_100 <= 100),
    weighted_score NUMERIC(18,8) NOT NULL,
    explanation_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_result_id, criterion_id)
);

CREATE INDEX idx_evaluation_result_details_result_id
ON evaluation_result_details(evaluation_result_id);

CREATE TABLE evaluation_result_reasons (
    id BIGSERIAL PRIMARY KEY,
    evaluation_result_id BIGINT NOT NULL REFERENCES evaluation_results(id) ON DELETE CASCADE,
    badge_code VARCHAR(50) NOT NULL,
    badge_label VARCHAR(120) NOT NULL,
    reason_text TEXT,
    priority_order SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evaluation_result_reasons_result_id
ON evaluation_result_reasons(evaluation_result_id);

-- =========================================================
-- 23) VIEWS
-- =========================================================
CREATE OR REPLACE VIEW v_ml_export_laptop_data AS
SELECT
    l.id AS laptop_id,
    l.name AS laptop_name,
    f.norm_cpu AS "Norm_CPU",
    f.norm_ram AS "Norm_RAM",
    f.norm_gpu AS "Norm_GPU",
    f.norm_screen AS "Norm_Screen",
    f.norm_weight AS "Norm_Weight",
    f.norm_battery AS "Norm_Battery",
    f.norm_durability AS "Norm_Durability",
    f.norm_upgradeability AS "Norm_Upgrade",
    COALESCE(l.price, 0) AS "Price (VND)"
FROM laptops l
JOIN laptop_ml_features f ON f.laptop_id = l.id
WHERE l.is_active = TRUE;

CREATE OR REPLACE VIEW v_recommendation_ready_laptops AS
SELECT
    l.id,
    l.brand_id,
    l.name,
    l.model_code,
    l.price,
    l.ram_gb,
    l.ssd_gb,
    l.cpu_name,
    l.cpu_benchmark_score,
    l.gpu_name,
    l.gpu_benchmark_score,
    l.screen_size_inch,
    l.weight_kg,
    l.battery_hours,
    l.durability_score,
    l.upgradeability_score,
    l.image_url,
    f.norm_cpu,
    f.norm_ram,
    f.norm_gpu,
    f.norm_screen,
    f.norm_weight,
    f.norm_battery,
    f.norm_durability,
    f.norm_upgradeability
FROM laptops l
JOIN laptop_ml_features f ON f.laptop_id = l.id
WHERE l.is_active = TRUE;

CREATE OR REPLACE VIEW v_session_top_results AS
SELECT
    er.evaluation_session_id,
    er.rank_position,
    er.total_score,
    er.match_percent,
    l.id AS laptop_id,
    b.name AS brand_name,
    l.name AS laptop_name,
    l.model_code,
    l.price,
    l.ram_gb,
    l.ssd_gb,
    l.weight_kg,
    l.battery_hours,
    COALESCE(li.image_url, l.image_url) AS image_url
FROM evaluation_results er
JOIN laptops l ON l.id = er.laptop_id
LEFT JOIN brands b ON b.id = l.brand_id
LEFT JOIN LATERAL (
    SELECT image_url
    FROM laptop_images
    WHERE laptop_id = l.id AND is_primary = TRUE
    ORDER BY sort_order ASC, id ASC
    LIMIT 1
) li ON TRUE;

-- =========================================================
-- 24) PROCEDURE IMPORT TỪ STAGING
-- =========================================================
CREATE OR REPLACE PROCEDURE sp_import_laptop_data()
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Import brands
    INSERT INTO brands (code, name)
    SELECT DISTINCT 
        LOWER(REGEXP_REPLACE(TRIM(brand_name), '\s+', '-', 'g')),
        TRIM(brand_name)
    FROM stg_laptop_data
    WHERE brand_name IS NOT NULL
      AND TRIM(brand_name) <> ''
    ON CONFLICT (name) DO NOTHING;

    -- 2. Import / update laptops
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
        is_active,
        stock_quantity
    )
    SELECT
        b.id,
        COALESCE(NULLIF(TRIM(s.laptop_name), ''), 'Unknown Laptop'),
        COALESCE(NULLIF(TRIM(s.model_code), ''), ''),
        COALESCE(NULLIF(TRIM(s.cpu_name), ''), 'Unknown CPU'),
        s.cpu_benchmark_score,
        NULLIF(TRIM(s.gpu_name), ''),
        s.gpu_benchmark_score,
        COALESCE(s.ram_gb, 0),
        COALESCE(s.ssd_gb, 0),
        s.screen_size_inch,
        s.screen_resolution,
        s.refresh_rate_hz,
        s.weight_kg,
        s.battery_hours,
        s.durability_score,
        s.upgradeability_score,
        COALESCE(s."Price (VND)", s.price, 0),
        s.image_url,
        s.product_url,
        s.description,
        TRUE,
        999
    FROM stg_laptop_data s
    LEFT JOIN brands b ON b.name = TRIM(s.brand_name)
    ON CONFLICT (name, model_code)
    DO UPDATE SET
        brand_id = EXCLUDED.brand_id,
        cpu_name = EXCLUDED.cpu_name,
        cpu_benchmark_score = EXCLUDED.cpu_benchmark_score,
        gpu_name = EXCLUDED.gpu_name,
        gpu_benchmark_score = EXCLUDED.gpu_benchmark_score,
        ram_gb = EXCLUDED.ram_gb,
        ssd_gb = EXCLUDED.ssd_gb,
        screen_size_inch = EXCLUDED.screen_size_inch,
        screen_resolution = EXCLUDED.screen_resolution,
        refresh_rate_hz = EXCLUDED.refresh_rate_hz,
        weight_kg = EXCLUDED.weight_kg,
        battery_hours = EXCLUDED.battery_hours,
        durability_score = EXCLUDED.durability_score,
        upgradeability_score = EXCLUDED.upgradeability_score,
        price = EXCLUDED.price,
        image_url = COALESCE(EXCLUDED.image_url, laptops.image_url),
        product_url = COALESCE(EXCLUDED.product_url, laptops.product_url),
        description = COALESCE(EXCLUDED.description, laptops.description),
        updated_at = CURRENT_TIMESTAMP;

    -- 3. Import / update feature store
    INSERT INTO laptop_ml_features (
        laptop_id,
        norm_cpu,
        norm_ram,
        norm_gpu,
        norm_screen,
        norm_weight,
        norm_battery,
        norm_durability,
        norm_upgradeability,
        feature_vector,
        features_version
    )
    SELECT
        l.id,
        s."Norm_CPU",
        s."Norm_RAM",
        s."Norm_GPU",
        s."Norm_Screen",
        s."Norm_Weight",
        s."Norm_Battery",
        s."Norm_Durability",
        s."Norm_Upgrade",
        jsonb_build_object(
            'Norm_CPU', s."Norm_CPU",
            'Norm_RAM', s."Norm_RAM",
            'Norm_GPU', s."Norm_GPU",
            'Norm_Screen', s."Norm_Screen",
            'Norm_Weight', s."Norm_Weight",
            'Norm_Battery', s."Norm_Battery",
            'Norm_Durability', s."Norm_Durability",
            'Norm_Upgrade', s."Norm_Upgrade",
            'Price (VND)', COALESCE(s."Price (VND)", s.price),
            'AHP Score', s."AHP Score"
        ),
        'v1'
    FROM stg_laptop_data s
    JOIN laptops l
      ON l.name = COALESCE(NULLIF(TRIM(s.laptop_name), ''), 'Unknown Laptop')
     AND l.model_code = COALESCE(NULLIF(TRIM(s.model_code), ''), '')
    ON CONFLICT (laptop_id)
    DO UPDATE SET
        norm_cpu = EXCLUDED.norm_cpu,
        norm_ram = EXCLUDED.norm_ram,
        norm_gpu = EXCLUDED.norm_gpu,
        norm_screen = EXCLUDED.norm_screen,
        norm_weight = EXCLUDED.norm_weight,
        norm_battery = EXCLUDED.norm_battery,
        norm_durability = EXCLUDED.norm_durability,
        norm_upgradeability = EXCLUDED.norm_upgradeability,
        feature_vector = EXCLUDED.feature_vector,
        features_version = EXCLUDED.features_version,
        prepared_at = CURRENT_TIMESTAMP;

    -- 4. Import / update training labels
    INSERT INTO laptop_training_labels (
        laptop_id,
        label_name,
        label_value,
        source_file_name
    )
    SELECT
        l.id,
        'AHP Score',
        s."AHP Score",
        s.source_file_name
    FROM stg_laptop_data s
    JOIN laptops l
      ON l.name = COALESCE(NULLIF(TRIM(s.laptop_name), ''), 'Unknown Laptop')
     AND l.model_code = COALESCE(NULLIF(TRIM(s.model_code), ''), '')
    WHERE s."AHP Score" IS NOT NULL
    ON CONFLICT (laptop_id, label_name)
    DO UPDATE SET
        label_value = EXCLUDED.label_value,
        source_file_name = EXCLUDED.source_file_name;
END;
$$;

-- =========================================================
-- 25) GỢI Ý IMPORT DATA
-- Sau khi upload/import file vào stg_laptop_data
-- chỉ cần chạy:
--
-- CALL sp_import_laptop_data();
--
-- Nếu bạn làm qua API Flask, API sẽ:
-- 1. đọc file Excel/CSV
-- 2. insert vào stg_laptop_data
-- 3. gọi CALL sp_import_laptop_data();
-- =========================================================