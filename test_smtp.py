import os
from pathlib import Path
from email.message import EmailMessage
import smtplib

BASE_DIR = Path(__file__).resolve().parent

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value

_load_env_file(BASE_DIR / '.env')

EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

print(f"Testing SMTP with {EMAIL_HOST}:{EMAIL_PORT} as {EMAIL_HOST_USER}")

msg = EmailMessage()
msg.set_content("This is a test email from the Wildlife Conserve project.")
msg['Subject'] = "Test Email"
msg['From'] = EMAIL_HOST_USER
msg['To'] = EMAIL_HOST_USER

try:
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.send_message(msg)
    print("SMTP test successful!")
except Exception as e:
    print(f"SMTP test failed: {e}")
