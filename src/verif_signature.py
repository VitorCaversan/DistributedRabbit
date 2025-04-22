import os, json, base64, pathlib
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

ROOT = pathlib.Path(__file__).resolve().parent.parent      # project root
# Creating global variables for the folder path
os.environ["MSPAYMENT_PRIV_KEY"] = str(ROOT / "keys" / "ms_payment_priv.pem")
os.environ["MSPAYMENT_PUB_KEY"]  = str(ROOT / "keys" / "ms_payment_pub.pem")

_PUB_PATH = os.getenv("MSPAYMENT_PUB_KEY")
with open(_PUB_PATH, "rb") as f:
    _PUBLIC = load_pem_public_key(f.read())

def verify_sig(body: bytes, headers: dict) -> dict:
    if headers.get("sig_alg") != "ed25519" or "sig" not in headers:
        raise InvalidSignature("missing signature")
    sig = base64.b64decode(headers["sig"])
    _PUBLIC.verify(sig, body)             # raises if bad
    return json.loads(body.decode("utf-8"))
