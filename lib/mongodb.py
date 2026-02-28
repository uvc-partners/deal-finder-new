import pandas as pd
from pymongo import MongoClient

DB_USERNAME = "admin"
DB_PASSWORD = "UTUM123!"
connection_string = f"mongodb+srv://{DB_USERNAME}:{DB_PASSWORD}@dealfinder-db.tiw0nsq.mongodb.net/?appName=dealfinder-db"


def download_mongodb_data(db_name=None, collection_name=None, database_name=None):
    """Download all documents from a MongoDB collection as a pandas DataFrame."""
    db_name = db_name or database_name
    if db_name is None or collection_name is None:
        raise ValueError("db_name (or database_name) and collection_name are required")
    try:
        client = MongoClient(connection_string)
        db = client[db_name]
        collection = db[collection_name]
        df = pd.DataFrame(list(collection.find({})))
    finally:
        client.close()
    return df


# Backwards-compatible alias for existing code
download_data_from_mongo_db = download_mongodb_data
