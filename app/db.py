import os
from datetime import datetime, timezone
import google.cloud.firestore

db = google.cloud.firestore.Client(project=os.environ["GCP_PROJECT"])

def get_user(username: str) -> dict | None:
    username = username.lower()
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else None

def create_user(username: str, email: str, password_hash: str, is_admin=False, must_change_password=True):
    username = username.lower()
    user_data = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "is_admin": is_admin,
        "created_at": datetime.now(timezone.utc),
        "must_change_password": must_change_password
    }
    db.collection("users").document(username).set(user_data)

def delete_user(username: str):
    username = username.lower()
    db.collection("users").document(username).delete()

def list_users() -> list[dict]:
    docs = db.collection("users").order_by("created_at").stream()
    return [doc.to_dict() for doc in docs]