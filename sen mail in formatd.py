import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load credentials securely from .env
load_dotenv()
SMTP_USER = os.getenv("SMTP_USER", "abdelrhmannaser06@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

html_content = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Retro Password Email Preview</title>
</head>
<body style="background:#111;padding:30px;font-family: 'Courier New', Courier, monospace;">
<div style="background: linear-gradient(180deg,#001100 0%, #000 60%);
            color: #bfffbf; font-family: 'Courier New', Courier, monospace;
            padding: 22px; border-radius: 10px; border: 2px solid rgba(0,255,120,0.18);
            box-shadow: 0 0 26px rgba(0,255,120,0.10), inset 0 0 40px rgba(0,20,0,0.6);
            max-width:720px; line-height:1.45; font-size:14px;
            background-image: repeating-linear-gradient(transparent, transparent 6px, rgba(0,8,0,0.12) 7px);">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div style="display:flex; gap:6px; align-items:center;">
        <span style="width:12px; height:12px; border-radius:50%; background:radial-gradient(circle at 30% 30%, #cfffaa, #00ff66); box-shadow:0 0 10px rgba(0,255,100,0.9), inset 0 -2px 6px rgba(0,0,0,0.25); border:1px solid rgba(0,255,100,0.25);"></span>
        <span style="width:12px; height:12px; border-radius:50%; background:linear-gradient(#88ff88,#00cc44); box-shadow:0 0 6px rgba(0,200,80,0.55); border:1px solid rgba(0,255,100,0.12);"></span>
        </div>

        <strong style="letter-spacing:1px; color:#eaffdf; font-size:13px;">SYSTEM — ACCESS LOG</strong>
        <span style="flex:1; text-align:right; font-size:12px; color:#bfffbf; opacity:0.9;">PASSWORD RECOVERY</span>
    </div>

    <pre style="margin:0; white-space:pre-wrap; padding:10px 12px; background: linear-gradient(180deg, rgba(0,16,0,0.12), transparent);
                border-radius:8px; border:1px solid rgba(0,255,120,0.06);
                box-shadow: inset 0 -10px 40px rgba(0,0,0,0.55); font-size:14px;">
&gt;&gt;&gt; SYSTEM ACCESS GRANTED
&gt;&gt;&gt; INITIATING PASSWORD RECOVERY PROTOCOL...
--------------------------------------------------
USER_ID: you@example.com
STATUS: PASSWORD_RESET_REQUESTED

SECRET_CODE: <span style="display:inline-block; padding:8px 12px; border-radius:10px;
                                background: linear-gradient(180deg,#e6ffd8,#c8ffb0);
                                color:#002200; font-weight:900; letter-spacing:3px; font-size:16px;
                                box-shadow: 0 6px 18px rgba(0,255,100,0.20), 0 0 24px rgba(0,255,120,0.18);
                                text-shadow:
                                0 0 18px rgba(0,255,90,0.45),
                                0 0 6px rgba(0,120,0,0.25);
                                border: 1px solid rgba(0,255,80,0.35);">A1B2-C3</span>

EXPIRES_IN: 15 MINUTES
--------------------------------------------------
&gt;&gt;&gt; WARNING: IF YOU DID NOT REQUEST THIS, DISREGARD AND CONTACT SYS_ADMIN.
&gt;&gt;&gt; END OF LINE.
    </pre>

    <div style="margin-top:12px; font-size:12px; color:#9ff59f; opacity:0.95;">
        <em>Note:</em> This is an automated message — keep the code confidential.
    </div>
</div>
</body>
</html>
"""

if not SMTP_PASSWORD:
    print("Warning: SMTP_PASSWORD is not set in .env. Please configure it.")
    exit(1)

msg = MIMEText(html_content, "html")
msg["Subject"] = "System Password Recovery"
msg["From"] = SMTP_USER
msg["To"] = SMTP_USER

server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
server.starttls()
server.login(SMTP_USER, SMTP_PASSWORD)
server.send_message(msg)
server.quit()
