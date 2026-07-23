"""Web app: Wholesale Packaging Order Management System (Phase 2).

Streamlit UI backed by db.py (SQLAlchemy / Postgres or SQLite), catalog.py
(product tree) and notifications.py (mock notification hook on
Dispatched/Delivered).
"""

import os

import streamlit as st

import catalog
import db
import notifications
from db import get_secret

st.set_page_config(page_title="Wholesale Packaging Orders", layout="wide")


# ---------------------------------------------------------------- auth ----

def check_auth():
    app_password = os.environ.get("APP_PASSWORD") or get_secret("APP_PASSWORD")
    if not app_password:
        # No password configured (e.g. local dev) -- skip the gate.
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("Wholesale Packaging Order Management System")
    st.text_input("Password", type="password", key="login_password")

    def do_login():
        if st.session_state.get("login_password") == app_password:
            st.session_state["authenticated"] = True
            st.session_state["login_error"] = None
        else:
            st.session_state["login_error"] = "Incorrect password."

    st.button("Login", on_click=do_login)
    if st.session_state.get("login_error"):
        st.error(st.session_state["login_error"])
    return False


# ---------------------------------------------------------- new order -----

def on_customer_picked(customer_options, customers):
    choice = st.session_state["customer_picker"]
    if choice == "-- New Customer --":
        return
    idx = customer_options.index(choice) - 1
    c = customers[idx]
    st.session_state["order_name"] = c["name"]
    st.session_state["order_phone"] = c["phone"]


def on_category_change():
    vs = catalog.variants(st.session_state["order_category"])
    st.session_state["order_variant"] = vs[0] if vs else None
    st.session_state.pop("order_grade", None)


def on_variant_change():
    st.session_state.pop("order_grade", None)


def submit_order():
    name = st.session_state.get("order_name", "").strip()
    phone = st.session_state.get("order_phone", "").strip()
    category = st.session_state.get("order_category")
    variant = st.session_state.get("order_variant")
    grade_options = catalog.grades(category, variant) if variant else []
    grade = st.session_state.get("order_grade") if grade_options else None
    weight = st.session_state.get("order_weight", 0)

    st.session_state["order_form_success"] = None
    st.session_state["order_form_error"] = None

    if not name or not phone:
        st.session_state["order_form_error"] = "Customer name and phone are required."
        return
    if not variant:
        st.session_state["order_form_error"] = "Please select a product variant."
        return
    if grade_options and not grade:
        st.session_state["order_form_error"] = "Please select a grade."
        return
    if not weight or weight <= 0:
        st.session_state["order_form_error"] = "Weight must be a positive number."
        return

    customer_id = db.get_or_create_customer(name, phone)
    order_id = db.create_order(customer_id, category, variant, grade, weight)

    st.session_state["order_form_success"] = f"Order #{order_id} created for {name}."
    st.session_state["order_name"] = ""
    st.session_state["order_phone"] = ""
    st.session_state["order_weight"] = 0.1
    st.session_state["customer_picker"] = "-- New Customer --"


def new_order_tab():
    customers = db.list_customers()
    customer_options = ["-- New Customer --"] + [
        f"{c['name']} ({c['phone']})" for c in customers
    ]
    if st.session_state.get("customer_picker") not in customer_options:
        st.session_state["customer_picker"] = customer_options[0]

    st.selectbox(
        "Existing Customer",
        customer_options,
        key="customer_picker",
        on_change=on_customer_picked,
        args=(customer_options, customers),
    )

    if "order_name" not in st.session_state:
        st.session_state["order_name"] = ""
    if "order_phone" not in st.session_state:
        st.session_state["order_phone"] = ""

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Customer Name", key="order_name")
    with col2:
        st.text_input("Phone", key="order_phone")

    categories = catalog.categories()
    if "order_category" not in st.session_state:
        st.session_state["order_category"] = categories[0]
    st.selectbox(
        "Category", categories, key="order_category", on_change=on_category_change
    )

    variant_options = catalog.variants(st.session_state["order_category"])
    if st.session_state.get("order_variant") not in variant_options:
        st.session_state["order_variant"] = variant_options[0] if variant_options else None
    st.selectbox(
        "Variant", variant_options, key="order_variant", on_change=on_variant_change
    )

    grade_options = catalog.grades(
        st.session_state["order_category"], st.session_state["order_variant"]
    )
    if grade_options:
        if st.session_state.get("order_grade") not in grade_options:
            st.session_state["order_grade"] = grade_options[0]
        st.selectbox("Grade", grade_options, key="order_grade")
    else:
        st.caption("This variant has no grade tiers.")
        st.session_state.pop("order_grade", None)

    if "order_weight" not in st.session_state:
        st.session_state["order_weight"] = 0.1
    st.number_input("Weight (kg)", min_value=0.1, step=0.5, key="order_weight")

    st.button("Create Order", on_click=submit_order)

    if st.session_state.get("order_form_error"):
        st.error(st.session_state["order_form_error"])
        st.session_state["order_form_error"] = None
    if st.session_state.get("order_form_success"):
        st.success(st.session_state["order_form_success"])
        st.session_state["order_form_success"] = None


# -------------------------------------------------------------- orders ----

def advance_order():
    order_id = st.session_state["selected_order_id"]
    order = db.get_order(order_id)
    nxt = db.next_status(order["status"])
    if nxt:
        updated = db.update_order_status(order_id, nxt)
        notifications.notify_status_change(updated, nxt)
        st.session_state["order_status_message"] = f"Order #{order_id} advanced to {nxt}."


@st.fragment(run_every="5s")
def orders_tab():
    st.caption("Auto-refreshes every 5s so updates from other devices show up here.")
    orders = db.list_orders()
    if not orders:
        st.info("No orders yet -- create one in the New Order tab.")
        return

    def fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

    rows = []
    for o in orders:
        product = f"{o['category']} / {o['variant']}"
        if o["grade"]:
            product += f" / {o['grade']}"
        rows.append(
            {
                "Order #": o["id"],
                "Customer": f"{o['customer_name']} ({o['customer_phone']})",
                "Product": product,
                "Weight (kg)": o["weight_kg"],
                "Status": o["status"],
                "Created": fmt(o["created_at"]),
                "Dispatched": fmt(o["dispatched_at"]),
                "Delivered": fmt(o["delivered_at"]),
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("Update Order Status")
    order_ids = [o["id"] for o in orders]
    if st.session_state.get("selected_order_id") not in order_ids:
        st.session_state["selected_order_id"] = order_ids[0]
    st.selectbox("Order #", order_ids, key="selected_order_id")

    selected_order = next(
        o for o in orders if o["id"] == st.session_state["selected_order_id"]
    )
    current_status = selected_order["status"]
    nxt = db.next_status(current_status)

    st.write(f"Current status: **{current_status}**")
    if nxt:
        st.button(f"Advance to {nxt}", on_click=advance_order)
    else:
        st.success("Order fully delivered.")

    if st.session_state.get("order_status_message"):
        st.success(st.session_state["order_status_message"])
        st.session_state["order_status_message"] = None


# ------------------------------------------------------------ customers ---

@st.fragment(run_every="5s")
def customers_tab():
    st.caption("Auto-refreshes every 5s so updates from other devices show up here.")
    stats = db.customer_stats()
    if not stats:
        st.info("No customers yet.")
        return
    rows = [
        {
            "Name": c["name"],
            "Phone": c["phone"],
            "Order Count": c["order_count"],
            "Total Weight (kg)": c["total_weight_kg"],
        }
        for c in stats
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


# ------------------------------------------------------------------ main --

def main():
    db.init_db()

    if not check_auth():
        st.stop()

    st.title("Wholesale Packaging Order Management System")

    tab1, tab2, tab3 = st.tabs(["New Order", "Orders", "Customers"])
    with tab1:
        new_order_tab()
    with tab2:
        orders_tab()
    with tab3:
        customers_tab()


if __name__ == "__main__":
    main()
