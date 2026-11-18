"""
ScamTrace Configuration
"""
import os

# Application
APP_NAME = "SCAMTRACE"
APP_SUBTITLE = "Financial Crime Intelligence & Investigation Platform"
VERSION = "1.0.0"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "scamtrace.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports_output")

# Limits
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Disclaimers
SYNTHETIC_DATA_DISCLAIMER = (
    "⚠️ All data is synthetic and fictional. No real individuals, accounts, or transactions "
    "are implicated. This platform is a demonstration prototype only."
)
RISK_SCORE_DISCLAIMER = (
    "⚠️ Risk scores are heuristic behavioral indicators, NOT probabilities of criminal activity "
    "and do not establish guilt. All flagged accounts require human investigation."
)

# Risk thresholds (score out of 100)
RISK_THRESHOLDS = {
    "LOW": 30,
    "MEDIUM": 60,
    "HIGH": 80,
    "CRITICAL": 90,
}

# Detection parameters
DETECTION_PARAMS = {
    "velocity_high": 10,
    "velocity_critical": 20,
    "io_ratio_suspicious": 0.9,
    "withdrawal_high": 0.7,
    "withdrawal_critical": 0.9,
    "counterparties_high": 15,
    "holding_hours_low": 2,
    "large_tx_threshold": 50000,
}

# UI Colors
COLORS = {
    "background": "#0d1117",
    "sidebar": "#161b22",
    "card_bg": "#161b22",
    "card_border": "#21262d",
    "accent_blue": "#1f6feb",
    "accent_teal": "#2ea8a5",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "success": "#3fb950",
    "warning": "#d29922",
    "critical": "#f85149",
    "medium": "#58a6ff",
}
