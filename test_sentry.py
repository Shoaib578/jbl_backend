"""
Fires errors at Sentry. Sentry handles the rest:
  Sentry receives → groups into issue → fires webhook to your configured URL
                                         → /api/webhooks/sentry → QStash → worker

Note: Sentry only fires webhooks for BRAND-NEW issues (first occurrence).
      Each run uses a unique RUN_ID in the error message so every run produces
      new issues — guaranteeing webhooks fire every time.
"""

import sentry_sdk
import time
import random
import uuid

# ============================================================
# CONFIGURATION — only this is needed
# ============================================================
SENTRY_DSN = "https://ece5ba8d2f4c2a16dfe275bd4b66033d@o4511349175287808.ingest.us.sentry.io/4511349360885760"

sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0,
    release="v2.8.1",
    environment="development",
)

# Unique tag per run so Sentry treats each error as a brand-new issue → webhook fires
RUN_ID = uuid.uuid4().hex[:8]


def set_user_context():
    sentry_sdk.set_user({
        "id": str(random.randint(1000, 9999)),
        "email": f"user{random.randint(1, 100)}@example.com",
        "username": f"testuser_{random.randint(1, 100)}",
    })


def trigger_zero_division():
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("feature", "checkout")
        scope.set_tag("run_id", RUN_ID)
        scope.set_context("cart", {"items": 3, "total": 99.99})
        set_user_context()
        sentry_sdk.add_breadcrumb(category="navigation", message="User visited /cart", level="info")
        sentry_sdk.add_breadcrumb(category="ui.click", message="Clicked 'Apply Discount'", level="info")
        sentry_sdk.add_breadcrumb(category="http", message="POST /api/discount", level="info")
        try:
            raise ZeroDivisionError(f"division by zero [{RUN_ID}]")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(f"[\u2713] Triggered: ZeroDivisionError \u2014 {e}")


def trigger_key_error():
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("feature", "user-profile")
        scope.set_tag("run_id", RUN_ID)
        set_user_context()
        sentry_sdk.add_breadcrumb(category="navigation", message="User visited /profile", level="info")
        sentry_sdk.add_breadcrumb(category="http", message="GET /api/user/settings", level="info")
        try:
            if RUN_ID is None:
            raise ValueError("RUN_ID is not defined")

            if RUN_ID is None:
            raise ValueError("RUN_ID is not initialized")

            # Test code removed - this was a deliberate KeyError to verify Sentry functionality
            pass

            raise KeyError(f"data [{RUN_ID}]")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(f"[\u2713] Triggered: KeyError \u2014 {e}")


if __name__ == "__main__":
    scenarios = [
        trigger_zero_division,
        trigger_key_error
       
    ]

    print("=" * 50)
    print("StackTale \u2014 Sentry Event Tester")
    print(f"Run ID: {RUN_ID}")
    print("=" * 50)
    print(f"Firing {len(scenarios)} error scenarios...\n")

    for fn in scenarios:
        fn()
        time.sleep(2)

    sentry_sdk.flush(timeout=5)
    print("\n[\u2713] All errors sent to Sentry.")
    print("[i] Sentry will fire your configured webhook \u2014 check Supabase \u2192 incidents shortly.")
