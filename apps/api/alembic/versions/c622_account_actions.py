"""Single-use account links with an encrypted persistent mail queue."""
from alembic import op
import sqlalchemy as sa
revision = 'c622accounts'
down_revision = 'c621prescription'
branch_labels = depends_on = None


def upgrade():
    op.create_table('account_actions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('membership_id', sa.String(36), nullable=True),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('encrypted_token', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['membership_id'], ['memberships.id']))
    op.create_index('ix_account_actions_user_id', 'account_actions', ['user_id'])


def downgrade():
    op.drop_table('account_actions')
