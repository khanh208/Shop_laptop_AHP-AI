import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
from sklearn.linear_model import LinearRegression


# 1. Load dataset
df = pd.read_excel("AHP_Laptop_Nhom8.xlsx", sheet_name="Laptop_Data")

# 2. Chọn feature và target
features = [
    "Norm_CPU", "Norm_RAM", "Norm_GPU",
    "Norm_Screen", "Norm_Weight",
    "Norm_Battery", "Norm_Durability",
    "Norm_Upgrade", "Price (VND)"
]

target = "AHP Score"

# 3. Làm sạch dữ liệu
df = df.dropna(subset=features + [target])

X = df[features]
y = df[target]

# 4. Chia train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# 5. Train Random Forest
model = RandomForestRegressor(
    n_estimators=300,
    max_depth=None,
    random_state=42
)

model.fit(X_train, y_train)

# 6. Dự đoán
y_pred = model.predict(X_test)

# 7. Đánh giá mô hình
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print("===== MODEL EVALUATION =====")
print("R2 Score:", r2)
print("MAE:", mae)
print("RMSE:", rmse)

# 8. Feature importance
importance = pd.Series(model.feature_importances_, index=features)
print("\n===== FEATURE IMPORTANCE =====")
print(importance.sort_values(ascending=False))

# 9. Lưu model
joblib.dump(model, "rf_ahp_model.pkl")

print("\nModel saved successfully!")