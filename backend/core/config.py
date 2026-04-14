from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "Landslide Detection & Routing AI API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    MODEL_PATH: str = "../twentyeight.pkt"
    SPATIAL_RESOLUTION: float = 10.0
    FOREGROUND_VALUE: int = 1
    IMG_SIZE: tuple = (512, 512)
    ENCODER: str = "resnet50"

    DEFAULT_MAP_PLACE: str = "Himachal Pradesh, India"

    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ALERT_FROM_EMAIL: str = os.getenv("ALERT_FROM_EMAIL", "")

    AUTHORITY_EMAIL_1: str = os.getenv("AUTHORITY_EMAIL_1", "")
    AUTHORITY_EMAIL_2: str = os.getenv("AUTHORITY_EMAIL_2", "")
    AUTHORITY_EMAIL_3: str = os.getenv("AUTHORITY_EMAIL_3", "")
    AUTHORITY_EMAIL_4: str = os.getenv("AUTHORITY_EMAIL_4", "")
    AUTHORITY_EMAIL_5: str = os.getenv("AUTHORITY_EMAIL_5", "")
    AUTHORITY_EMAIL_6: str = os.getenv("AUTHORITY_EMAIL_6", "")
    AUTHORITY_EMAIL_7: str = os.getenv("AUTHORITY_EMAIL_7", "")
    AUTHORITY_EMAIL_8: str = os.getenv("AUTHORITY_EMAIL_8", "")
    AUTHORITY_EMAIL_9: str = os.getenv("AUTHORITY_EMAIL_9", "")
    AUTHORITY_EMAIL_10: str = os.getenv("AUTHORITY_EMAIL_10", "")
    AUTHORITY_EMAIL_11: str = os.getenv("AUTHORITY_EMAIL_11", "")
    AUTHORITY_EMAIL_12: str = os.getenv("AUTHORITY_EMAIL_12", "")

    RISK_ALERT_THRESHOLD: str = os.getenv("RISK_ALERT_THRESHOLD", "High")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "default-secret-key-change-in-production")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
