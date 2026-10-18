"""Management commands.

    python -m app.cli create-admin --email you@x.com --name "You"
    python -m app.cli seed
"""
import argparse
import getpass

from app.auth.service import create_user, find_by_email
from app.core.db import SessionLocal


def create_admin(email: str, name: str) -> None:
    with SessionLocal() as db:
        user = find_by_email(db, email)
        if user:
            user.role = "admin"
            db.commit()
            print(f"Promoted existing user {email} to admin.")
            return
        password = getpass.getpass("Password (min 8 chars): ")
        if len(password) < 8:
            raise SystemExit("Password must be at least 8 characters.")
        create_user(db, name, email, password, role="admin")
        print(f"Created admin {email}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an admin user, or promote an existing one")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Admin")
    sub.add_parser("seed", help="Load sample categories and products")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name)
    elif args.command == "seed":
        from app.seed import seed

        with SessionLocal() as db:
            print(seed(db))


if __name__ == "__main__":
    main()
