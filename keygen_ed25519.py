# keygen_ed25519.py
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from pathlib import Path

keys_path = Path(__file__).with_name("keys")
keys_path.mkdir(exist_ok=True)

priv = Ed25519PrivateKey.generate()
pub  = priv.public_key()

(priv_bytes, pub_bytes) = (
    priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()),
    pub.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)
)

(keys_path / "ms_payment_priv.pem").write_bytes(priv_bytes)
(keys_path / "ms_payment_pub.pem").write_bytes(pub_bytes)

print("✔  Keypair written to ./keys/")
