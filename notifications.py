"""Mock notification hook.

In production this would call an SMS/WhatsApp/email API. For now it just
prints to the console (visible in the terminal running `streamlit run`)
so the rest of the app can be built and tested against a stable interface.
"""

NOTIFY_STATUSES = ("Dispatched", "Delivered")


def notify_status_change(order, new_status):
    """order is a dict with at least id, customer_name, customer_phone."""
    if new_status not in NOTIFY_STATUSES:
        return
    print(
        f"[NOTIFY] Order #{order['id']} for {order['customer_name']} "
        f"({order['customer_phone']}) is now {new_status}."
    )
