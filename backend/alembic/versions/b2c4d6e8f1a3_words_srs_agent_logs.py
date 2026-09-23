"""words SRS/category/wordbook + agent collaboration logs

Revision ID: b2c4d6e8f1a3
Revises: a1b2c3d4e5f6
Create Date: 2026-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c4d6e8f1a3'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # words 表：去 unique，加 category/user_id（SQLite 无法 ALTER 加 FK 约束，仅加列与索引）
    op.drop_index('ix_words_word', table_name='words')
    op.create_index('ix_words_word', 'words', ['word'], unique=False)
    op.add_column('words', sa.Column('category', sa.String(length=20), nullable=False, server_default='CET-4'))
    op.add_column('words', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_words_user_id', 'words', ['user_id'], unique=False)

    # user_words 表：新增列
    op.add_column('user_words', sa.Column('first_study_date', sa.Date(), nullable=True))
    op.add_column('user_words', sa.Column('last_rating', sa.String(length=20), nullable=True))
    op.add_column('user_words', sa.Column('srs_stage', sa.Integer(), nullable=False, server_default='0'))

    # users 表：新增学习计划字段
    op.add_column('users', sa.Column('selected_word_category', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('batch_size', sa.Integer(), nullable=False, server_default='20'))
    op.add_column('users', sa.Column('study_mode', sa.String(length=20), nullable=False, server_default='mixed'))
    op.add_column('users', sa.Column('study_session_json', sa.Text(), nullable=True))

    # 智能体协作日志
    op.create_table('agent_collaboration_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('orchestrator_name', sa.String(length=100), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('total_time_ms', sa.Float(), nullable=False),
        sa.Column('consulted_agent_count', sa.Integer(), nullable=False),
        sa.Column('accepted_agent_count', sa.Integer(), nullable=False),
        sa.Column('recommendation_count', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_collaboration_logs_id'), 'agent_collaboration_logs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_collaboration_logs_request_id'), 'agent_collaboration_logs', ['request_id'], unique=False)

    op.create_table('agent_interaction_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('agent_domain', sa.String(length=100), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('recommendation_count', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_interaction_logs_id'), 'agent_interaction_logs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_interaction_logs_request_id'), 'agent_interaction_logs', ['request_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_interaction_logs_request_id'), table_name='agent_interaction_logs')
    op.drop_index(op.f('ix_agent_interaction_logs_id'), table_name='agent_interaction_logs')
    op.drop_table('agent_interaction_logs')
    op.drop_index(op.f('ix_agent_collaboration_logs_request_id'), table_name='agent_collaboration_logs')
    op.drop_index(op.f('ix_agent_collaboration_logs_id'), table_name='agent_collaboration_logs')
    op.drop_table('agent_collaboration_logs')
    op.drop_column('users', 'study_session_json')
    op.drop_column('users', 'study_mode')
    op.drop_column('users', 'batch_size')
    op.drop_column('users', 'selected_word_category')
    op.drop_column('user_words', 'srs_stage')
    op.drop_column('user_words', 'last_rating')
    op.drop_column('user_words', 'first_study_date')
    op.drop_index('ix_words_user_id', table_name='words')
    op.drop_column('words', 'user_id')
    op.drop_column('words', 'category')
    op.drop_index('ix_words_word', table_name='words')
    op.create_index('ix_words_word', 'words', ['word'], unique=True)