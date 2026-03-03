import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── relationships ──
    created_groups = relationship("Group", back_populates="creator", foreign_keys="Group.created_by")
    group_memberships = relationship("GroupMember", back_populates="user")
    paid_expenses = relationship("Expense", back_populates="payer", foreign_keys="Expense.paid_by")
    created_expenses = relationship("Expense", back_populates="creator", foreign_keys="Expense.created_by")
    expense_splits = relationship("ExpenseSplit", back_populates="user")
    sent_settlements = relationship("Settlement", back_populates="payer", foreign_keys="Settlement.payer_id")
    received_settlements = relationship("Settlement", back_populates="receiver", foreign_keys="Settlement.receiver_id")
