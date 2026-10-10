import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool



PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = PROJECT_ROOT / "apps"

sys.path.insert(0, str(APPS_DIR))

from backend.database import Base, settings
from backend.messages.models import TicketMessage
from backend.tickets.models import Ticket
from backend.users.models import User
from backend.activity.models import TicketActivity
from backend.orders.models import Order
from backend.payments.models import Payment
from backend.policies.models import PolicyDocument, PolicyChunk
from backend.ai.models import BillingAnalysisRecord
from backend.shipments.models import Shipment
from backend.approvals.models import ApprovalRequest

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "pyformat"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    if configuration is None:
        raise RuntimeError("Alembic configuration section is missing")

    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()