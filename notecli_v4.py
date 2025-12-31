#!/usr/bin/env python3
import os
import json
import uuid
import base64
import argparse
import requests
import redis
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# -----------------------------
# Backend URLs (env)
# -----------------------------
# Default to localhost and standard ports if env vars missing
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://127.0.0.1:6380")
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN")


HEADERS = {}
if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
    HEADERS = {
        "Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}",
        "Content-Type": "application/json"
    }

# -----------------------------
# Crypto
# -----------------------------
def derive_key(share_key: bytes, salt: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA384(),
        length=32,
        salt=salt,
        info=b"secure-note"
    ).derive(share_key)

def encrypt(note: str, key: bytes) -> dict:
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, note.encode(), None)
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode()
    }

def decrypt(blob: dict, key: bytes) -> str:
    aes = AESGCM(key)
    return aes.decrypt(
        base64.b64decode(blob["nonce"]),
        base64.b64decode(blob["ciphertext"]),
        None
    ).decode()

# -----------------------------
# Lua for atomic read-count decay
# -----------------------------
LUA_UNSEAL = """
local note = redis.call("GET", KEYS[1])
if not note then return nil end
local reads = redis.call("GET", KEYS[2])
if reads then
  reads = tonumber(reads) - 1
  if reads <= 0 then
    redis.call("DEL", KEYS[1])
    redis.call("DEL", KEYS[2])
  else
    redis.call("SET", KEYS[2], reads)
  end
end
return note
"""

# -----------------------------
# Redis / Dragonfly failover client
# -----------------------------
def get_redis_client(url=None):
    backends = [url] if url else [REDIS_URL, DRAGONFLY_URL]
    for u in backends:
        if not u:
            continue
        try:
            r = redis.from_url(u, decode_responses=True)
            r.ping()
            print(f"Connected to backend: {u}")
            return r
        except Exception as e:
            print(f"Failed to connect to {u}: {e}")
    raise RuntimeError("All requested backends unavailable!")

# -----------------------------
# Upstash helpers
# -----------------------------
def upstash_set(key, value, ex=None):
    if not UPSTASH_REDIS_URL or not HEADERS:
        raise RuntimeError("Upstash URL or token missing")
    url = f"{UPSTASH_REDIS_URL}/set/{key}"
    if ex:
        url += f"?ex={ex}"
    r = requests.post(url, headers=HEADERS, data=value)
    r.raise_for_status()

def upstash_eval(script, keys, args=None):
    if args is None:
        args = []
    payload = {"script": script, "keys": keys, "args": args}
    r = requests.post(f"{UPSTASH_REDIS_URL}/eval", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json().get("result")

# -----------------------------
# CLI Functions
# -----------------------------
def create(note, ttl, reads, backend="local", url=None):
    note_id = uuid.uuid4().hex
    share_key = os.urandom(32)
    salt = os.urandom(16)

    key = derive_key(share_key, salt)
    blob = encrypt(note, key)
    blob["salt"] = base64.b64encode(salt).decode()
    blob_json = json.dumps(blob)

    if backend == "upstash":
        upstash_set(f"note:{note_id}", blob_json, ex=ttl)
        upstash_set(f"note:{note_id}:reads", str(reads))
    else:
        r = get_redis_client(url)
        r.setex(f"note:{note_id}", ttl, blob_json)
        r.set(f"note:{note_id}:reads", reads)

    print("NOTE CREATED")
    print(f"URL: note://{note_id}#{base64.urlsafe_b64encode(share_key).decode()}")


def create_with_failover(note, ttl=3600, reads=1):
    """
    Attempt Redis first, then Dragonfly on fail
    """
    try:
        print("Trying Redis...")
        create(note, ttl, reads, backend="local", url=REDIS_URL)
    except Exception as e_redis:
        print(f"[Redis failed] {e_redis}")
        if DRAGONFLY_URL:
            try:
                print("Trying Dragonfly...")
                create(note, ttl, reads, backend="local", url=DRAGONFLY_URL)
            except Exception as e_df:
                print(f"[Dragonfly failed] {e_df}")
                print("ERROR: Both Redis and Dragonfly backends unavailable!")
        else:
            print("ERROR: DRAGONFLY_URL not set, cannot failover!")


def open_note(note_id, share_key_b64, backend="local"):
    if not note_id or not share_key_b64:
        print("Error: note_id and share_key required")
        return
    share_key = base64.urlsafe_b64decode(share_key_b64)

    if backend == "upstash":
        try:
            result = upstash_eval(LUA_UNSEAL, keys=[f"note:{note_id}", f"note:{note_id}:reads"])
        except Exception as e:
            print(f"Upstash EVAL HTTP error: {e}")
            return
    else:
        r = get_redis_client()
        try:
            pipe = r.pipeline()
            pipe.get(f"note:{note_id}")
            pipe.get(f"note:{note_id}:reads")
            note_json, reads = pipe.execute()
            if not note_json:
                print("Note expired, already opened, or keys invalid")
                return
            if reads:
                reads = int(reads) - 1
                pipe = r.pipeline()
                if reads <= 0:
                    pipe.delete(f"note:{note_id}")
                    pipe.delete(f"note:{note_id}:reads")
                else:
                    pipe.set(f"note:{note_id}:reads", reads)
                pipe.execute()
            result = note_json
        except Exception as e:
            print(f"Local backend read failed: {e}")
            return

    try:
        blob = json.loads(result)
        salt = base64.b64decode(blob["salt"])
        key = derive_key(share_key, salt)
        decrypted = decrypt(blob, key)
        print("NOTE CONTENT:")
        print(decrypted)
    except Exception as e:
        print(f"Failed to decrypt note: {e}")

# -----------------------------
# CLI Entry Point
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    c = sub.add_parser("create")
    c.add_argument("note")
    c.add_argument("--ttl", type=int, default=3600)
    c.add_argument("--reads", type=int, default=1)
    c.add_argument("--backend", choices=["local", "upstash"], default="local")

    o = sub.add_parser("open")
    o.add_argument("note_url")
    o.add_argument("--backend", choices=["local", "upstash"], default="local")

    args = parser.parse_args()

    if args.cmd == "create":
        if args.backend == "local":
            create_with_failover(args.note, args.ttl, args.reads)
        else:
            create(args.note, args.ttl, args.reads, backend=args.backend)
    elif args.cmd == "open":
        if not args.note_url.startswith("note://") or "#" not in args.note_url:
            print("Invalid note URL")
            return
        note_id, share_key = args.note_url.replace("note://", "").split("#")
        open_note(note_id, share_key, backend=args.backend)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
