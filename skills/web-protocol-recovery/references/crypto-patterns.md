# Crypto Patterns

Use this file when signatures, encryption, or helper outputs look suspicious.

## Standard-looking helpers that are often not standard

- `md5`
- `sha1`
- `btoa`
- `atob`
- `hmac`
- `aes`
- `rsa`

## Fast recognition checklist

- length matches a common digest size
- alphabet matches hex, Base64, URL-safe Base64, or a custom alphabet
- padding matches a standard encoder
- output changes with timestamp, page, or session state
- helper reads DOM, globals, or side-script state
- output is digest plus a short suffix digest, checksum nibble, or version fragment
- a UUID, nonce, or session value looks standard at first glance but contains an inserted fixed-width segment, prefix, or checksum-derived fragment
- the apparent key, iv, seed, or hash source comes from slicing, concatenating, trimming, or decorating a config field instead of using it directly

## Fixed-input validation loop

1. freeze a tiny input such as `"abc"`
2. freeze a live input such as a captured timestamp
3. compare browser output with local output
4. compare intermediate strings, not only final digests

## Cross-runtime porting loop

When porting JS logic to Python or another runtime:

1. freeze the same config blob, timestamp, nonce, UUID source, and fingerprint vector
2. compare normalization outputs first, such as compact JSON, sliced key material, prefixed payloads, or checksum inputs
3. compare the final cookie, token, or sign output only after the intermediate forms match
4. keep one deterministic parity vector before trusting live traffic

## Common failure modes

- standard Base64 library used against a patched alphabet
- standard MD5 used against a custom string-to-word packing step
- custom `chrsz` or string-width handling
- little-endian versus big-endian word packing
- patched constants, altered rounds, or nonstandard hex output order
- URL-encoding mismatch before hashing
- wrong timestamp precision
- hidden page or session state included in the input
- correct hash function applied to the wrong JSON serialization, item order, or compactness rule
- standard UUID or random hex used where the protocol expects a structurally constrained local identifier
- apparent key or iv used directly when the page normalizes it through slice, concat, trim, or wrapper removal first
- recomputing an accepted bundle or version hash from current file bytes when the client actually uses an embedded compatibility id

## Delivery rule

Do not call crypto "done" until fixed-input self-checks are in the collector and any cross-runtime port has at least one deterministic parity vector.

## Reference implementations (Node.js / Python)

Use these as the standard-behaviour baseline. If the target diverges on a frozen input, the helper is patched — extract and run the original JS instead of forcing a standard library.

### MD5 / HMAC

```javascript
// Node.js
const crypto = require('crypto');
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const hmacSha256 = (msg, secret) => crypto.createHmac('sha256', secret).update(msg).digest('hex');
```

```python
# Python
import hashlib, hmac
def md5(text: str) -> str: return hashlib.md5(text.encode('utf-8')).hexdigest()
def hmac_sha256(msg: str, secret: str) -> str:
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
```

Non-standard MD5 (e.g. altered `chrsz`, custom string-to-word packing) will disagree with the standard output on the same input — extract the original JS and run it in a runtime.

### AES (CBC / ECB / CryptoJS)

```javascript
// Node.js
const crypto = require('crypto');
function aesCbcEncrypt(plaintext, key, iv) {
  const c = crypto.createCipheriv('aes-128-cbc', key, iv); // PKCS7 by default
  return c.update(plaintext, 'utf8', 'base64') + c.final('base64');
}
// CryptoJS compatibility (PKCS7 default):
// CryptoJS.AES.encrypt(pt, CryptoJS.enc.Utf8.parse(key), { iv: CryptoJS.enc.Utf8.parse(iv), mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 })
```

```python
# Python
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
def aes_cbc_encrypt(pt, key, iv):
    c = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    return base64.b64encode(c.encrypt(pad(pt.encode(), AES.block_size))).decode()
def aes_ecb_encrypt(pt, key):
    c = AES.new(key.encode(), AES.MODE_ECB)
    return base64.b64encode(c.encrypt(pad(pt.encode(), AES.block_size))).decode()
```

Key-length maps mode: 16/24/32 bytes = AES-128/192/256; iv is 16 bytes; CBC needs iv, ECB does not. Confirm key/iv are used directly and not sliced/concatenated/wrapped from a config field first.

### DES / 3DES

```javascript
// Node.js: 'des-ecb' (8-byte key), 'des-ede3-cbc' (24-byte key + iv)
```

```python
from Crypto.Cipher import DES, DES3
def des_ecb_encrypt(pt, key):
    return base64.b64encode(DES.new(key.encode(), DES.MODE_ECB).encrypt(pad(pt.encode(), DES.block_size))).decode()
def des3_cbc_encrypt(pt, key, iv):
    return base64.b64encode(DES3.new(key.encode(), DES3.MODE_CBC, iv.encode()).encrypt(pad(pt.encode(), DES3.block_size))).decode()
```

### RSA

```javascript
// Node.js (PKCS1); node-forge for RSAES-PKCS1-V1_5 from a PEM public key
const enc = crypto.publicEncrypt({ key: publicKeyPem, padding: crypto.constants.RSA_PKCS1_PADDING }, Buffer.from(pt)).toString('base64');
```

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, PKCS1_OAEP
def rsa_pkcs1(pt, pem):
    return base64.b64encode(PKCS1_v1_5.new(RSA.import_key(pem)).encrypt(pt.encode())).decode()
def rsa_oaep(pt, pem):
    return base64.b64encode(PKCS1_OAEP.new(RSA.import_key(pem)).encrypt(pt.encode())).decode()
```

Public keys arrive as PEM or as modulus(n)+exponent(e) that must be assembled into a PEM. Long payloads may be chunked before encryption.

### Base64 variants / XOR / RC4

```javascript
// Base64url: base64 then replace + / = with - _ (strip). Custom alphabet: map std alphabet chars to the target table.
// XOR: charCodeAt(i) ^ key.charCodeAt(i % key.length). RC4: standard KSA+PRGA.
```

```python
import base64
b64url = base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')
def custom_b64(text, table):
    std = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    return base64.b64encode(text.encode()).decode().translate(str.maketrans(std, table))
def xor_hex(pt, key):
    return bytes(ord(pt[i]) ^ ord(key[i % len(key)]) for i in range(len(pt))).hex()
from Crypto.Cipher import ARC4
def rc4(data, key): return ARC4.new(key.encode()).encrypt(data.encode())
```

### Timestamps and signing concatenation

```python
import time, hashlib, json
ts_ms = int(time.time() * 1000)   # 13-digit
ts_sec = int(time.time())          # 10-digit
def md5(s): return hashlib.md5(s.encode()).hexdigest()
# fixed format:  md5(f"page={page}&t={ts}&key={secret}")
# sorted params: md5("&".join(f"{k}={p[k]}" for k in sorted(p)) + secret)
# JSON body:     md5(json.dumps(data, separators=(',', ':'), sort_keys=True) + secret)  # match the page's exact serialization
# pipe:          md5(f"{page}|{ts}|{secret}")
```

Some targets sign with a server-issued timestamp from a response header or bootstrap endpoint, not the local clock. JSON serialization (compactness, key order, non-ASCII escaping) is part of the signed input — match the page byte-for-byte.

