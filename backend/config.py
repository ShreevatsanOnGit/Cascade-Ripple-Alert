import os
import logging

class Settings:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
    NETWORK_JSON_PATH = os.environ.get("NETWORK_JSON_PATH", os.path.join(DATA_DIR, "dummy_network.json"))
    
    # CORS Configuration
    # Example: "http://localhost:3000,http://localhost:8080"
    cors_env = os.environ.get("CORS_ORIGINS", "*")
    CORS_ORIGINS = [origin.strip() for origin in cors_env.split(",")] if cors_env != "*" else ["*"]

settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
