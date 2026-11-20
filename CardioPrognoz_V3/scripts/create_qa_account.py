"""Create an isolated, synthetic-only account for the LZ11 load workflow."""

import os
import sqlite3

from accounts import create_user, init_db
from app import app


def main():
    username = os.environ.get("LZ11_QA_USERNAME", "synthetic_qa")
    password = os.environ.get("LZ11_QA_PASSWORD")
    if not password:
        raise RuntimeError("LZ11_QA_PASSWORD is required")
    with app.app_context():
        init_db()
        try:
            create_user(username, password, "user")
        except sqlite3.IntegrityError as error:
            raise RuntimeError("QA account already exists; use a fresh test database") from error
    print("Created one isolated synthetic QA account")


if __name__ == "__main__":
    main()
