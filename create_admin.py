"""Create an owner-level admin user from the command line.

Usage:
    python create_admin.py                     # interactive prompts
    python create_admin.py --login admin --password secret
"""

import argparse
import asyncio
import getpass
import sys

from passlib.context import CryptContext
from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models import AdminUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_owner(login: str, password: str) -> None:
    await ensure_tables()

    async with SessionLocal() as db:
        existing = await db.scalar(
            select(AdminUser).where(AdminUser.login == login)
        )
        if existing:
            print(f"[!] Пользователь «{login}» уже существует (role={existing.role}).")
            sys.exit(1)

        user = AdminUser(
            login=login,
            password_hash=pwd_context.hash(password),
            role="owner",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"[+] Owner-админ создан: id={user.id}, login={user.login}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Создать owner-админа")
    parser.add_argument("--login", help="Логин администратора")
    parser.add_argument("--password", help="Пароль (если не указан — спросит интерактивно)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    login = args.login or input("Логин: ").strip()
    if not login:
        print("[!] Логин не может быть пустым.")
        sys.exit(1)

    password = args.password
    if not password:
        password = getpass.getpass("Пароль: ")
        confirm = getpass.getpass("Повторите пароль: ")
        if password != confirm:
            print("[!] Пароли не совпадают.")
            sys.exit(1)

    if len(password) < 4:
        print("[!] Пароль слишком короткий (минимум 4 символа).")
        sys.exit(1)

    if len(password.encode("utf-8")) > 72:
        print("[!] Пароль слишком длинный (макс. 72 байта — ограничение bcrypt).")
        sys.exit(1)

    asyncio.run(create_owner(login, password))


if __name__ == "__main__":
    main()
