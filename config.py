import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dream_project")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smart_agri_db")
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5001"))
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=True)
    TESTING = _as_bool(os.getenv("FLASK_TESTING"), default=False)


_mongo_client = None
_mongo_db = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(Config.MONGO_URI)
    return _mongo_client


def get_db():
    global _mongo_db
    if _mongo_db is None:
        _mongo_db = get_mongo_client()[Config.MONGO_DB_NAME]
    return _mongo_db
