import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
