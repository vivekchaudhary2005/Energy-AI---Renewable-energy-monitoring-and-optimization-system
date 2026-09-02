"""
============================================================
  AI-Powered Renewable Energy Management System
  FILE: model/train_model.py
  PURPOSE: Load data, train Random Forest model, save model.pkl
           Also includes fault detection & optimization logic
============================================================
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
#  STEP 1: Load Dataset
# ─────────────────────────────────────────────
def load_data(filepath="../data/dataset.csv"):
    """
    Load the solar power dataset from Kaggle.
    If file not found, generate realistic synthetic data for testing.
    """
    if os.path.exists(filepath):
        print(f"[INFO] Loading real dataset from: {filepath}")
        df = pd.read_csv(filepath)
        print(f"[INFO] Dataset shape: {df.shape}")
        print(f"[INFO] Columns: {list(df.columns)}")
        return df
    else:
        print("[WARNING] dataset.csv not found. Generating synthetic training data...")
        return generate_synthetic_data()


def generate_synthetic_data(n_samples=5000):
    """
    Generate realistic synthetic solar energy data for demo/training.
    Based on typical Indian subcontinent solar plant readings.
    """
    np.random.seed(42)

    # Hours of the day (solar generation happens 6am–6pm)
    hours = np.random.choice(range(0, 24), n_samples)

    # Solar irradiation peaks at midday
    irradiation = np.where(
        (hours >= 6) & (hours <= 18),
        np.random.uniform(0.1, 1.0, n_samples) * np.sin((hours - 6) / 12 * np.pi),
        0.0
    )

    # Temperature peaks in afternoon
    ambient_temp = 20 + 15 * np.sin((hours - 6) / 24 * np.pi) + np.random.normal(0, 3, n_samples)
    ambient_temp = np.clip(ambient_temp, 5, 48)

    # Module (panel) temp is higher than ambient
    module_temp = ambient_temp + irradiation * 20 + np.random.normal(0, 2, n_samples)

    # AC Power: depends mainly on irradiation and temperature
    # Too much heat reduces efficiency
    efficiency = 1.0 - np.clip((module_temp - 25) * 0.004, 0, 0.25)
    ac_power = irradiation * 3000 * efficiency + np.random.normal(0, 50, n_samples)
    ac_power = np.clip(ac_power, 0, 3500)

    # DC Power is slightly higher than AC
    dc_power = ac_power * 1.05 + np.random.normal(0, 20, n_samples)
    dc_power = np.clip(dc_power, 0, 4000)

    # Daily yield (cumulative)
    daily_yield = ac_power * 0.5 + np.random.normal(0, 100, n_samples)
    daily_yield = np.clip(daily_yield, 0, None)

    df = pd.DataFrame({
        'AMBIENT_TEMPERATURE': ambient_temp,
        'MODULE_TEMPERATURE': module_temp,
        'IRRADIATION': irradiation,
        'DC_POWER': dc_power,
        'DAILY_YIELD': daily_yield,
        'HOUR': hours,
        'AC_POWER': ac_power  # ← TARGET variable
    })

    print(f"[INFO] Synthetic dataset created: {df.shape}")
    return df


# ─────────────────────────────────────────────
#  STEP 2: Preprocess Data
# ─────────────────────────────────────────────
def preprocess_data(df):
    """
    Clean data, engineer features, select relevant columns.
    Returns: X (features), y (target), scaler
    """
    print("\n[INFO] Preprocessing data...")

    # --- Handle real Kaggle dataset column names ---
    # Rename columns if they come from the actual Kaggle dataset
    rename_map = {
        'AMBIENT_TEMPERATURE': 'AMBIENT_TEMPERATURE',
        'MODULE_TEMPERATURE': 'MODULE_TEMPERATURE',
        'IRRADIATION': 'IRRADIATION',
        'DC_POWER': 'DC_POWER',
        'DAILY_YIELD': 'DAILY_YIELD',
        'AC_POWER': 'AC_POWER',
    }

    # If DATE_TIME column exists (real dataset), extract hour
    if 'DATE_TIME' in df.columns:
        df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'], dayfirst=True, errors='coerce')
        df['HOUR'] = df['DATE_TIME'].dt.hour
        df['MONTH'] = df['DATE_TIME'].dt.month
        df = df.drop(columns=['DATE_TIME'], errors='ignore')
    elif 'HOUR' not in df.columns:
        df['HOUR'] = 12  # default midday if no time info

    # Drop unnecessary columns
    drop_cols = ['DATE_TIME', 'PLANT_ID', 'SOURCE_KEY', 'TOTAL_YIELD']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Drop rows with missing target
    df = df.dropna(subset=['AC_POWER'])

    # Fill remaining NaN with median
    df = df.fillna(df.median(numeric_only=True))

    # ── Feature Engineering ──
    # Ratio of DC to AC (efficiency indicator)
    if 'DC_POWER' in df.columns:
        df['EFFICIENCY'] = np.where(
            df['DC_POWER'] > 0,
            df['AC_POWER'] / df['DC_POWER'],
            0
        )

    # Temperature stress indicator (above 35°C hurts panel efficiency)
    if 'MODULE_TEMPERATURE' in df.columns:
        df['TEMP_STRESS'] = np.clip(df['MODULE_TEMPERATURE'] - 35, 0, None)

    print(f"[INFO] Features after preprocessing: {list(df.columns)}")
    print(f"[INFO] Data shape: {df.shape}")

    # ── Select feature columns ──
    feature_cols = [c for c in df.columns if c != 'AC_POWER']
    X = df[feature_cols]
    y = df['AC_POWER']

    # ── Scale features ──
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"[INFO] Training features ({len(feature_cols)}): {feature_cols}")
    return X_scaled, y, scaler, feature_cols


# ─────────────────────────────────────────────
#  STEP 3: Train Random Forest Model
# ─────────────────────────────────────────────
def train_model(X, y):
    """
    Train a Random Forest Regressor to predict AC power output.
    Returns trained model + evaluation metrics.
    """
    print("\n[INFO] Splitting data into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("[INFO] Training Random Forest model...")
    model = RandomForestRegressor(
        n_estimators=100,      # 100 decision trees
        max_depth=10,          # prevent overfitting
        min_samples_split=5,
        random_state=42,
        n_jobs=-1              # use all CPU cores
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"\n[RESULTS] Model Evaluation:")
    print(f"  Mean Absolute Error : {mae:.2f} kW")
    print(f"  R² Score            : {r2:.4f}  (1.0 = perfect)")

    return model, mae, r2


# ─────────────────────────────────────────────
#  STEP 4: Save Model
# ─────────────────────────────────────────────
def save_model(model, scaler, feature_cols, output_path="../model/model.pkl"):
    """
    Save the trained model, scaler, and feature names as a single .pkl bundle.
    The backend will load this entire bundle.
    """
    bundle = {
        'model': model,
        'scaler': scaler,
        'feature_cols': feature_cols
    }
    with open(output_path, 'wb') as f:
        pickle.dump(bundle, f)
    print(f"\n[SAVED] Model saved to: {output_path}")


# ─────────────────────────────────────────────
#  STEP 5: Energy Prediction (standalone function)
# ─────────────────────────────────────────────
def predict_energy(model_bundle, input_features: dict) -> float:
    """
    Given a dictionary of feature values, return predicted AC power in kW.

    Example input_features:
    {
        'AMBIENT_TEMPERATURE': 35.0,
        'MODULE_TEMPERATURE': 48.0,
        'IRRADIATION': 0.85,
        'DC_POWER': 2800.0,
        'DAILY_YIELD': 4200.0,
        'HOUR': 13
    }
    """
    model = model_bundle['model']
    scaler = model_bundle['scaler']
    feature_cols = model_bundle['feature_cols']

    # Build a DataFrame matching training columns
    row = {}
    for col in feature_cols:
        row[col] = input_features.get(col, 0.0)

    df_input = pd.DataFrame([row])
    X_scaled = scaler.transform(df_input)
    prediction = model.predict(X_scaled)[0]
    return max(0.0, float(prediction))


# ─────────────────────────────────────────────
#  STEP 6: Basic Fault Detection
# ─────────────────────────────────────────────
def detect_fault(input_features: dict, predicted_power: float) -> dict:
    """
    Simple rule-based fault detection logic.
    Checks for:
    - Overheating panels
    - Low efficiency
    - Zero generation during peak hours
    - Irradiation-power mismatch

    Returns a dict with fault status and message.
    """
    faults = []
    severity = "normal"  # normal | warning | critical

    ambient = input_features.get('AMBIENT_TEMPERATURE', 25)
    module_temp = input_features.get('MODULE_TEMPERATURE', 30)
    irradiation = input_features.get('IRRADIATION', 0.5)
    dc_power = input_features.get('DC_POWER', 0)
    hour = input_features.get('HOUR', 12)

    # ── Fault 1: Panel overheating ──
    if module_temp > 65:
        faults.append("Panel temperature critically high (>65°C)")
        severity = "critical"
    elif module_temp > 50:
        faults.append("Panel temperature elevated (>50°C)")
        if severity == "normal":
            severity = "warning"

    # ── Fault 2: Low efficiency during peak hours ──
    if 10 <= hour <= 15 and irradiation > 0.5 and predicted_power < 500:
        faults.append("Low power output despite high irradiation — possible soiling or shading")
        if severity == "normal":
            severity = "warning"

    # ── Fault 3: DC-AC conversion loss too high ──
    if dc_power > 100:
        efficiency = predicted_power / dc_power
        if efficiency < 0.7:
            faults.append(f"Inverter efficiency low ({efficiency:.0%}) — check inverter")
            severity = "critical"

    # ── Fault 4: No generation at peak sun ──
    if irradiation > 0.7 and predicted_power < 100:
        faults.append("Near-zero generation at high irradiation — sensor or panel failure")
        severity = "critical"

    return {
        "has_fault": len(faults) > 0,
        "severity": severity,
        "fault_messages": faults if faults else ["All systems operating normally"],
        "fault_count": len(faults)
    }


# ─────────────────────────────────────────────
#  STEP 7: Optimization Suggestion
# ─────────────────────────────────────────────
def get_optimization_suggestion(input_features: dict, predicted_power: float,
                                  consumption_kwh: float = None) -> dict:
    """
    Provide actionable recommendations based on current conditions.
    Returns a recommendation string and battery action.
    """
    hour = input_features.get('HOUR', 12)
    irradiation = input_features.get('IRRADIATION', 0.5)
    module_temp = input_features.get('MODULE_TEMPERATURE', 35)

    # Convert kW to kWh estimate (assuming 1-hour window)
    production_kwh = predicted_power / 1000.0 * 1.0

    if consumption_kwh is None:
        # Estimate average household/microgrid consumption
        consumption_kwh = 2.5 if 8 <= hour <= 22 else 0.8

    surplus = production_kwh - consumption_kwh
    battery_action = "hold"
    recommendation = ""

    if surplus > 1.0:
        battery_action = "charge"
        recommendation = (
            f"Surplus of {surplus:.1f} kWh detected. "
            "Charge battery banks and consider grid export."
        )
    elif surplus < -0.5:
        battery_action = "discharge"
        recommendation = (
            f"Deficit of {abs(surplus):.1f} kWh. "
            "Discharging battery to cover load. Reduce non-essential consumption."
        )
    else:
        battery_action = "balanced"
        recommendation = "Production and consumption are balanced. System running optimally."

    # Extra tip based on conditions
    if module_temp > 45:
        recommendation += " Consider cleaning panels to reduce heat buildup."
    if irradiation < 0.2 and 10 <= hour <= 14:
        recommendation += " Cloud cover detected — activate backup supply."

    return {
        "production_kwh": round(production_kwh, 3),
        "consumption_kwh": round(consumption_kwh, 3),
        "surplus_kwh": round(surplus, 3),
        "battery_action": battery_action,
        "recommendation": recommendation
    }


# ─────────────────────────────────────────────
#  MAIN: Run full training pipeline
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Renewable Energy ML Model — Training Pipeline")
    print("=" * 55)

    # 1. Load data
    df = load_data("../data/dataset.csv")

    # 2. Preprocess
    X, y, scaler, feature_cols = preprocess_data(df)

    # 3. Train
    model, mae, r2 = train_model(X, y)

    # 4. Save
    save_model(model, scaler, feature_cols, "../model/model.pkl")

    # 5. Quick test prediction
    print("\n[TEST] Running a sample prediction...")
    bundle = {'model': model, 'scaler': scaler, 'feature_cols': feature_cols}
    test_input = {
        'AMBIENT_TEMPERATURE': 35.0,
        'MODULE_TEMPERATURE': 48.0,
        'IRRADIATION': 0.85,
        'DC_POWER': 2800.0,
        'DAILY_YIELD': 4200.0,
        'HOUR': 13
    }
    power = predict_energy(bundle, test_input)
    print(f"  Predicted AC Power : {power:.2f} kW")

    # 6. Test fault detection
    fault = detect_fault(test_input, power)
    print(f"  Fault Status       : {fault['severity']} — {fault['fault_messages'][0]}")

    # 7. Test optimization
    opt = get_optimization_suggestion(test_input, power)
    print(f"  Battery Action     : {opt['battery_action']}")
    print(f"  Recommendation     : {opt['recommendation'][:60]}...")

    print("\n[DONE] Training complete. model.pkl is ready for backend.")
