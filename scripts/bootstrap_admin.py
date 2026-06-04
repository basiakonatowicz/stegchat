import sys
import os
import getpass
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import get_user, create_user
from app.auth import hash_password

def main():
    if len(sys.argv) < 3:
        email = input("Podaj email administratora: ")
        password = getpass.getpass("Podaj hasło administratora: ")
    else:
        email = sys.argv[1]
        password = sys.argv[2]

    if "@" not in email:
        print("Błąd: Niepoprawny adres email.")
        return

    username = email.split("@")[0].lower()

    print(f"Sprawdzam użytkownika '{username}' w bazie Firestore...")
    if get_user(username):
        print("Błąd: Taki użytkownik już istnieje w bazie!")
        return

    hashed = hash_password(password)
    create_user(
        username=username,
        email=email,
        password_hash=hashed,
        is_admin=True,
        must_change_password=False
    )
    print(f"Sukces! Administrator '{username}' został utworzony w bazie danych.")

if __name__ == "__main__":
    main()