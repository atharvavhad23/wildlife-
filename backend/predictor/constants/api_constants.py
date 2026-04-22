"""
API response and validation constants.
"""

# ── ERROR MESSAGES ──────────────────────────────────────────────────
ERROR_INVALID_INPUT = "Invalid input parameters"
ERROR_MODEL_NOT_LOADED = "Model not yet trained"
ERROR_FILE_NOT_FOUND = "Data file not found"
ERROR_PROCESSING_FAILED = "Error processing request"
ERROR_OTP_EXPIRED = "OTP expired or not found. Request a new code."
ERROR_INVALID_OTP = "Invalid OTP code."
ERROR_EMAIL_INVALID = "Valid email is required."
ERROR_SMTP_NOT_CONFIGURED = "Project email SMTP is not configured on server."

# ── SUCCESS MESSAGES ────────────────────────────────────────────────
SUCCESS_OTP_SENT = "OTP sent to email."
SUCCESS_VERIFIED = "OTP verified successfully."

# ── CATEGORIES ──────────────────────────────────────────────────────
VALID_CATEGORIES = ['animals', 'birds', 'insects', 'plants']

# ── RESPONSE STATUS CODES ───────────────────────────────────────────
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500

# ── PREDICTION RESULT KEYS ──────────────────────────────────────────
RESULT_KEYS = {
    'prediction': 'prediction',
    'risk_level': 'risk_level',
    'status': 'status',
    'recommendation': 'recommendation',
    'trend': 'trend',
    'percentage_change': 'percentage_change',
    'environmental_data': 'environmental_data',
    'input_data': 'input_data',
    'model_info': 'model_info',
}

# ── GALLERY PAGINATION ──────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
