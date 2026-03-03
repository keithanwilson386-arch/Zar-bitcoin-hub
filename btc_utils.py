"""Bitcoin address utilities: validation and pubkey->address confirmation.

Functions:
- `is_valid_btc_address(address)` -> bool
- `pubkey_to_p2pkh(pubkey_hex)` -> P2PKH address
- `pubkey_to_p2wpkh(pubkey_hex, hrp='bc')` -> Bech32 P2WPKH address
- `confirm_pubkey_matches_address(pubkey_hex, address)` -> bool

This module implements base58check and bech32 encoding/decoding minimally
without external dependencies.
"""
from __future__ import annotations

import hashlib
from typing import Tuple


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def ripemd160(b: bytes) -> bytes:
    h = hashlib.new('ripemd160')
    h.update(b)
    return h.digest()


def base58_encode(b: bytes) -> str:
    n = int.from_bytes(b, 'big')
    res = ''
    while n > 0:
        n, r = divmod(n, 58)
        res = BASE58_ALPHABET[r] + res
    # leading zeros
    zeros = 0
    for c in b:
        if c == 0:
            zeros += 1
        else:
            break
    return '1' * zeros + res


def base58check_encode(payload: bytes) -> str:
    chk = sha256(sha256(payload))[:4]
    return base58_encode(payload + chk)


def base58_decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + BASE58_ALPHABET.index(ch)
    b = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    # add leading zeros
    zeros = 0
    for ch in s:
        if ch == '1':
            zeros += 1
        else:
            break
    return b'\x00' * zeros + b


def base58check_decode(s: str) -> Tuple[bytes, bytes]:
    b = base58_decode(s)
    if len(b) < 4:
        raise ValueError('Invalid base58 string')
    payload, chk = b[:-4], b[-4:]
    if sha256(sha256(payload))[:4] != chk:
        raise ValueError('Invalid checksum')
    return payload, chk


# --- Bech32 (BIP173) minimal implementation ---
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values):
    GENERATORS = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = (chk >> 25)
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= GENERATORS[i] if ((b >> i) & 1) else 0
    return chk


def bech32_hrp_expand(hrp: str):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_create_checksum(hrp: str, data):
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp: str, data) -> str:
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + '1' + ''.join([BECH32_CHARSET[d] for d in combined])


def convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def pubkey_to_p2pkh(pubkey_hex: str) -> str:
    pk = bytes.fromhex(pubkey_hex)
    h = ripemd160(sha256(pk))
    payload = b'\x00' + h  # 0x00 mainnet
    return base58check_encode(payload)


def pubkey_to_p2wpkh(pubkey_hex: str, hrp: str = 'bc') -> str:
    pk = bytes.fromhex(pubkey_hex)
    prog = ripemd160(sha256(pk))
    # witness version 0
    data = [0] + convertbits(prog, 8, 5)
    return bech32_encode(hrp, data)


def is_valid_btc_address(addr: str) -> bool:
    addr = addr.strip()
    if addr.startswith('1') or addr.startswith('3'):
        # base58 addresses
        try:
            payload, chk = base58check_decode(addr)
            # payload[0] is version
            return True
        except Exception:
            return False
    if addr.lower().startswith('bc1') or addr.lower().startswith('tb1'):
        # bech32 validation (light): ensure decode works
        try:
            # split
            pos = addr.rfind('1')
            hrp = addr[:pos]
            data = [BECH32_CHARSET.index(c) for c in addr[pos+1:]]
            # basic checksum test
            return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1
        except Exception:
            return False
    return False


def confirm_pubkey_matches_address(pubkey_hex: str, address: str) -> bool:
    try:
        addr = address.strip()
        # Try p2pkh
        if addr.startswith('1'):
            return pubkey_to_p2pkh(pubkey_hex) == addr
        # Try bech32
        if addr.lower().startswith('bc1') or addr.lower().startswith('tb1'):
            # assume hrp based on address prefix
            hrp = 'bc' if addr.lower().startswith('bc1') else 'tb'
            return pubkey_to_p2wpkh(pubkey_hex, hrp=hrp) == addr.lower()
        # Try p2sh address (not derived from pubkey directly)
        return False
    except Exception:
        return False


def verify_message(address: str, message: str, signature_b64: str) -> bool:
    """Verify a Bitcoin signed message.

    Returns True if the signature corresponds to the address. Requires `coincurve`.
    The signature should be base64 encoded and include recovery ID (65 bytes).
    """
    try:
        import base64
        from coincurve import PublicKey
    except ImportError:
        raise RuntimeError("coincurve is required for message verification")

    # decode signature
    sig = base64.b64decode(signature_b64)
    if len(sig) != 65:
        raise ValueError("Invalid signature length")

    # Bitcoin message prefix
    prefix = b"\x18Bitcoin Signed Message:\n"
    # encoded length as varint
    def varint(i):
        if i < 0xfd:
            return bytes([i])
        elif i <= 0xffff:
            return b"\xfd" + i.to_bytes(2, "little")
        elif i <= 0xffffffff:
            return b"\xfe" + i.to_bytes(4, "little")
        else:
            return b"\xff" + i.to_bytes(8, "little")

    msg_bytes = message.encode('utf-8')
    data = prefix + varint(len(msg_bytes)) + msg_bytes
    hashed = sha256(sha256(data))

    # recovery: first byte contains recovery id + 27 + (4 if compressed)
    first = sig[0]
    rec_id = first - 27
    compressed = False
    if rec_id >= 4:
        compressed = True
        rec_id -= 4

    # The current coincurve API expects a 65-byte recoverable signature
    # where the recovery id is embedded in the first byte.  We can pass the
    # entire signature and let `from_signature_and_message` recover the pubkey.
    pubkey = PublicKey.from_signature_and_message(sig, hashed, hasher=None)
    pubkey_hex = pubkey.format(compressed=compressed).hex()
    # check against address using existing confirmation
    return confirm_pubkey_matches_address(pubkey_hex, address)


if __name__ == '__main__':
    print('btc_utils helper')
