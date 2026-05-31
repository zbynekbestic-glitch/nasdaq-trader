import os
import json
import base64
import tempfile
from pywebpush import webpush, WebPushException

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = "mailto:zbynekbestic@gmail.com"

_subscriptions: list = []
_tmp_key_path = None


def _get_private_key_path() -> str:
    global _tmp_key_path
    raw = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not raw:
        return ""

    # Pokud je base64 DER, převeď na PEM
    if not raw.startswith("-----"):
        try:
            padding = '=' * (4 - len(raw) % 4) if len(raw) % 4 else ''
            der = base64.urlsafe_b64decode(raw + padding)
            from cryptography.hazmat.primitives.serialization import load_der_private_key, Encoding, PrivateFormat, NoEncryption
            from cryptography.hazmat.backends import default_backend
            pk = load_der_private_key(der, password=None, backend=default_backend())
            pem = pk.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
        except Exception as e:
            print(f"DER conversion error: {e}")
            pem = raw.replace("\\n", "\n")
    else:
        pem = raw.replace("\\n", "\n")

    # Zapiš do temp souboru
    if _tmp_key_path is None:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        tmp.write(pem)
        tmp.close()
        _tmp_key_path = tmp.name
        print(f"VAPID key written to {_tmp_key_path}")

    return _tmp_key_path


def add_subscription(subscription: dict):
    endpoint = subscription.get("endpoint")
    if not any(s.get("endpoint") == endpoint for s in _subscriptions):
        _subscriptions.append(subscription)
        print(f"New push subscription, total: {len(_subscriptions)}")


def remove_subscription(endpoint: str):
    global _subscriptions
    _subscriptions = [s for s in _subscriptions if s.get("endpoint") != endpoint]


def send_push(title: str, body: str, url: str = "/"):
    key_path = _get_private_key_path()
    if not key_path or not VAPID_PUBLIC_KEY:
        print(f"Push skipped: key_path={bool(key_path)}, public={bool(VAPID_PUBLIC_KEY)}")
        return

    data = json.dumps({"title": title, "body": body, "url": url})
    dead = []

    for sub in list(_subscriptions):
        try:
            webpush(
                subscription_info=sub,
                data=data,
                vapid_private_key=key_path,
                vapid_claims={"sub": VAPID_EMAIL},
            )
            print(f"Push sent to {sub.get('endpoint', '')[:50]}")
        except WebPushException as e:
            print(f"WebPush error: {e}")
            if e.response and e.response.status_code in (404, 410):
                dead.append(sub.get("endpoint"))
        except Exception as e:
            print(f"Push error: {e}")

    for endpoint in dead:
        remove_subscription(endpoint)


def get_vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY
