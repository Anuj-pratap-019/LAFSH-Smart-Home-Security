import hashlib
import time
import secrets

def sha256_hash(text: str) -> str:
    """Compute SHA-256 hash and return lowercase hex string."""
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest().lower()

def xor_hex(hex1: str, hex2: str) -> str:
    """Bitwise XOR of two equal-length hex strings."""
    b1 = bytes.fromhex(hex1)
    b2 = bytes.fromhex(hex2)
    xored = bytes(x ^ y for x, y in zip(b1, b2))
    return xored.hex().lower()

def generate_nonce(len_bits: int = 128) -> str:
    """Generate a random hex nonce."""
    num_bytes = len_bits // 8
    return secrets.token_hex(num_bytes).lower()

def get_timestamp() -> int:
    """Return current Unix timestamp as integer (seconds)."""
    return int(time.time())

def totp_generate(secret_hex: str, unix_time: int = None) -> int:
    """Generate a 6-digit TOTP code (RFC 6238 simplified, matching the MATLAB version)."""
    if unix_time is None:
        unix_time = get_timestamp()
    time_step = int(unix_time // 30)
    hmac_input = f"{secret_hex}||{time_step}"
    hash_hex = sha256_hash(hmac_input)
    # Truncate: take last 8 hex chars -> 32-bit integer -> mod 10^6
    trunc_hex = hash_hex[-8:]
    trunc_int = int(trunc_hex, 16)
    return trunc_int % 1000000

def totp_verify(secret_hex: str, submitted_otp: int, unix_time: int = None) -> bool:
    """Verify a submitted OTP with a 90-second grace window."""
    if unix_time is None:
        unix_time = get_timestamp()
    time_step = int(unix_time // 30)
    for offset in (-1, 0, 1):
        expected = totp_generate(secret_hex, (time_step + offset) * 30)
        if int(submitted_otp) == expected:
            return True
    return False
