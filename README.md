# CausalGuard-Edge

### Ubiquitous Edge-AI for Real-Time Pedestrian–Vehicle Near-Miss Detection and Causal Risk Analysis

**CausalGuard-Edge** is an Edge-AI-based research prototype designed to detect potentially dangerous pedestrian–vehicle interactions from traffic videos, assess near-miss risks and investigate contributing factors through causal and counterfactual analysis.

The project combines computer vision, multi-object tracking, trajectory-based safety assessment and a proposed decoupled dual-path architecture to support proactive pedestrian-safety monitoring.

---

## 1. Project Overview

Pedestrian–vehicle conflicts can develop rapidly, making it important to identify potentially dangerous interactions and assess their associated risks.

CausalGuard-Edge aims to address this challenge through a video-based framework that:

- Detects pedestrians and vehicles in recorded traffic videos.
- Tracks road users across video frames.
- Extracts object trajectories and motion information.
- Assesses interaction risk using surrogate safety indicators.
- Identifies potential near-miss events.
- Investigates contributing factors using Structural Causal Models (SCMs).
- Evaluates alternative scenarios using counterfactual analysis.
- Provides an interactive dashboard for visualising results.

The system is intended as a research and decision-support prototype, not an autonomous vehicle-control system.

## 2. System Architecture

The proposed architecture consists of a video-processing pipeline followed by two independent processing paths.

### Video Processing Pipeline

1. Recorded traffic video input.
2. YOLO-based object detection.
3. ByteTrack multi-object tracking.
4. Trajectory extraction.
5. Motion and interaction risk assessment.
6. Near-miss event identification.

### Decoupled Dual-Path Architecture

**Fast Safety Path – Real-Time**

Responsible for immediate risk evaluation and warning generation.

- Risk-level evaluation.
- Warning generation.
- Planned MQTT communication.
- Planned ESP32 integration.
- LED and/or speaker alerts.

**Diagnostic Path – Asynchronous**

Responsible for detailed event-level analysis.

- Event and trajectory data collection.
- Structural Causal Model development.
- Counterfactual analysis.
- Contributing-factor investigation.
- Alternative-scenario evaluation.

The separation is intended to prevent computationally intensive diagnostics from delaying immediate safety warnings.

## 3. Technologies Used

| Component                 | Technology          |
| ------------------------- | ------------------- |
| Programming Language      | Python              |
| Object Detection          | YOLO (Ultralytics)  |
| Multi-Object Tracking     | ByteTrack           |
| Video Processing          | OpenCV              |
| Data Processing           | Pandas, NumPy       |
| Dashboard                 | Streamlit           |
| Data Visualisation        | Plotly              |
| Database                  | SQLite              |
| Communication (planned)   | MQTT                |
| Hardware Alerts (planned) | ESP32, LED, Speaker |

## 4. Key Features

### Implemented

- YOLO-based object detection.
- ByteTrack-based multi-object tracking.
- Recorded-video processing.
- Annotated video generation.
- Detection and tracking data storage.
- Interactive Streamlit dashboard.
- Initial trajectory and near-miss metric functionality.

### Under Development

- Trajectory-based motion analysis.
- TTC, PET and CPA-based risk assessment.
- Near-miss classification and validation.
- Structural Causal Model-based analysis.
- Counterfactual scenario analysis.

### Planned

- Fully decoupled fast safety and diagnostic paths.
- MQTT-based communication.
- ESP32-based physical warning mechanism.
- LED and speaker alerts.
- Complete end-to-end system integration.
- Performance and reliability evaluation.

## 5. Near-Miss Risk Assessment

The project investigates surrogate safety measures to assess potentially hazardous pedestrian–vehicle interactions.

| Metric | Description                                                                                                      |
| ------ | ---------------------------------------------------------------------------------------------------------------- |
| TTC    | Time-to-Collision – estimates the time to a potential collision under specified motion assumptions.              |
| PET    | Post-Encroachment Time – measures the time difference between road users passing through a shared conflict area. |
| CPA    | Closest Point of Approach – estimates the minimum separation between projected trajectories.                     |

These indicators support interaction-risk assessment but do not independently establish that a collision will occur.

## 6. Causal and Counterfactual Analysis

The diagnostic component aims to investigate why a detected interaction may have become hazardous.

Structural Causal Models are intended to represent relationships among relevant variables, while counterfactual analysis examines hypothetical alternatives.

Example scenarios include:

- What if the vehicle had travelled at a lower speed?
- What if braking had started earlier?
- How might a change in pedestrian movement have affected the estimated interaction risk?

Counterfactual outputs are model-based estimates and depend on the assumptions and quality of the causal model.

## 7. Project Structure

```text
CausalGuard-Edge/
│
├── .streamlit/       # Streamlit configuration
│
├── app/              # Dashboard, video processing and application pages
│   └── pages/        # Video, causal, counterfactual and alert settings
│
├── docs/             # Experiment documentation and reports
│
├── evidence/         # Dataset, training, validation and testing evidence
│
├── tests/            # Application and metric testing
│
├── tools/            # Validation, annotation audit and analysis scripts
│
├── training/         # Algorithm comparison resources
│
├── app.py            # Application entry point
├── alerting.py       # Alert management
├── active_video.py   # Active video management
├── video_library.py  # Video library management
├── navigation.py     # Application navigation
├── style.py          # UI styling
│
├── requirements.txt  # Python dependencies
├── packages.txt      # Additional system packages
└── .gitignore
```

The repository is organised into application modules, experimental documentation, supporting evidence, testing resources and development tools.

## 8. Installation and Setup

### Prerequisites

- Python 3.10 or a compatible version supported by the installed dependencies.
- Git.
- Visual Studio Code or another Python IDE.
- NVIDIA GPU is optional; CPU execution may be slower.

### Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
streamlit run app.py --server.port 8502
```

Open the dashboard in your browser:

```text
http://localhost:8502
```

**Note:** These commands assume the repository retains the documented `app.py` entry point and Streamlit configuration. Verify them against the current repository before publishing.

## 9. Testing

The project includes unit tests for near-miss metrics and related calculations.

To run the near-miss metric tests:

```bash
python -m unittest tests.test_near_miss_metrics -v
```

Additional testing is required to establish complete pipeline reliability, risk-classification accuracy and real-time performance.

## 10. Current Development Status

| Module                          | Status                           |
| ------------------------------- | -------------------------------- |
| YOLO Object Detection           | Implemented                      |
| ByteTrack Tracking              | Implemented                      |
| Video Processing                | Implemented                      |
| Interactive Dashboard           | Available                        |
| Trajectory and Risk Assessment  | Under development and validation |
| Causal Analysis                 | Under development                |
| Counterfactual Analysis         | Under development                |
| Decoupled Dual-Path Integration | Proposed                         |
| MQTT Communication              | Pending                          |
| ESP32 Hardware Alerts           | Pending                          |
| Complete System Evaluation      | Pending                          |

## 11. Current Limitations

- Detection and tracking accuracy may be affected by occlusion, missed detections and ID switches.
- Handheld and varying-viewpoint videos introduce camera-motion and perspective challenges.
- Pixel-based trajectories do not automatically provide accurate real-world distances or speeds without suitable calibration.
- TTC and PET estimates depend on trajectory quality and their underlying assumptions.
- Causal and counterfactual conclusions depend on the validity of the model and its assumptions.
- MQTT and ESP32 hardware alerts have not yet been fully integrated.
- Real-world deployment and large-scale validation remain future work.

## 12. Expected Outcome

The expected outcome is an evaluated pedestrian–vehicle safety monitoring prototype that combines:

- Video-based road-user detection and tracking.
- Trajectory-derived near-miss risk assessment.
- Timely safety warning generation.
- Event-level causal diagnostics.
- Counterfactual scenario analysis.
- Interactive visualisation of detected events and risk information.

The project aims to support more interpretable and proactive pedestrian-safety monitoring.

## 13. Research and Development

CausalGuard-Edge is developed as an undergraduate research and engineering project exploring the combination of Edge AI, computer vision, surrogate safety measures and causal reasoning for pedestrian–vehicle safety analysis.

---

**Project:** CausalGuard-Edge
**Focus:** Edge AI | Computer Vision | Traffic Safety | Causal AI | Counterfactual Analysis
**Application:** Pedestrian–Vehicle Near-Miss Detection and Risk Analysis
