import hashlib
import secrets


def hash_password(password: str) -> str:
  salt = secrets.token_bytes(16)
  dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
  return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
  if "$" not in stored:
    return False
  salt_hex, expected_hex = stored.split("$", 1)
  try:
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(expected_hex)
  except ValueError:
    return False
  dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
  return secrets.compare_digest(dk, expected)
