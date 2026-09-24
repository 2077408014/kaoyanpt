"""words toastfish features: srs 4-grade + study_records + push settings

Revision ID: a3b4c5d6e7f8
Revises: b2c4d6e8f1a3
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'b2c4d6e8f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # user_words：SM2+ 四档状态列
    op.add_column('user_words', sa.Column('srs_status', sa.String(length=20), nullable=False, server_default='new'))
    op.add_column('user_words', sa.Column('difficulty', sa.Float(), nullable=False, server_default='0.3'))
    op.add_column('user_words', sa.Column('days_between_reviews', sa.Float(), nullable=False, server_default='3.0'))

    # 存量数据迁移：已学过的按旧间隔序列初始化
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, srs_stage FROM user_words WHERE srs_stage > 0")).fetchall()
    for rid, stage in rows:
        days = [1, 3, 7, 15][min(stage, 3)]
        conn.execute(
            sa.text("UPDATE user_words SET srs_status='reviewed', days_between_reviews=:d WHERE id=:i"),
            {"d": float(days), "i": rid},
        )

    # users：弹卡配置
    op.add_column('users', sa.Column('push_settings_json', sa.Text(), nullable=True))

    # study_records 审计表
    op.create_table('study_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=50), nullable=False),
        sa.Column('phonetic', sa.String(length=100), nullable=True),
        sa.Column('meaning', sa.Text(), nullable=False),
        sa.Column('rating', sa.String(length=20), nullable=False),
        sa.Column('quiz_result', sa.Boolean(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='card'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_records_id'), 'study_records', ['id'], unique=False)
    op.create_index(op.f('ix_study_records_session_id'), 'study_records', ['session_id'], unique=False)
    op.create_index(op.f('ix_study_records_user_id'), 'study_records', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_study_records_user_id'), table_name='study_records')
    op.drop_index(op.f('ix_study_records_session_id'), table_name='study_records')
    op.drop_index(op.f('ix_study_records_id'), table_name='study_records')
    op.drop_table('study_records')
    op.drop_column('users', 'push_settings_json')
    op.drop_column('user_words', 'days_between_reviews')
    op.drop_column('user_words', 'difficulty')
    op.drop_column('user_words', 'srs_status')