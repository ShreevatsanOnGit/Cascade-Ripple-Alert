import os
import logging

# Load local .env file if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

class Settings:
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    
    manipal_path = os.path.join(DATA_DIR, "manipal_network.json")
    dummy_path = os.path.join(DATA_DIR, "dummy_network.json")
    default_net = manipal_path if os.path.exists(manipal_path) else dummy_path
    
    NETWORK_JSON_PATH = os.environ.get("NETWORK_JSON_PATH", default_net)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    
    # CORS Configuration
    cors_env = os.environ.get("CORS_ORIGINS", "*")
    CORS_ORIGINS = [origin.strip() for origin in cors_env.split(",")] if cors_env != "*" else ["*"]

settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
