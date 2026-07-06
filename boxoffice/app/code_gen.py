import secrets
import string

# Remove visually ambiguous characters: O/0, I/1
_ALPHABET = "".join(
    c for c in (string.ascii_uppercase + string.digits)
    if c not in "O0I1"
)


def generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def unique_code(db, model) -> str:
    """Generate a code guaranteed unique for model.code, or raise."""
    for _ in range(10):
        code = generate_code()
        if not db.query(model).filter(model.code == code).first():
            return code
    raise RuntimeError("Could not generate unique code")
