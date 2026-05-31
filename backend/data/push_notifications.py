import os
import json
from pywebpush import webpush, WebPushException

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
VAPID_EMAIL = "mailto:zbynekbestic@gmail.com"

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
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        return

    data = json.dumps({"title": title, "body": body, "url": url})
    dead = []

    for sub in list(_subscriptions):
        try:
            webpush(
                subscription_info=sub,
                data=data,
                vapid_private_key=VAPID_PRIVATE_KEY,
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
