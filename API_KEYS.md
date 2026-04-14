# API Keys & Configuration Template

## Quick Start

Copy this template to create your `.env` file:

```env
# Email Configuration (REQUIRED for alerts)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=your-email@gmail.com

# Authority Emails (Optional)
AUTHORITY_EMAIL_1=ddma-hamirpur@hp.gov.in
AUTHORITY_EMAIL_2=ddma-kangra@hp.gov.in
AUTHORITY_EMAIL_11=ndma@nic.in
AUTHORITY_EMAIL_12=controlroom@ndrf.gov.in
```

---

## How to Get Gmail App Password

1. Go to [Google Account → Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Go to **App Passwords** (search in settings)
4. Create new app password for "Mail"
5. Copy the 16-character password

---

## No API Keys Needed (All Free)

| Service | Status |
|--------|---------|
| Open-Meteo Weather API | Free - No key |
| Microsoft Planetary Computer | Free - No key |
| OpenStreetMap (OSMnx) | Free - No key |
| DeepLabV3+ Model | Local - No key |
| Gmail SMTP | Free - App password only |

---

## Deployment

For production, set environment variables:
```bash
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
```