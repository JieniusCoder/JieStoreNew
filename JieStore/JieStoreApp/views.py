from decimal import Decimal
import os
import json
from base64 import b64encode
from typing import Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Item, UserCart, UserCartItem


def _google_env_keys_present() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID", "") and os.getenv("GOOGLE_CLIENT_SECRET", ""))


def _missing_google_keys_popup(redirect_url: str = "/items/") -> HttpResponse:
    # Minimal HTML + JS alert (no secrets).
    return HttpResponse(
        f"""<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Missing Google keys</title></head>
  <body>
    <script>
      alert("Missing Google API keys. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env, then restart the server.");
      window.location.href = {redirect_url!r};
    </script>
  </body>
</html>""",
        content_type="text/html",
        status=400,
    )


def _ensure_google_socialapp_configured(request) -> bool:
    """
    If GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET exist in env, ensure allauth SocialApp + Site
    are configured for the current host.
    """
    if not _google_env_keys_present():
        return False

    try:
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
    except Exception:
        return False

    host = request.get_host()
    site, _ = Site.objects.get_or_create(
        id=getattr(settings, "SITE_ID", 1),
        defaults={"domain": host, "name": host},
    )
    if site.domain != host or site.name != host:
        site.domain = host
        site.name = host
        site.save(update_fields=["domain", "name"])

    app, _ = SocialApp.objects.get_or_create(
        provider="google",
        defaults={
            "name": "Google",
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
    )
    changed = False
    if app.client_id != os.getenv("GOOGLE_CLIENT_ID", ""):
        app.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        changed = True
    if app.secret != os.getenv("GOOGLE_CLIENT_SECRET", ""):
        app.secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        changed = True
    if changed:
        app.save(update_fields=["client_id", "secret"])

    if not app.sites.filter(id=site.id).exists():
        app.sites.add(site)

    return True

# Create your views here.
def home(request):
    return render(request, 'home.html')

_CART_SESSION_KEY = "cart"  # { "<item_id>": <qty_int> }


def _get_cart(request) -> dict:
    cart = request.session.get(_CART_SESSION_KEY)
    if not isinstance(cart, dict):
        cart = {}
        request.session[_CART_SESSION_KEY] = cart
    return cart


def _session_cart_count(cart: dict) -> int:
    total = 0
    for qty in cart.values():
        try:
            total += int(qty)
        except (TypeError, ValueError):
            continue
    return total


def _get_or_create_user_cart(user):
    cart, _ = UserCart.objects.get_or_create(user=user)
    return cart


def _user_cart_count(user) -> int:
    total = (
        UserCartItem.objects.filter(cart__user=user).aggregate(total=Sum("qty")).get("total")
        or 0
    )
    return int(total)


def _get_user_cart_rows(user):
    rows = []
    total = Decimal("0.00")
    qs = UserCartItem.objects.filter(cart__user=user).select_related("item")
    for row in qs:
        qty = int(row.qty or 0)
        if qty <= 0:
            continue
        item = row.item
        subtotal = (item.price or Decimal("0.00")) * qty
        total += subtotal
        rows.append({"item": item, "qty": qty, "subtotal": subtotal})
    return rows, total


def _clear_user_cart(user):
    UserCartItem.objects.filter(cart__user=user).delete()


def _redirect_back(request, fallback_url_name: str):
    ref = request.META.get("HTTP_REFERER")
    if ref and url_has_allowed_host_and_scheme(
        url=ref,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(ref)
    return redirect(fallback_url_name)


def _google_login_url() -> str:
    try:
        return reverse("google_login")
    except NoReverseMatch:
        return "/accounts/google/login/"


def _redirect_to_google_login(request, next_path: str):
    url = _google_login_url()
    if next_path:
        return redirect(f"{url}?next={next_path}")
    return redirect(url)


def login(request):
    if not _ensure_google_socialapp_configured(request):
        return _missing_google_keys_popup("/items/")
    return _redirect_to_google_login(request, request.GET.get("next", "/items/"))


def item_list(request):
    items = Item.objects.all()
    in_cart_ids = []

    if request.user.is_authenticated:
        qs = UserCartItem.objects.filter(cart__user=request.user, qty__gt=0).values_list("item_id", flat=True)
        in_cart_ids = list(qs)
        cart_count = _user_cart_count(request.user)
    else:
        cart = _get_cart(request)
        for item_id, qty in cart.items():
            try:
                if int(qty) > 0:
                    in_cart_ids.append(int(item_id))
            except (TypeError, ValueError):
                continue
        cart_count = _session_cart_count(cart)

    return render(
        request,
        "item_list.html",
        {
            "items": items,
            "cart_count": cart_count,
            "in_cart_ids": in_cart_ids,
        },
    )

@login_required
def cart_view(request):
    rows, total = _get_user_cart_rows(request.user)
    return render(
        request,
        "cart.html",
        {
            "cart_items": rows,
            "total": total,
            "cart_count": _user_cart_count(request.user),
        },
    )


def _get_cart_rows(request):
    # For checkout/payment paths we require login, so use DB cart.
    if request.user.is_authenticated:
        rows, total = _get_user_cart_rows(request.user)
        return rows, total, None
    rows = []
    return rows, Decimal("0.00"), None


def _clear_cart(request):
    # Legacy session cart (kept for merging on login).
    request.session[_CART_SESSION_KEY] = {}
    request.session.modified = True


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))


def _to_cents(amount: Decimal) -> int:
    return int((_money(amount) * 100).quantize(Decimal("1")))


def start_add_to_cart(request, item_id: int):
    """
    Anonymous entry point: stash item in session cart, then redirect to Google OAuth.
    On login, `merge_session_cart_into_user_cart` moves it into the DB cart.
    """
    get_object_or_404(Item, id=item_id)

    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        row, created = UserCartItem.objects.get_or_create(cart=cart, item_id=item_id, defaults={"qty": 1})
        if not created:
            row.qty = row.qty + 1
            row.save(update_fields=["qty"])
        return _redirect_back(request, "storefront")

    if not _ensure_google_socialapp_configured(request):
        return _missing_google_keys_popup("/items/")

    cart = _get_cart(request)
    key = str(item_id)
    try:
        cart[key] = int(cart.get(key, 0)) + 1
    except (TypeError, ValueError):
        cart[key] = 1
    request.session.modified = True

    next_path = request.META.get("HTTP_REFERER") or "/items/"
    if next_path.startswith("http"):
        try:
            next_path = "/" + next_path.split("/", 3)[3]
        except Exception:
            next_path = "/items/"

    return _redirect_to_google_login(request, next_path)


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@require_POST
@login_required
def add_to_cart(request, item_id: int):
    get_object_or_404(Item, id=item_id)
    cart = _get_or_create_user_cart(request.user)
    row, created = UserCartItem.objects.get_or_create(cart=cart, item_id=item_id, defaults={"qty": 1})
    if not created:
        row.qty = row.qty + 1
        row.save(update_fields=["qty"])
    if _wants_json(request):
        return JsonResponse({
            "success": True,
            "cart_count": _user_cart_count(request.user),
            "in_cart": True,
        })
    return _redirect_back(request, "storefront")


@require_POST
@login_required
def remove_from_cart(request, item_id: int):
    UserCartItem.objects.filter(cart__user=request.user, item_id=item_id).delete()
    if _wants_json(request):
        return JsonResponse({
            "success": True,
            "cart_count": _user_cart_count(request.user),
            "in_cart": False,
        })
    return _redirect_back(request, "storefront")


@ensure_csrf_cookie
@login_required
def checkout(request):
    rows, total, cart = _get_cart_rows(request)

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
    paypal_env = os.getenv("PAYPAL_ENV", "sandbox")

    stripe_enabled = bool(stripe_secret_key)
    paypal_enabled = bool(paypal_client_id and paypal_client_secret)

    return render(
        request,
        "checkout.html",
        {
            "cart_items": rows,
            "total": _money(total),
            "cart_count": _user_cart_count(request.user),
            "stripe_enabled": stripe_enabled,
            "stripe_publishable_key": stripe_publishable_key,
            "paypal_client_id": paypal_client_id,
            "paypal_enabled": paypal_enabled,
            "paypal_env": paypal_env,
            "debug": settings.DEBUG,
            "config_status": {
                "stripe_secret_present": bool(stripe_secret_key),
                "stripe_secret_prefix": (stripe_secret_key[:7] if stripe_secret_key else ""),
                "stripe_publishable_present": bool(stripe_publishable_key),
                "stripe_publishable_prefix": (stripe_publishable_key[:7] if stripe_publishable_key else ""),
                "paypal_client_id_present": bool(paypal_client_id),
                "paypal_client_id_prefix": (paypal_client_id[:10] if paypal_client_id else ""),
                "paypal_client_secret_present": bool(paypal_client_secret),
                "paypal_env": paypal_env,
            },
        },
    )


@require_POST
@login_required
def stripe_create_checkout_session(request):
    import stripe

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_secret_key:
        return redirect("checkout")

    rows, total, _cart = _get_cart_rows(request)
    if not rows:
        return redirect("checkout")

    stripe.api_key = stripe_secret_key

    line_items = []
    for row in rows:
        item = row["item"]
        qty = row["qty"]
        unit_amount = _to_cents(item.price or Decimal("0.00"))
        if unit_amount <= 0:
            continue
        line_items.append(
            {
                "quantity": qty,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_amount,
                    "product_data": {"name": item.name},
                },
            }
        )

    if not line_items:
        return redirect("checkout")

    success_url = request.build_absolute_uri("/checkout/success/?provider=stripe&session_id={CHECKOUT_SESSION_ID}")
    cancel_url = request.build_absolute_uri("/checkout/cancel/?provider=stripe")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    request.session["stripe_checkout_session_id"] = session.id
    request.session["stripe_expected_total_cents"] = _to_cents(total)
    request.session.modified = True

    return redirect(session.url, permanent=False)


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe server-to-server webhook endpoint.
    We validate signature if STRIPE_WEBHOOK_SECRET is set.
    Cart clearing is handled on the success page after verification because webhooks
    are not tied to a specific browser session.
    """
    import stripe

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if webhook_secret:
        try:
            stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
        except Exception:
            return JsonResponse({"ok": False}, status=400)

    return JsonResponse({"ok": True})


def _paypal_base_url() -> str:
    env = os.getenv("PAYPAL_ENV", "sandbox").strip().lower()
    return "https://api-m.sandbox.paypal.com" if env != "live" else "https://api-m.paypal.com"


def _paypal_access_token() -> Optional[str]:
    import requests

    client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    basic = b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    r = requests.post(
        f"{_paypal_base_url()}/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data="grant_type=client_credentials",
        timeout=15,
    )
    if r.status_code >= 400:
        return None
    return r.json().get("access_token")


@require_POST
@login_required
def paypal_create_order(request):
    import requests

    rows, total, _cart = _get_cart_rows(request)
    if not rows:
        return JsonResponse({"error": "Cart is empty."}, status=400)

    token = _paypal_access_token()
    if not token:
        return JsonResponse(
            {"error": "PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET."},
            status=400,
        )

    total = _money(total)
    items = []
    item_total = Decimal("0.00")
    for row in rows:
        item = row["item"]
        qty = int(row["qty"])
        unit = _money(item.price or Decimal("0.00"))
        if unit <= 0 or qty <= 0:
            continue
        item_total += unit * qty
        items.append(
            {
                "name": item.name[:127],
                "unit_amount": {"currency_code": "USD", "value": f"{unit:.2f}"},
                "quantity": str(qty),
            }
        )

    item_total = _money(item_total)
    if item_total <= 0:
        return JsonResponse({"error": "Cart total must be > 0."}, status=400)

    # Keep order totals consistent with our server calculation
    total = item_total

    r = requests.post(
        f"{_paypal_base_url()}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{total:.2f}",
                        "breakdown": {
                            "item_total": {"currency_code": "USD", "value": f"{item_total:.2f}"},
                        },
                    },
                    "items": items,
                }
            ],
        },
        timeout=20,
    )
    if r.status_code >= 400:
        return JsonResponse({"error": "Failed to create PayPal order.", "details": r.text[:500]}, status=400)

    order_id = r.json().get("id")
    if not order_id:
        return JsonResponse({"error": "Invalid PayPal order response."}, status=400)

    request.session["paypal_order_id"] = order_id
    request.session["paypal_expected_total"] = f"{total:.2f}"
    request.session.modified = True

    return JsonResponse({"orderID": order_id})


@require_POST
@login_required
def paypal_redirect_checkout(request):
    """
    Create PayPal order and redirect to PayPal (same window).
    Avoids the about:blank popup issue with the JS SDK.
    """
    import requests

    rows, total, _cart = _get_cart_rows(request)
    if not rows:
        return redirect("checkout")

    token = _paypal_access_token()
    if not token:
        return redirect("checkout")

    total = _money(total)
    items = []
    item_total = Decimal("0.00")
    for row in rows:
        item = row["item"]
        qty = int(row["qty"])
        unit = _money(item.price or Decimal("0.00"))
        if unit <= 0 or qty <= 0:
            continue
        item_total += unit * qty
        items.append(
            {
                "name": item.name[:127],
                "unit_amount": {"currency_code": "USD", "value": f"{unit:.2f}"},
                "quantity": str(qty),
            }
        )

    item_total = _money(item_total)
    if item_total <= 0:
        return redirect("checkout")

    total = item_total

    return_url = request.build_absolute_uri(reverse("paypal_return"))
    cancel_url = request.build_absolute_uri(reverse("checkout_cancel"))

    r = requests.post(
        f"{_paypal_base_url()}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "intent": "CAPTURE",
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{total:.2f}",
                        "breakdown": {
                            "item_total": {"currency_code": "USD", "value": f"{item_total:.2f}"},
                        },
                    },
                    "items": items,
                }
            ],
        },
        timeout=20,
    )
    if r.status_code >= 400:
        return redirect("checkout")

    data = r.json()
    order_id = data.get("id")
    if not order_id:
        return redirect("checkout")

    approve_url = None
    for link in data.get("links", []):
        if link.get("rel") == "approve":
            approve_url = link.get("href")
            break

    if not approve_url:
        return redirect("checkout")

    request.session["paypal_order_id"] = order_id
    request.session["paypal_expected_total"] = f"{total:.2f}"
    request.session.modified = True

    return redirect(approve_url)


@login_required
def paypal_return(request):
    """
    Handle redirect back from PayPal after approval.
    Captures the order and redirects to success.
    """
    import requests

    token_param = request.GET.get("token")
    if not token_param:
        return redirect("checkout")

    if request.session.get("paypal_order_id") != token_param:
        return redirect("checkout")

    order_id = token_param
    paypal_token = _paypal_access_token()
    if not paypal_token:
        return redirect("checkout")

    r = requests.post(
        f"{_paypal_base_url()}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {paypal_token}",
            "Content-Type": "application/json",
        },
        timeout=20,
    )
    if r.status_code >= 400:
        return redirect("checkout")

    data = r.json()
    if data.get("status") != "COMPLETED":
        return redirect("checkout")

    expected = request.session.get("paypal_expected_total")
    try:
        capture_amount = data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
    except Exception:
        capture_amount = None

    if expected and capture_amount and expected != capture_amount:
        return redirect("checkout")

    _clear_user_cart(request.user)
    _clear_cart(request)
    request.session.pop("paypal_order_id", None)
    request.session.pop("paypal_expected_total", None)
    request.session.modified = True

    return redirect(reverse("checkout_success") + "?provider=paypal")


@require_POST
@login_required
def paypal_capture_order(request):
    import requests

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}
    order_id = payload.get("orderID")
    if not order_id:
        return JsonResponse({"error": "Missing orderID."}, status=400)

    if request.session.get("paypal_order_id") != order_id:
        return JsonResponse({"error": "Order/session mismatch."}, status=400)

    token = _paypal_access_token()
    if not token:
        return JsonResponse(
            {"error": "PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET."},
            status=400,
        )

    r = requests.post(
        f"{_paypal_base_url()}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=20,
    )
    if r.status_code >= 400:
        return JsonResponse({"error": "Failed to capture PayPal order.", "details": r.text[:500]}, status=400)

    data = r.json()
    if data.get("status") != "COMPLETED":
        return JsonResponse({"error": "PayPal payment not completed.", "status": data.get("status")}, status=400)

    expected = request.session.get("paypal_expected_total")
    try:
        capture_amount = data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
    except Exception:
        capture_amount = None

    if expected and capture_amount and expected != capture_amount:
        return JsonResponse({"error": "Amount mismatch."}, status=400)

    _clear_user_cart(request.user)
    request.session.pop("paypal_order_id", None)
    request.session.pop("paypal_expected_total", None)
    request.session.modified = True

    return JsonResponse({"ok": True})


@login_required
def checkout_success(request):
    provider = request.GET.get("provider", "")
    if provider == "stripe":
        import stripe

        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        if not stripe_secret_key:
            return render(request, "checkout_error.html", {"message": "Stripe is not configured."})

        session_id = request.GET.get("session_id", "")
        if not session_id:
            return render(request, "checkout_error.html", {"message": "Missing Stripe session id."})

        expected_session_id = request.session.get("stripe_checkout_session_id")
        if expected_session_id and expected_session_id != session_id:
            return render(request, "checkout_error.html", {"message": "Session mismatch."})

        stripe.api_key = stripe_secret_key
        try:
            s = stripe.checkout.Session.retrieve(session_id)
        except Exception:
            return render(request, "checkout_error.html", {"message": "Unable to verify Stripe session."})

        if getattr(s, "payment_status", None) != "paid":
            return render(request, "checkout_error.html", {"message": "Stripe payment is not paid yet."})

        expected_total = request.session.get("stripe_expected_total_cents")
        if expected_total is not None and getattr(s, "amount_total", None) != expected_total:
            return render(request, "checkout_error.html", {"message": "Amount mismatch."})

        _clear_user_cart(request.user)
        _clear_cart(request)
        request.session.pop("stripe_checkout_session_id", None)
        request.session.pop("stripe_expected_total_cents", None)
        request.session.modified = True
        return render(request, "checkout_success.html", {})

    if provider == "paypal":
        _clear_user_cart(request.user)
        _clear_cart(request)
        request.session.pop("paypal_order_id", None)
        request.session.pop("paypal_expected_total", None)
        request.session.modified = True
        return render(request, "checkout_success.html", {})

    return render(request, "checkout_success.html", {})


def checkout_cancel(request):
    return render(request, "checkout_cancel.html", {})