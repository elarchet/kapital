from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from src.config import settings

# For sqlite, we need connect_args={"check_same_thread": False}
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


def init_db() -> None:
    """Initialize database and create all tables.

    Imports all models first to ensure they are registered with SQLAlchemy/SQLModel metadata.
    """
    # Import all models to register them on the metadata before calling create_all
    from src.models import SABase  # noqa: PLC0415

    SQLModel.metadata.create_all(engine)
    SABase.metadata.create_all(engine)

    # Seed default public templates
    import json  # noqa: PLC0415

    from sqlmodel import select  # noqa: PLC0415

    from src.models.import_file_schema import ImportFileSchema  # noqa: PLC0415

    with Session(engine) as session:
        t212 = session.exec(select(ImportFileSchema).where(ImportFileSchema.name == "Trading 212")).first()
        if not t212:
            t212_mappings = {
                "columns": {
                    "operation_type": "Action",
                    "executed_at": "Time",
                    "isin": "ISIN",
                    "ticker": "Ticker",
                    "name": "Name",
                    "notes": "Notes",
                    "transaction_id": "ID",
                    "quantity": "No. of shares",
                    "unit_price": "Price / share",
                    "currency": "Currency (Total)",
                    "total_amount": "Total",
                    "exchange_rate": "Exchange rate",
                    "fee_amount": "Currency conversion fee",
                    "fee_currency": "Currency (Currency conversion fee)",
                    "tax_amount": "Withholding tax",
                    "tax_currency": "Currency (Withholding tax)",
                    "merchant_name": "Merchant name",
                    "merchant_category": "Merchant category",
                },
                "type_mappings": {
                    "buy": ["Market buy", "Limit buy", "Stock split open"],
                    "sell": ["Market sell", "Limit sell", "Stock split close"],
                    "dividend": ["Dividend (Dividend)", "Dividend (Dividend manufactured payment)"],
                    "interest": ["Interest on cash", "Lending interest", "Spending cashback"],
                    "transfer_in": ["Deposit"],
                    "transfer_out": ["Withdrawal"],
                    "expense": ["Card debit"],
                    "revenue": ["Card credit"],
                    "fx_rate_change": ["Currency conversion"],
                },
                "scaling": {
                    "unit_price": {
                        "GBX": 0.01,
                    },
                    "total_amount": {
                        "GBX": 0.01,
                    },
                },
            }
            schema_obj = ImportFileSchema(
                name="Trading 212",
                is_public=True,
                delimiter=",",
                decimal_separator=".",
                mappings=json.dumps(t212_mappings),
            )
            session.add(schema_obj)
            session.commit()


def get_session() -> Generator[Session]:
    """Dependency injection generator yielding a SQLModel Session."""
    with Session(engine) as session:
        yield session
