import os
from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None


def get_db() -> Database:
    global _client
    if _client is None:
        uri = os.environ["MONGO_URI"]
        _client = MongoClient(uri)
    db_name = os.environ.get("MONGO_DB_NAME", "nie")
    return _client[db_name]
