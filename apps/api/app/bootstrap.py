"""Create the first local club and administrator once.

Usage: APP_ENV=development python -m app.bootstrap <email> <password> <club name>
"""

import os
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import Club, Membership, User
from .security import hash_password


def main():
    if os.environ.get("APP_ENV") != "development":
        raise SystemExit("Bootstrap only runs in development")
    if len(sys.argv) != 4 or len(sys.argv[2]) < 12:
        raise SystemExit("Usage: python -m app.bootstrap EMAIL PASSWORD CLUB_NAME (password >= 12 characters)")
    email, password, club_name = sys.argv[1:]
    email = email.lower().strip()
    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("User already exists")
        user = User(email=email, name="Administrador", password_hash=hash_password(password))
        club = Club(name=club_name)
        db.add_all([user, club])
        db.flush()
        db.add(Membership(club_id=club.id, user_id=user.id, roles=["club_admin", "coach"]))
        print(f"Club ID: {club.id}")


if __name__ == "__main__":
    main()
