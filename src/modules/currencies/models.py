from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
