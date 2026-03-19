"""Seed a demo-api app with realistic e-commerce HTTP traces.

Usage::

    uv run python scripts/seed_demo_app.py

Creates (or overwrites) a ``demo-api`` app in the managed storage with 7
traces covering login, product browsing, cart management, and checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure the project root is on sys.path so cli.* imports work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.commands.capture.types import CaptureBundle, Context, Trace  # noqa: E402
from cli.formats.capture_bundle import (  # noqa: E402
    AppInfo,
    BrowserInfo,
    CaptureManifest,
    CaptureStats,
    ContextMeta,
    ElementInfo,
    Header,
    PageContent,
    PageInfo,
    RequestMeta,
    ResponseMeta,
    Timeline,
    TimelineEvent,
    TimingInfo,
    TraceMeta,
    ViewportInfo,
)
from cli.helpers.storage import store_capture, store_root  # noqa: E402

APP_NAME = "demo-api"
BASE_URL = "https://demo-shop.example.com"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1XzQyIiwiZXhwIjoxNzE2MjM5MDIyfQ.fake"
REFRESH_TOKEN = "rt_a1b2c3d4e5f6"

AUTH_HEADER = Header(name="Authorization", value=f"Bearer {TOKEN}")
JSON_CT = Header(name="Content-Type", value="application/json")


# -- Helpers -----------------------------------------------------------------

def _trace(
    trace_id: str,
    method: str,
    path: str,
    status: int,
    timestamp: int,
    *,
    request_body: dict[str, object] | None = None,
    response_body: dict[str, object] | list[object] | None = None,
    request_headers: list[Header] | None = None,
    context_refs: list[str] | None = None,
) -> Trace:
    req_bytes = json.dumps(request_body).encode() if request_body else b""
    resp_bytes = json.dumps(response_body).encode() if response_body is not None else b""

    req_headers = request_headers or []
    resp_headers = [JSON_CT]

    status_text = {200: "OK", 201: "Created", 204: "No Content"}.get(status, "OK")

    return Trace(
        meta=TraceMeta(
            id=trace_id,
            timestamp=timestamp,
            request=RequestMeta(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=req_headers,
                body_file=f"{trace_id}_request.bin" if req_bytes else None,
                body_size=len(req_bytes),
            ),
            response=ResponseMeta(
                status=status,
                status_text=status_text,
                headers=[] if status == 204 else resp_headers,
                body_file=f"{trace_id}_response.bin" if resp_bytes else None,
                body_size=len(resp_bytes),
            ),
            timing=TimingInfo(total_ms=85),
            context_refs=context_refs or [],
        ),
        request_body=req_bytes,
        response_body=resp_bytes,
    )


def _context(
    context_id: str,
    timestamp: int,
    action: str,
    selector: str,
    tag: str,
    text: str,
    page_path: str,
    page_title: str,
    *,
    content: PageContent | None = None,
) -> Context:
    return Context(
        meta=ContextMeta(
            id=context_id,
            timestamp=timestamp,
            action=action,
            element=ElementInfo(selector=selector, tag=tag, text=text),
            page=PageInfo(
                url=f"{BASE_URL}{page_path}",
                title=page_title,
                content=content,
            ),
            viewport=ViewportInfo(width=1440, height=900),
        )
    )


# -- Data --------------------------------------------------------------------

def _build_bundle() -> CaptureBundle:
    # Contexts
    contexts = [
        _context(
            "c_0001", 1000000, "click", "button.btn-signin", "BUTTON", "Sign in",
            "/login", "Demo Shop — Sign in",
            content=PageContent(
                headings=["Sign in to your account"],
                forms=[{
                    "id": "login-form",
                    "fields": ["email", "password"],
                    "submitLabel": "Sign in",
                }],
            ),
        ),
        _context(
            "c_0002", 1002000, "click", "nav a.nav-products", "A", "Products",
            "/dashboard", "Demo Shop — Dashboard",
            content=PageContent(
                headings=["Dashboard"],
                navigation=["Products", "Orders", "Cart", "Account"],
            ),
        ),
        _context(
            "c_0003", 1004000, "click", "a.product-link[data-id='42']", "A",
            "Wireless Headphones",
            "/products", "Demo Shop — Products",
            content=PageContent(
                headings=["All Products"],
                tables=["Name | Price | Category"],
            ),
        ),
        _context(
            "c_0004", 1006000, "click", "button.add-to-cart", "BUTTON", "Add to cart",
            "/products/42", "Demo Shop — Wireless Headphones",
            content=PageContent(
                headings=["Wireless Headphones"],
                main_text="Premium wireless headphones with noise cancellation. $79.99",
            ),
        ),
        _context(
            "c_0005", 1008000, "click", "nav a.nav-cart", "A", "Cart",
            "/products/42", "Demo Shop — Wireless Headphones",
            content=PageContent(
                navigation=["Products", "Orders", "Cart", "Account"],
            ),
        ),
        _context(
            "c_0006", 1010000, "click", "button.remove-item[data-id='ci-1']", "BUTTON",
            "Remove",
            "/cart", "Demo Shop — Cart",
            content=PageContent(
                headings=["Your Cart"],
                tables=["Item | Qty | Price | Actions"],
            ),
        ),
        _context(
            "c_0007", 1012000, "click", "button.place-order", "BUTTON", "Place order",
            "/cart", "Demo Shop — Cart",
            content=PageContent(
                headings=["Your Cart"],
                main_text="Total: $79.99",
            ),
        ),
    ]

    # Traces
    traces = [
        # t_0001 — login
        _trace(
            "t_0001", "POST", "/auth/login", 200, 1001000,
            request_body={"email": "alice@example.com", "password": "••••••••"},
            response_body={
                "access_token": TOKEN,
                "refresh_token": REFRESH_TOKEN,
                "expires_in": 3600,
                "user": {"id": "u_42", "email": "alice@example.com", "name": "Alice Martin"},
            },
            request_headers=[JSON_CT],
            context_refs=["c_0001"],
        ),
        # t_0002 — list products
        _trace(
            "t_0002", "GET", "/api/products", 200, 1003000,
            response_body={
                "items": [
                    {"id": "p_42", "name": "Wireless Headphones", "price": 79.99, "category": "Electronics", "in_stock": True},
                    {"id": "p_15", "name": "Cotton T-Shirt", "price": 24.50, "category": "Clothing", "in_stock": True},
                    {"id": "p_78", "name": "Coffee Mug", "price": 12.00, "category": "Home", "in_stock": False},
                ],
                "total": 3,
                "page": 1,
            },
            request_headers=[AUTH_HEADER],
            context_refs=["c_0002"],
        ),
        # t_0003 — product detail
        _trace(
            "t_0003", "GET", "/api/products/42", 200, 1005000,
            response_body={
                "id": "p_42",
                "name": "Wireless Headphones",
                "price": 79.99,
                "category": "Electronics",
                "description": "Premium wireless headphones with active noise cancellation and 30h battery.",
                "in_stock": True,
                "rating": 4.5,
                "review_count": 128,
            },
            request_headers=[AUTH_HEADER],
            context_refs=["c_0003"],
        ),
        # t_0004 — add to cart
        _trace(
            "t_0004", "POST", "/api/cart/items", 201, 1007000,
            request_body={"product_id": "p_42", "quantity": 1},
            response_body={
                "id": "ci-1",
                "product_id": "p_42",
                "product_name": "Wireless Headphones",
                "quantity": 1,
                "unit_price": 79.99,
            },
            request_headers=[AUTH_HEADER, JSON_CT],
            context_refs=["c_0004"],
        ),
        # t_0005 — view cart
        _trace(
            "t_0005", "GET", "/api/cart", 200, 1009000,
            response_body={
                "items": [
                    {"id": "ci-1", "product_id": "p_42", "product_name": "Wireless Headphones", "quantity": 1, "unit_price": 79.99},
                ],
                "subtotal": 79.99,
                "tax": 6.40,
                "total": 86.39,
            },
            request_headers=[AUTH_HEADER],
            context_refs=["c_0005"],
        ),
        # t_0006 — remove cart item
        _trace(
            "t_0006", "DELETE", "/api/cart/items/ci-1", 204, 1011000,
            request_headers=[AUTH_HEADER],
            context_refs=["c_0006"],
        ),
        # t_0007 — place order
        _trace(
            "t_0007", "POST", "/api/orders", 201, 1013000,
            request_body={"shipping_address_id": "addr_1", "payment_method_id": "pm_visa_42"},
            response_body={
                "id": "ord_1001",
                "status": "confirmed",
                "items_count": 1,
                "total": 86.39,
                "created_at": "2026-03-19T10:15:00Z",
            },
            request_headers=[AUTH_HEADER, JSON_CT],
            context_refs=["c_0007"],
        ),
    ]

    # Timeline (interleave contexts and traces chronologically)
    events = [
        TimelineEvent(timestamp=1000000, type="context", ref="c_0001"),
        TimelineEvent(timestamp=1001000, type="trace", ref="t_0001"),
        TimelineEvent(timestamp=1002000, type="context", ref="c_0002"),
        TimelineEvent(timestamp=1003000, type="trace", ref="t_0002"),
        TimelineEvent(timestamp=1004000, type="context", ref="c_0003"),
        TimelineEvent(timestamp=1005000, type="trace", ref="t_0003"),
        TimelineEvent(timestamp=1006000, type="context", ref="c_0004"),
        TimelineEvent(timestamp=1007000, type="trace", ref="t_0004"),
        TimelineEvent(timestamp=1008000, type="context", ref="c_0005"),
        TimelineEvent(timestamp=1009000, type="trace", ref="t_0005"),
        TimelineEvent(timestamp=1010000, type="context", ref="c_0006"),
        TimelineEvent(timestamp=1011000, type="trace", ref="t_0006"),
        TimelineEvent(timestamp=1012000, type="context", ref="c_0007"),
        TimelineEvent(timestamp=1013000, type="trace", ref="t_0007"),
    ]

    manifest = CaptureManifest(
        capture_id="seed-demo-api-001",
        created_at="2026-03-19T10:00:00Z",
        app=AppInfo(name="Demo Shop", base_url=BASE_URL, title="Demo Shop"),
        browser=BrowserInfo(name="Chrome", version="134.0"),
        duration_ms=13000,
        stats=CaptureStats(
            trace_count=len(traces),
            context_count=len(contexts),
        ),
    )

    return CaptureBundle(
        manifest=manifest,
        traces=traces,
        contexts=contexts,
        timeline=Timeline(events=events),
    )


# -- Main --------------------------------------------------------------------

def main() -> None:
    bundle = _build_bundle()

    # Remove existing app to allow re-seeding
    app_dir = store_root() / "apps" / APP_NAME
    if app_dir.exists():
        import shutil
        shutil.rmtree(app_dir)
        print(f"Removed existing {APP_NAME}")

    cap_dir = store_capture(bundle, APP_NAME, display_name="Demo Shop")
    print(f"Seeded {APP_NAME} → {cap_dir}")
    print(f"  {len(bundle.traces)} traces, {len(bundle.contexts)} contexts")
    print(f"\nVerify with:")
    print(f"  uv run spectral capture show {APP_NAME}")


if __name__ == "__main__":
    main()
