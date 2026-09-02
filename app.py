"""
============================================================
  AI-Powered Renewable Energy Management System
  FILE: backend/app.py
  PURPOSE: Flask API server that loads model.pkl and serves
           prediction, data, and fault detection endpoints
============================================================

ENDPOINTS:
  GET  /              → health check
  POST /predict       → ML prediction for a city
  GET  /data          → city energy stats (historical-style)
  POST /fault         → fault detection analysis
  GET  /cities        → list of supported cities

HOW TO RUN:
  pip install flask flask-cors scikit-learn pandas numpy
  python app.py
  → Runs on http://localhost:5000
============================================================
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add model directory to path so we can import helper functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'model'))

# ─────────────────────────────────────────────
#  Flask App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow frontend (any origin) to call this API

# ─────────────────────────────────────────────
#  Load ML Model Bundle
# ─────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'model.pkl')
model_bundle = None

def load_model():
    """Load model.pkl into memory at startup."""
    global model_bundle
    try:
        with open(MODEL_PATH, 'rb') as f:
            model_bundle = pickle.load(f)
        print(f"[OK] Model loaded from: {MODEL_PATH}")
        print(f"[OK] Features: {model_bundle['feature_cols']}")
    except FileNotFoundError:
        print(f"[WARNING] model.pkl not found at {MODEL_PATH}")
        print("[WARNING] Run model/train_model.py first to generate model.pkl")
        model_bundle = None


# ─────────────────────────────────────────────
#  City Feature Map
#  Maps city name → approximate real-world
#  solar/weather features for that region
# ─────────────────────────────────────────────
CITY_FEATURES = {
    # North India — hot, high irradiation
    "delhi": {
        "AMBIENT_TEMPERATURE": 38.0, "MODULE_TEMPERATURE": 52.0,
        "IRRADIATION": 0.82, "DC_POWER": 2750.0,
        "DAILY_YIELD": 5200.0, "HOUR": 13,
        "region": "North India", "climate": "Semi-arid",
        "wind_speed": 3.2, "cloud_cover": 0.15
    },
    "una": {
        "AMBIENT_TEMPERATURE": 40.0, "MODULE_TEMPERATURE": 55.0,
        "IRRADIATION": 0.88, "DC_POWER": 2900.0,
        "DAILY_YIELD": 5600.0, "HOUR": 13,
        "region": "Himachal Pradesh", "climate": "Hot semi-arid",
        "wind_speed": 2.8, "cloud_cover": 0.10
    },
    "chandigarh": {
        "AMBIENT_TEMPERATURE": 36.0, "MODULE_TEMPERATURE": 50.0,
        "IRRADIATION": 0.79, "DC_POWER": 2600.0,
        "DAILY_YIELD": 5000.0, "HOUR": 13,
        "region": "Punjab/Haryana", "climate": "Semi-arid",
        "wind_speed": 3.5, "cloud_cover": 0.20
    },
    "amritsar": {
        "AMBIENT_TEMPERATURE": 37.0, "MODULE_TEMPERATURE": 51.0,
        "IRRADIATION": 0.80, "DC_POWER": 2650.0,
        "DAILY_YIELD": 5100.0, "HOUR": 13,
        "region": "Punjab", "climate": "Semi-arid",
        "wind_speed": 4.0, "cloud_cover": 0.18
    },
    # West India — moderate, coastal
    "mumbai": {
        "AMBIENT_TEMPERATURE": 30.0, "MODULE_TEMPERATURE": 44.0,
        "IRRADIATION": 0.72, "DC_POWER": 2400.0,
        "DAILY_YIELD": 4600.0, "HOUR": 13,
        "region": "West India", "climate": "Tropical wet-dry",
        "wind_speed": 5.1, "cloud_cover": 0.35
    },
    "pune": {
        "AMBIENT_TEMPERATURE": 28.0, "MODULE_TEMPERATURE": 42.0,
        "IRRADIATION": 0.75, "DC_POWER": 2500.0,
        "DAILY_YIELD": 4800.0, "HOUR": 13,
        "region": "Maharashtra", "climate": "Tropical",
        "wind_speed": 4.2, "cloud_cover": 0.25
    },
    "jaipur": {
        "AMBIENT_TEMPERATURE": 42.0, "MODULE_TEMPERATURE": 58.0,
        "IRRADIATION": 0.91, "DC_POWER": 3000.0,
        "DAILY_YIELD": 5800.0, "HOUR": 13,
        "region": "Rajasthan", "climate": "Hot desert",
        "wind_speed": 4.5, "cloud_cover": 0.08
    },
    # South India — high irradiation year-round
    "bangalore": {
        "AMBIENT_TEMPERATURE": 26.0, "MODULE_TEMPERATURE": 40.0,
        "IRRADIATION": 0.77, "DC_POWER": 2550.0,
        "DAILY_YIELD": 4900.0, "HOUR": 13,
        "region": "South India", "climate": "Tropical savanna",
        "wind_speed": 3.8, "cloud_cover": 0.22
    },
    "hyderabad": {
        "AMBIENT_TEMPERATURE": 32.0, "MODULE_TEMPERATURE": 46.0,
        "IRRADIATION": 0.84, "DC_POWER": 2780.0,
        "DAILY_YIELD": 5300.0, "HOUR": 13,
        "region": "Telangana", "climate": "Semi-arid",
        "wind_speed": 3.5, "cloud_cover": 0.18
    },
    "chennai": {
        "AMBIENT_TEMPERATURE": 33.0, "MODULE_TEMPERATURE": 47.0,
        "IRRADIATION": 0.80, "DC_POWER": 2650.0,
        "DAILY_YIELD": 5100.0, "HOUR": 13,
        "region": "Tamil Nadu", "climate": "Tropical wet-dry",
        "wind_speed": 5.5, "cloud_cover": 0.30
    },
    # East India
    "kolkata": {
        "AMBIENT_TEMPERATURE": 30.0, "MODULE_TEMPERATURE": 44.0,
        "IRRADIATION": 0.68, "DC_POWER": 2250.0,
        "DAILY_YIELD": 4300.0, "HOUR": 13,
        "region": "East India", "climate": "Tropical wet-dry",
        "wind_speed": 4.2, "cloud_cover": 0.40
    },
    "bhopal": {
        "AMBIENT_TEMPERATURE": 36.0, "MODULE_TEMPERATURE": 50.0,
        "IRRADIATION": 0.83, "DC_POWER": 2750.0,
        "DAILY_YIELD": 5250.0, "HOUR": 13,
        "region": "Madhya Pradesh", "climate": "Tropical",
        "wind_speed": 3.0, "cloud_cover": 0.20
    },
    # Default fallback
    "default": {
        "AMBIENT_TEMPERATURE": 30.0, "MODULE_TEMPERATURE": 44.0,
        "IRRADIATION": 0.75, "DC_POWER": 2500.0,
        "DAILY_YIELD": 4800.0, "HOUR": 13,
        "region": "India", "climate": "Tropical",
        "wind_speed": 3.5, "cloud_cover": 0.25
    }
}


def get_city_features(city_name: str) -> dict:
    """
    Look up city features. Case-insensitive.
    Falls back to 'default' if city not found.
    """
    key = city_name.strip().lower()
    if key in CITY_FEATURES:
        return CITY_FEATURES[key].copy()
    # Partial match (e.g., "New Delhi" → "delhi")
    for city_key in CITY_FEATURES:
        if city_key in key or key in city_key:
            return CITY_FEATURES[city_key].copy()
    return CITY_FEATURES["default"].copy()


# ─────────────────────────────────────────────
#  Helper: Run ML Prediction
# ─────────────────────────────────────────────
def run_prediction(features: dict) -> float:
    """Use loaded model to predict AC power (kW) from feature dict."""
    if model_bundle is None:
        # Fallback: rule-based estimate when model not loaded
        irradiation = features.get('IRRADIATION', 0.5)
        temp = features.get('AMBIENT_TEMPERATURE', 30)
        efficiency = max(0.5, 1.0 - (temp - 25) * 0.005)
        return max(0.0, irradiation * 3200 * efficiency)

    model = model_bundle['model']
    scaler = model_bundle['scaler']
    feature_cols = model_bundle['feature_cols']

    # Build feature row, compute EFFICIENCY and TEMP_STRESS if needed
    dc = features.get('DC_POWER', 0)
    row = {}
    for col in feature_cols:
        if col == 'EFFICIENCY':
            row[col] = features.get('AC_POWER', features.get('DC_POWER', 1000)) / dc if dc > 0 else 0.9
        elif col == 'TEMP_STRESS':
            row[col] = max(0, features.get('MODULE_TEMPERATURE', 35) - 35)
        else:
            row[col] = features.get(col, 0.0)

    df_in = pd.DataFrame([row])
    X_scaled = scaler.transform(df_in)
    prediction = model.predict(X_scaled)[0]
    return float(max(0.0, prediction))


# ─────────────────────────────────────────────
#  Helper: Fault Detection Logic
# ─────────────────────────────────────────────
def check_faults(features: dict, predicted_power: float) -> dict:
    faults = []
    severity = "normal"

    module_temp = features.get('MODULE_TEMPERATURE', 35)
    irradiation = features.get('IRRADIATION', 0.5)
    dc_power = features.get('DC_POWER', 1000)
    hour = features.get('HOUR', 12)

    if module_temp > 65:
        faults.append("Critical: Panel temperature >65°C — risk of damage")
        severity = "critical"
    elif module_temp > 52:
        faults.append("Warning: Panel overheating (>52°C) — efficiency reduced")
        severity = "warning"

    if 10 <= hour <= 15 and irradiation > 0.6 and predicted_power < 500:
        faults.append("Warning: Low output during peak irradiation — possible soiling")
        if severity == "normal":
            severity = "warning"

    if dc_power > 100:
        ratio = predicted_power / dc_power
        if ratio < 0.72:
            faults.append(f"Critical: Inverter efficiency {ratio:.0%} — check inverter")
            severity = "critical"

    if irradiation > 0.75 and predicted_power < 200:
        faults.append("Critical: Near-zero output at high irradiation — sensor failure")
        severity = "critical"

    return {
        "has_fault": len(faults) > 0,
        "severity": severity,
        "fault_messages": faults if faults else ["All systems operating normally"],
        "fault_count": len(faults)
    }


# ─────────────────────────────────────────────
#  Helper: Optimization Recommendation
# ─────────────────────────────────────────────
def get_recommendation(features: dict, predicted_power: float) -> dict:
    hour = features.get('HOUR', 12)
    irradiation = features.get('IRRADIATION', 0.5)
    module_temp = features.get('MODULE_TEMPERATURE', 35)

    production_kwh = predicted_power / 1000.0
    consumption_kwh = 2.5 if 8 <= hour <= 22 else 0.8
    surplus = production_kwh - consumption_kwh
    battery_action = "hold"
    rec = ""

    if surplus > 1.0:
        battery_action = "charge"
        rec = f"Surplus {surplus:.1f} kWh — charging battery banks."
    elif surplus < -0.5:
        battery_action = "discharge"
        rec = f"Deficit {abs(surplus):.1f} kWh — discharging batteries."
    else:
        battery_action = "balanced"
        rec = "Production balanced with consumption."

    if module_temp > 45:
        rec += " Clean panels to reduce heat buildup."
    if irradiation < 0.2 and 10 <= hour <= 14:
        rec += " Low irradiation — activate backup supply."

    return {
        "production_kwh": round(production_kwh, 2),
        "consumption_kwh": round(consumption_kwh, 2),
        "surplus_kwh": round(surplus, 2),
        "battery_action": battery_action,
        "recommendation": rec
    }


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "online",
        "message": "Renewable Energy Management API is running",
        "model_loaded": model_bundle is not None,
        "version": "1.0.0"
    })


@app.route("/cities", methods=["GET"])
def list_cities():
    """Return the list of supported cities."""
    cities = [c for c in CITY_FEATURES.keys() if c != "default"]
    return jsonify({"cities": cities, "count": len(cities)})


@app.route("/predict", methods=["POST"])
def predict():
    """
    Main prediction endpoint.

    INPUT (JSON):
    { "city": "Delhi" }

    OUTPUT (JSON):
    {
      "city": "Delhi",
      "predicted_power_kw": 2672.3,
      "daily_yield_kwh": 5200,
      "consumption_kwh": 2.5,
      "surplus_kwh": 0.17,
      "battery_action": "balanced",
      "recommendation": "...",
      "fault": { "has_fault": false, "severity": "normal", ... },
      "features": { ... city weather features ... }
    }
    """
    try:
        data = request.get_json(force=True)
        city = data.get("city", "default")

        # 1. Get city features
        features = get_city_features(city)

        # 2. Run ML prediction
        predicted_power = run_prediction(features)

        # 3. Fault detection
        fault = check_faults(features, predicted_power)

        # 4. Optimization recommendation
        opt = get_recommendation(features, predicted_power)

        return jsonify({
            "status": "success",
            "city": city.title(),
            "predicted_power_kw": round(predicted_power, 2),
            "daily_yield_kwh": features.get("DAILY_YIELD", 5000),
            "ambient_temperature": features.get("AMBIENT_TEMPERATURE"),
            "module_temperature": features.get("MODULE_TEMPERATURE"),
            "irradiation": features.get("IRRADIATION"),
            "wind_speed": features.get("wind_speed", 3.5),
            "cloud_cover": features.get("cloud_cover", 0.2),
            "region": features.get("region", "India"),
            "climate": features.get("climate", "Tropical"),
            "consumption_kwh": opt["consumption_kwh"],
            "production_kwh": opt["production_kwh"],
            "surplus_kwh": opt["surplus_kwh"],
            "battery_action": opt["battery_action"],
            "recommendation": opt["recommendation"],
            "fault": fault,
            "features_used": {
                k: v for k, v in features.items()
                if k in ["AMBIENT_TEMPERATURE", "IRRADIATION", "MODULE_TEMPERATURE"]
            }
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/data", methods=["GET"])
def get_data():
    """
    Return 7-day simulated historical energy data for a city.
    Used for charting trends on the dashboard.

    QUERY PARAMS: ?city=Delhi
    """
    city = request.args.get("city", "default")
    features = get_city_features(city)

    base_irr = features.get("IRRADIATION", 0.75)
    base_temp = features.get("AMBIENT_TEMPERATURE", 30)

    # Generate 7 days of daily readings
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    history = []
    rng = np.random.default_rng(seed=42)

    for i, day in enumerate(days):
        # Slight variation per day
        irr = base_irr * rng.uniform(0.85, 1.1)
        temp = base_temp + rng.uniform(-3, 4)
        eff = max(0.6, 1.0 - (temp - 25) * 0.004)
        production = round(irr * 3000 * eff * rng.uniform(0.9, 1.05), 1)
        consumption = round(rng.uniform(1800, 2800), 1)
        history.append({
            "day": day,
            "production_kw": production,
            "consumption_kw": consumption,
            "irradiation": round(float(irr), 3),
            "temperature": round(float(temp), 1)
        })

    return jsonify({
        "status": "success",
        "city": city.title(),
        "history": history,
        "region": features.get("region", "India")
    })


@app.route("/fault", methods=["POST"])
def fault_check():
    """
    Fault detection endpoint.

    INPUT: { "city": "Jaipur", "predicted_power": 2500 }
    OUTPUT: fault analysis dict
    """
    try:
        data = request.get_json(force=True)
        city = data.get("city", "default")
        predicted_power = data.get("predicted_power", 1000)

        features = get_city_features(city)
        fault = check_faults(features, predicted_power)

        return jsonify({
            "status": "success",
            "city": city.title(),
            **fault
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  Start Server
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  Renewable Energy API Server")
    print("=" * 50)
    load_model()
    print("[INFO] Starting Flask server on http://localhost:5000")
    print("[INFO] Press CTRL+C to stop\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
