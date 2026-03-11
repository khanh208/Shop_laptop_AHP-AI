import pandas as pd
import numpy as np
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

print("=== TRAIN AI MODELS FOR DSS ===\n")

# =============================
# STEP 1: Load dataset
# =============================
df = pd.read_excel("AHP_Laptop_Nhom8.xlsx", sheet_name="Laptop_Data")
df.columns = df.columns.str.strip()

# remove missing rows
df = df.dropna(subset=[
    "Norm_CPU",
    "Norm_RAM",
    "Norm_GPU",
    "Norm_Screen",
    "Norm_Weight",
    "Norm_Battery",
    "Norm_Durability"
])

print("Dataset shape:", df.shape)

# =============================
# STEP 2: Features
# =============================
features = [
    "Norm_CPU",
    "Norm_RAM",
    "Norm_GPU",
    "Norm_Screen",
    "Norm_Weight",
    "Norm_Battery",
    "Norm_Durability"
]

X = df[features]

# =============================
# STEP 3: Create targets
# =============================

# Performance
df["Performance"] = (
    0.4 * df["Norm_CPU"] +
    0.3 * df["Norm_RAM"] +
    0.3 * df["Norm_GPU"]
)

# Portability
df["Portability"] = (
    0.7 * (1 - df["Norm_Weight"]) +
    0.3 * (1 - df["Norm_Screen"])
)

targets = ["Performance", "Portability"]

# =============================
# STEP 4: Train models
# =============================
os.makedirs("models", exist_ok=True)

models = {}

print("\nTraining models...\n")

for target in targets:

    print("Training:", target)

    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print("R2:", round(r2,4))
    print("MAE:", round(mae,4))

    model_path = f"models/{target}_model.pkl"
    joblib.dump(model, model_path)

    print("Saved:", model_path)
    print("----------------------")

    models[target] = model

print("\nModels training completed!")

# =============================
# STEP 5: TEST PIPELINE (AI + AHP)
# =============================

print("\n=== TEST HYBRID PIPELINE ===")

# AI scoring
df["Performance_AI"] = models["Performance"].predict(X)
df["Portability_AI"] = models["Portability"].predict(X)

df["Battery_AI"] = df["Norm_Battery"]
df["Durability_AI"] = df["Norm_Durability"]

# AHP weights example
weights = {
    "performance": 0.45,
    "portability": 0.25,
    "battery": 0.20,
    "durability": 0.10
}

# Hybrid score
df["MatchScore"] = (
    df["Performance_AI"] * weights["performance"]
    + df["Portability_AI"] * weights["portability"]
    + df["Battery_AI"] * weights["battery"]
    + df["Durability_AI"] * weights["durability"]
)

# Ranking
ranking = df.sort_values("MatchScore", ascending=False)

print("\nTop 5 laptop recommendations:\n")

print(ranking[[
    "Performance_AI",
    "Portability_AI",
    "Battery_AI",
    "Durability_AI",
    "MatchScore"
]].head(5))

print("\nHybrid DSS training + test completed successfully!")