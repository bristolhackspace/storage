import base64
import hashlib
import secrets

TOKEN_BYTES = 32
HASH_ALGORITHM = "sha256"

def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)

def token_to_id(token: str | None) -> str | None:
    if token is None:
        return None
    token_bytes = base64.urlsafe_b64decode(token + "==")
    m = hashlib.new(HASH_ALGORITHM, token_bytes)
    id_bytes = m.digest()
    id_token = base64.urlsafe_b64encode(id_bytes).rstrip(b'=').decode('ascii')
    return id_token