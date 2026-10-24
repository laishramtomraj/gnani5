"""create_admin.py - create the first administrator (or reset a password) from the server's command line.

    python create_admin.py                              create an administrator (asks for the details)
    python create_admin.py --reset-password EMAIL       set a new password for an existing administrator

The password is typed without being shown and is stored only as a salted scrypt hash. Nothing is written to
a file and there is no sign-up page on the website.
"""
import argparse
import getpass
import sys

import admin_auth as auth


def ask_password(email: str) -> str:
    while True:
        first = getpass.getpass("Password (at least 12 characters, letters and numbers): ")
        problems = auth.password_problems(first, email)
        if problems:
            print("  " + " ".join(problems))
            continue
        if getpass.getpass("Repeat the password: ") != first:
            print("  The passwords did not match. Try again.")
            continue
        return first


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a website administrator.")
    parser.add_argument("--reset-password", metavar="EMAIL", help="reset the password of an existing administrator")
    args = parser.parse_args()
    try:
        if args.reset_password:
            auth.set_password(args.reset_password, ask_password(args.reset_password))
            print(f"Password updated for {args.reset_password}. All their sessions were ended.")
        else:
            email = input("Administrator email: ").strip()
            if not auth.valid_email(email):
                print("That does not look like a valid email address.")
                return 1
            name = input("Display name (optional): ").strip()
            auth.create_admin(email, ask_password(email), name)
            print(f"Administrator {email} created. Sign in at  /?admin  on your website.")
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
