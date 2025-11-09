#Первая миграция создаём таблицу incidents, имя типов ENUM можно задать явно(по возможности), чтобы управлять ими в downgrade (по желанию))
from alembic import op
import sqlalchemy as sa
from app.domain.models import Status, Source

# revision identifiers, used by Alembic.
revision = "20251108_133921"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.Enum(Status), nullable=False, server_default=Status.NEW.name),
        sa.Column("source", sa.Enum(Source), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("incidents")
