"""Configuration"""
APP_TITLE = "BRSR-Report"
DATABASE_PATH = "brsr_report.db"
DATABASE_URL = "sqlite:///" + DATABASE_PATH
APP_SECRET = "brsr_report_secret_2026"
UPLOAD_FOLDER = "evidence_uploads"
DIESEL_FACTOR = 2.68
ELECTRICITY_FACTOR = 0.82
MANHOURS_PER_PROJECT = 500000
GRADE_THRESHOLDS = {"A+": 85, "A": 70, "B": 55, "C": 40, "D": 0}

PROJECT_PORTFOLIO = [
    {"name": "Hyderabad Water Grid", "state": "Telangana", "lat": 17.385, "lng": 78.486, "value_cr": 4200, "status": "Active"},
    {"name": "Godavari Lift Irrigation", "state": "Telangana", "lat": 18.112, "lng": 79.594, "value_cr": 8500, "status": "Active"},
    {"name": "Metro Phase-3 Tunnels", "state": "Telangana", "lat": 17.423, "lng": 78.473, "value_cr": 6300, "status": "Active"},
    {"name": "Mahanadi Canal Tunnels", "state": "Odisha", "lat": 20.296, "lng": 85.824, "value_cr": 3100, "status": "Active"},
    {"name": "NH-48 Highway Package", "state": "Gujarat", "lat": 23.022, "lng": 72.571, "value_cr": 2800, "status": "Active"},
]
