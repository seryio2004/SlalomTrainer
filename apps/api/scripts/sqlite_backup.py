"""Consistent SQLite backup/restore to a new file; never overwrite a database."""
import argparse
import json
import os
from pathlib import Path
import sqlite3


def copy_database(source: Path, target: Path):
    if not source.is_file() or source.resolve() == target.resolve():
        raise ValueError('El origen debe existir y el destino ser distinto')
    # Exclusive creation also protects against concurrent overwrite and symlinks.
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as origin:
            with sqlite3.connect(target) as destination:
                origin.backup(destination)
                if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('La comprobación de integridad ha fallado')
                if destination.execute('PRAGMA foreign_key_check').fetchall():
                    raise ValueError('La comprobación de claves foráneas ha fallado')
                tables = [row[0] for row in destination.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                counts = {table: destination.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in tables}
                version = destination.execute('SELECT version_num FROM alembic_version').fetchone()[0] if 'alembic_version' in tables else None
        return {'integrity': 'ok', 'foreign_keys': 'ok', 'migration': version, 'counts': counts}
    except Exception:
        target.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path, help='Ruta nueva; se rechaza cualquier archivo existente')
    args = parser.parse_args()
    print(json.dumps(copy_database(args.source, args.target), indent=2))
