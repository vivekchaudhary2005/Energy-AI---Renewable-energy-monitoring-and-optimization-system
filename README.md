# Energy-AI---Renewable-energy-monitoring-and-optimization-system
EnergyAI an AI-powered microgrid energy dashboard for Indian cities. It combines real-time weather (Open-Meteo API) with physics-based NOCT solar prediction model to forecast hourly power output, track battery/energy balance, detect system faults via anomaly detection, and generate actionable AI recommendations through live monitoring and reports.
🌍 Overview

EnergyAI is a single-page dashboard (vanilla HTML/CSS/JS) backed by a Flask API and a scikit-learn Random Forest model. Select any of the supported Indian cities and the app returns:

Predicted AC power output (kW) from the ML model
Daily energy yield, production vs. consumption, and surplus/deficit
Battery action recommendation (charge / discharge / hold)
Rule-based fault detection (overheating panels, low output, inverter issues, sensor failure)
A 7-day production/consumption trend for charting

If the Flask backend is unreachable, the frontend automatically falls back to a local, deterministic data-simulation engine so the UI never breaks.

✨ Features
📊 Live Monitor

Predicted power, consumption, daily yield, and temperature at a glance, plus a 7-day trend chart and energy balance donut (Chart.js).

🌦️ Weather / City Profiles

Each supported city has a hand-tuned weather/solar profile (ambient temp, module temp, irradiation, wind speed, cloud cover, region, climate) used as input to the prediction model.

🔋 Energy Forecast

Hourly-style production breakdown and production split (used vs. battery-stored), derived from the model's output.

🛠️ Fault Detection

Rule-based checks for:

Panel overheating (module temperature thresholds)
Low output during peak irradiation hours (possible soiling/shading)
Poor inverter efficiency (predicted output vs. DC power ratio)
Near-zero output despite high irradiation (sensor/panel failure)
📄 Reports & Recommendations

Consolidated summary with an AI-style recommendation (e.g. "Deficit 2.47 kWh — discharging batteries. Clean panels to reduce heat buildup.").

🛟 Offline Fallback

script.js includes a full fallback data engine (getFallbackData, getFallbackHistory) that mirrors the backend's logic in JavaScript, using deterministic pseudo-random variation — so the dashboard is demoable even without the Flask server running.

🧠 Machine Learning Model
Aspect	Details
Algorithm	RandomForestRegressor (scikit-learn) — 100 trees, max depth 10
Target	AC_POWER (predicted solar output in kW)
Features	Ambient temperature, module temperature, irradiation, DC power, daily yield, hour, plus engineered EFFICIENCY and TEMP_STRESS
Preprocessing	StandardScaler feature scaling, median imputation for missing values
Training data	Solar Power Generation Dataset (Kaggle) — falls back to a physics-informed synthetic dataset generator if data/dataset.csv isn't present
Evaluation	Mean Absolute Error (MAE) and R² score, printed after training
Output	Serialized to model/model.pkl (model + scaler + feature list bundle)

train_model.py also contains standalone predict_energy(), detect_fault(), and get_optimization_suggestion() helper functions used to validate the pipeline outside the API.

🖥️ Tech Stack
Frontend: Vanilla HTML, CSS, JavaScript — no framework, Chart.js for charts, Space Grotesk / JetBrains Mono fonts
Backend: Flask + Flask-CORS (Python)
ML: scikit-learn (RandomForestRegressor), pandas, NumPy
Model persistence: pickle (model.pkl)
📁 Project Structure
energyai/
├── backend/
│   └── app.py              # Flask API server
├── model/
│   ├── train_model.py      # Data loading, preprocessing, training, save model.pkl
│   └── model.pkl           # Generated after training (not committed)
├── data/
│   └── dataset.csv         # Kaggle solar power dataset (optional — synthetic data used if absent)
├── index.html               # Dashboard UI
├── script.js                 # API calls, fallback engine, charts, UI logic
├── style.css                 # Dashboard styling
└── README.md
🚀 Getting Started
Prerequisites
Python 3.10+
pip
1. Install backend dependencies
bash
pip install flask flask-cors scikit-learn pandas numpy
2. Train the model
bash
cd model
python train_model.py

This loads ../data/dataset.csv if present (otherwise generates synthetic training data), trains the Random Forest model, prints MAE/R² metrics, and saves model.pkl to the model/ folder.

3. Run the API server
bash
cd backend
python app.py

The server starts at http://localhost:5000 and loads model.pkl on startup. If the model file isn't found, /predict falls back to a simple rule-based estimate.

4. Open the dashboard

Open index.html directly in your browser (or serve it with any static file server). By default it points to http://localhost:5000 as the API base — configurable from the Settings panel in the UI.

🔌 API Reference
Method	Endpoint	Description
GET	/	Health check — returns API status and whether the model is loaded
GET	/cities	List of supported cities
POST	/predict	Main prediction endpoint — body: { "city": "Delhi" }
GET	/data?city=Delhi	7-day simulated historical production/consumption data for charting
POST	/fault	Fault detection — body: { "city": "Jaipur", "predicted_power": 2500 }

Example /predict response:

json
{
  "status": "success",
  "city": "Delhi",
  "predicted_power_kw": 2672.3,
  "daily_yield_kwh": 5200,
  "consumption_kwh": 2.5,
  "surplus_kwh": 0.17,
  "battery_action": "balanced",
  "recommendation": "Production balanced with consumption.",
  "fault": { "has_fault": false, "severity": "normal", "fault_messages": ["All systems operating normally"] }
}
Supported cities

Delhi, Una, Chandigarh, Amritsar, Mumbai, Pune, Jaipur, Bangalore, Hyderabad, Chennai, Kolkata, Bhopal (plus a default fallback profile for unlisted cities).

🗺️ Roadmap
 Replace static per-city weather profiles with a live weather API integration
 Persist historical data instead of simulating it per request
 Export reports as PDF
 User authentication for multiple site profiles
 Push notifications for fault alerts
🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change, then submit a pull request.

Fork the repo
Create a feature branch (git checkout -b feature/your-feature)
Commit your changes
Push and open a PR
📜 License

This project is licensed under the MIT License.

🙏 Acknowledgements
Kaggle Solar Power Generation dataset for model training/validation
Chart.js for dashboard visualizations
