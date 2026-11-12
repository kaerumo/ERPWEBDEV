"""enterprise foundation tables

Revision ID: 2f4d8a1b7c9e
Revises: 9c89c9a21e5b
"""
from alembic import op
import sqlalchemy as sa

revision = "2f4d8a1b7c9e"
down_revision = "9c89c9a21e5b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("equipment", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("asset_tag", sa.String(80), nullable=False, unique=True), sa.Column("description", sa.Text, nullable=False, server_default=""), sa.Column("status", sa.String(30), nullable=False, server_default="available"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("borrowing_requests", sa.Column("id", sa.Integer, primary_key=True), sa.Column("equipment_id", sa.Integer, sa.ForeignKey("equipment.id"), nullable=False), sa.Column("borrower_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("purpose", sa.Text, nullable=False), sa.Column("requested_from", sa.Date, nullable=False), sa.Column("due_date", sa.Date, nullable=False), sa.Column("returned_at", sa.DateTime(timezone=True)), sa.Column("condition", sa.String(30), nullable=False, server_default="good"), sa.Column("damage_notes", sa.Text, nullable=False, server_default=""), sa.Column("status", sa.String(30), nullable=False, server_default="pending"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("approval_requests", sa.Column("id", sa.Integer, primary_key=True), sa.Column("request_type", sa.String(40), nullable=False), sa.Column("reference_id", sa.Integer), sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("reviewed_by", sa.Integer, sa.ForeignKey("users.id")), sa.Column("status", sa.String(20), nullable=False, server_default="pending"), sa.Column("comments", sa.Text, nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_table("notifications", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("message", sa.Text, nullable=False), sa.Column("read_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("suppliers", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("contact_name", sa.String(120), nullable=False, server_default=""), sa.Column("email", sa.String(160), nullable=False, server_default=""), sa.Column("phone", sa.String(50), nullable=False, server_default=""), sa.Column("address", sa.String(255), nullable=False, server_default=""), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("purchase_records", sa.Column("id", sa.Integer, primary_key=True), sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.id"), nullable=False), sa.Column("description", sa.String(255), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("purchase_date", sa.Date, nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="recorded"), sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("expenses", sa.Column("id", sa.Integer, primary_key=True), sa.Column("category", sa.String(80), nullable=False), sa.Column("description", sa.String(255), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("expense_date", sa.Date, nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="submitted"), sa.Column("submitted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("budgets", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("category", sa.String(80), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("period_start", sa.Date, nullable=False), sa.Column("period_end", sa.Date, nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for table in ("budgets", "expenses", "purchase_records", "suppliers", "notifications", "approval_requests", "borrowing_requests", "equipment"):
        op.drop_table(table)
