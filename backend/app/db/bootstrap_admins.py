from __future__ import annotations

from typing import Any

from sqlalchemy import update

from app.core.config import settings
from app.db.session import session_scope
from app.modules.users.models import User


def main() -> int:
    emails = settings.admin_emails
    if not emails:
        return 0
    with session_scope() as session:
        result: Any = session.execute(
            update(User).where(User.email.in_(emails)).values(role="admin")
        )
        return int(result.rowcount or 0)


if __name__ == "__main__":
    print(f"admins_bootstrapped={main()}")
