"""Reset existing passwords in the selected development database.

Usage: APP_ENV=development DATABASE_URL=... python -m app.dev_passwords 12345678
"""

import os
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import User
from .security import hash_password


def main() -> None:
    if os.environ.get("APP_ENV") != "development":
        raise SystemExit("Este comando solo funciona con APP_ENV=development")
    if os.environ.get("DATABASE_URL") != "sqlite+pysqlite:///./dev.db":
        raise SystemExit("Selecciona explícitamente la base SQLite local ./dev.db")
    if len(sys.argv) != 2 or len(sys.argv[1]) < 8:
        raise SystemExit("Uso: python -m app.dev_passwords CONTRASEÑA (mínimo 8 caracteres)")

    with SessionLocal.begin() as db:
        users = db.scalars(select(User)).all()
        for user in users:
            user.password_hash = hash_password(sys.argv[1])

    print(f"Contraseña actualizada para {len(users)} cuentas de desarrollo")


if __name__ == "__main__":
    main()
