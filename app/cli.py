"""Operator commands (run by a human, never by the web app).

    uv run python -m app.cli create-platform-admin --email you@company.com --name "Your Name"

Invite-only sign-in means the FIRST Platform Administrator must be created from the command
line (after that, admins invite everyone else through the API). In AWS, run it as a
one-off ECS task with the same image, like migrations.
"""

from __future__ import annotations

import argparse
import sys

from app.core.enums import PlatformRole
from app.db.session import get_sessionmaker
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.common import normalize_email
from app.services import audit


def create_platform_admin(email: str, name: str | None) -> str:
    email = normalize_email(email)
    session = get_sessionmaker()()
    try:
        repo = UserRepository(session)
        existing = repo.get_by_email(email)
        if existing is not None:
            if existing.platform_role is not PlatformRole.PLATFORM_ADMINISTRATOR:
                raise SystemExit(f"{email} exists with role {existing.platform_role.value}; not changing it.")
            return f"{email} is already a Platform Administrator."
        user = User(email=email, full_name=name, platform_role=PlatformRole.PLATFORM_ADMINISTRATOR)
        repo.add(user)
        audit.record(
            session,
            actor=None,
            action="user.create",
            resource_type="user",
            resource_id=user.id,
            clinic_id=None,
            details={"platform_role": "platform_administrator", "via": "cli"},
        )
        session.commit()
        return f"Created Platform Administrator {email}. They can now sign in with Google."
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-platform-admin", help="Create the first Platform Administrator")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default=None)
    args = parser.parse_args(argv)
    if args.command == "create-platform-admin":
        sys.stdout.write(create_platform_admin(args.email, args.name) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
