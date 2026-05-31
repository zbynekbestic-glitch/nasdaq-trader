import os
import json
import base64
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, EllipticCurvePrivateKey
from cryptography.hazmat.backends import default_backend

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
_VAPID_PRIVATE_RAW = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_EMAIL = "mailto:zbynekbestic@gmail.com"


def _get_private_key_pem() -> str:
    key = _VAPID_PRIVATE_RAW.strip()
    if not key:
        return ""
    # Pokud je to base64 DER formát, převeď na PEM
    if not key.startswith("-----"):
        try:
            padding = '=' * (4 - len(key) % 4) if len(key) % 4 else ''
            der = base64.urlsafe_b64decode(key + padding)
            from cryptography.hazmat.primitives.serialization import load_der_private_key
            pk = load_der_private_key(der, password=None, backend=default_backend())
            return pk.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
        except Exception as e:
            print(f"Key conversion error: {e}")
            return key
    return key.replace("\\n", "\n")

# In-memory store subscriptions
_subscriptions: list = []


def add_subscription(subscription: dict):
    endpoint = subscription.get("endpoint")
    if not any(s.get("endpoint") == endpoint for s in _subscriptions):
        _subscriptions.append(subscription)
        print(f"New push subscription, total: {len(_subscriptions)}")


def remove_subscription(endpoint: str):
    global _subscriptions
    _subscriptions = [s for s in _subscriptions if s.get("endpoint") != endpoint]


def send_push(title: str, body: str, url: str = "/"):
    private_key = _get_private_key_pem()
    if not private_key or not VAPID_PUBLIC_KEY:
        print("Push skipped: missing VAPID keys")
        return

    data = json.dumps({"title": title, "body": body, "url": url})
    dead = []

    for sub in list(_subscriptions):
        try:
            webpush(
                subscription_info=sub,
                data=data,
                vapid_private_key=private_key,
                vapid_claims={"sub": VAPID_EMAIL},
            )
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                dead.append(sub.get("endpoint"))
            else:
                print(f"Push error: {e}")
        except Exception as e:
            print(f"Push error: {e}")

    for endpoint in dead:
        remove_subscription(endpoint)


def get_vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY
