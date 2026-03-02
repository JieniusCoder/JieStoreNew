from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import UserCart, UserCartItem


@receiver(user_logged_in)
def merge_session_cart_into_user_cart(sender, request, user, **kwargs):
    cart = request.session.get("cart")
    if not isinstance(cart, dict) or not cart:
        return

    user_cart, _ = UserCart.objects.get_or_create(user=user)

    for raw_item_id, raw_qty in cart.items():
        try:
            item_id = int(raw_item_id)
            qty = int(raw_qty)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue

        row, created = UserCartItem.objects.get_or_create(cart=user_cart, item_id=item_id, defaults={"qty": qty})
        if not created:
            row.qty = row.qty + qty
            row.save(update_fields=["qty"])

    request.session["cart"] = {}
    request.session.modified = True

