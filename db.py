"""SQLAlchemy data access layer for the web app.

Uses DATABASE_URL (env var or Streamlit secret) when present -- pointing at
Postgres in production. Falls back to a local SQLite file when no
DATABASE_URL is configured, so the app runs out of the box for local dev.
"""

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

STATUS_FLOW = ["Received", "Packing", "Packed", "Dispatched", "Delivered"]


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    category = Column(String, nullable=False)
    variant = Column(String, nullable=False)
    grade = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="Received")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    dispatched_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orders")


def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return None


def _database_url():
    url = os.environ.get("DATABASE_URL") or get_secret("DATABASE_URL")
    if not url:
        db_path = Path(__file__).parent / "orders.db"
        return f"sqlite:///{db_path}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


@st.cache_resource
def get_engine():
    url = _database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    Session = sessionmaker(bind=get_engine())
    return Session()


def _order_to_dict(o: Order):
    return {
        "id": o.id,
        "customer_id": o.customer_id,
        "customer_name": o.customer.name,
        "customer_phone": o.customer.phone,
        "category": o.category,
        "variant": o.variant,
        "grade": o.grade,
        "weight_kg": o.weight_kg,
        "status": o.status,
        "created_at": o.created_at,
        "dispatched_at": o.dispatched_at,
        "delivered_at": o.delivered_at,
    }


def _customer_to_dict(c: Customer):
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "created_at": c.created_at,
    }


def init_db():
    get_engine()


def get_or_create_customer(name, phone):
    session = get_session()
    try:
        customer = session.query(Customer).filter_by(phone=phone).first()
        if customer:
            if name and name != customer.name:
                customer.name = name
                session.commit()
            return customer.id
        customer = Customer(name=name, phone=phone, created_at=datetime.utcnow())
        session.add(customer)
        session.commit()
        return customer.id
    finally:
        session.close()


def find_customer_by_phone(phone):
    session = get_session()
    try:
        customer = session.query(Customer).filter_by(phone=phone).first()
        return _customer_to_dict(customer) if customer else None
    finally:
        session.close()


def list_customers():
    session = get_session()
    try:
        customers = session.query(Customer).order_by(Customer.name).all()
        return [_customer_to_dict(c) for c in customers]
    finally:
        session.close()


def create_order(customer_id, category, variant, grade, weight_kg):
    session = get_session()
    try:
        order = Order(
            customer_id=customer_id,
            category=category,
            variant=variant,
            grade=grade,
            weight_kg=weight_kg,
            status="Received",
            created_at=datetime.utcnow(),
        )
        session.add(order)
        session.commit()
        return order.id
    finally:
        session.close()


def list_orders():
    session = get_session()
    try:
        orders = session.query(Order).order_by(Order.id.desc()).all()
        return [_order_to_dict(o) for o in orders]
    finally:
        session.close()


def get_order(order_id):
    session = get_session()
    try:
        order = session.query(Order).filter_by(id=order_id).first()
        return _order_to_dict(order) if order else None
    finally:
        session.close()


def next_status(current_status):
    idx = STATUS_FLOW.index(current_status)
    if idx + 1 < len(STATUS_FLOW):
        return STATUS_FLOW[idx + 1]
    return None


def update_order_status(order_id, new_status):
    if new_status not in STATUS_FLOW:
        raise ValueError(f"Invalid status: {new_status}")
    session = get_session()
    try:
        order = session.query(Order).filter_by(id=order_id).first()
        order.status = new_status
        now = datetime.utcnow()
        if new_status == "Dispatched":
            order.dispatched_at = now
        elif new_status == "Delivered":
            order.delivered_at = now
        session.commit()
        return _order_to_dict(order)
    finally:
        session.close()


def delete_order(order_id):
    session = get_session()
    try:
        session.query(Order).filter_by(id=order_id).delete()
        session.commit()
    finally:
        session.close()


def customer_stats():
    session = get_session()
    try:
        customers = session.query(Customer).order_by(Customer.name).all()
        stats = []
        for c in customers:
            order_count = len(c.orders)
            total_weight = sum(o.weight_kg for o in c.orders)
            stats.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "order_count": order_count,
                    "total_weight_kg": total_weight,
                }
            )
        return stats
    finally:
        session.close()
