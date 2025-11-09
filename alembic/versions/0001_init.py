from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "weather_queries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city", sa.String(255), nullable=False, index=True),
        sa.Column("units", sa.String(10), nullable=False),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("raw_json", sa.JSON, nullable=False),
        sa.Column("from_cache", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_weather_queries_created_at", "weather_queries", ["created_at"])
    op.create_index("ix_weather_queries_city_ci", "weather_queries", [sa.text("LOWER(city)")])

def downgrade():
    op.drop_table("weather_queries")
