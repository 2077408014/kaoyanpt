"""port seven new features: supervision, ai_configs, email codes, password reset, knowledge documents + column additions

Revision ID: a1b2c3d4e5f6
Revises: 7051146a43b0
Create Date: 2026-09-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7051146a43b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 学习监督记录
    op.create_table('study_supervision_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('face_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_supervision_records_id'), 'study_supervision_records', ['id'], unique=False)
    op.create_index(op.f('ix_study_supervision_records_session_id'), 'study_supervision_records', ['session_id'], unique=False)
    op.create_index(op.f('ix_study_supervision_records_user_id'), 'study_supervision_records', ['user_id'], unique=False)

    # 用户 AI 多配置
    op.create_table('ai_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('api_key', sa.String(length=500), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_configs_id'), 'ai_configs', ['id'], unique=False)
    op.create_index(op.f('ix_ai_configs_user_id'), 'ai_configs', ['user_id'], unique=False)

    # 邮箱验证码
    op.create_table('email_verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_verification_codes_email'), 'email_verification_codes', ['email'], unique=False)
    op.create_index(op.f('ix_email_verification_codes_id'), 'email_verification_codes', ['id'], unique=False)

    # 密码重置验证码
    op.create_table('password_reset_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_codes_id'), 'password_reset_codes', ['id'], unique=False)
    op.create_index(op.f('ix_password_reset_codes_user_id'), 'password_reset_codes', ['user_id'], unique=False)

    # RAG 知识库文档
    op.create_table('knowledge_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('file_type', sa.String(length=20), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('subject', sa.String(length=50), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_documents_id'), 'knowledge_documents', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_user_id'), 'knowledge_documents', ['user_id'], unique=False)

    # ai_chat_history 增加智能体标识与相关片段
    with op.batch_alter_table('ai_chat_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_name', sa.String(length=50), nullable=False, server_default='ai-qa'))
        batch_op.add_column(sa.Column('relevant_chunks', sa.Text(), nullable=True))

    # users 表增加当前激活的 AI 配置（SQLite ALTER 不支持带 FK 的加列，故仅加整型列）
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active_ai_config_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('active_ai_config_id')

    with op.batch_alter_table('ai_chat_history', schema=None) as batch_op:
        batch_op.drop_column('relevant_chunks')
        batch_op.drop_column('agent_name')

    op.drop_index(op.f('ix_knowledge_documents_user_id'), table_name='knowledge_documents')
    op.drop_index(op.f('ix_knowledge_documents_id'), table_name='knowledge_documents')
    op.drop_table('knowledge_documents')

    op.drop_index(op.f('ix_password_reset_codes_user_id'), table_name='password_reset_codes')
    op.drop_index(op.f('ix_password_reset_codes_id'), table_name='password_reset_codes')
    op.drop_table('password_reset_codes')

    op.drop_index(op.f('ix_email_verification_codes_id'), table_name='email_verification_codes')
    op.drop_index(op.f('ix_email_verification_codes_email'), table_name='email_verification_codes')
    op.drop_table('email_verification_codes')

    op.drop_index(op.f('ix_ai_configs_user_id'), table_name='ai_configs')
    op.drop_index(op.f('ix_ai_configs_id'), table_name='ai_configs')
    op.drop_table('ai_configs')

    op.drop_index(op.f('ix_study_supervision_records_user_id'), table_name='study_supervision_records')
    op.drop_index(op.f('ix_study_supervision_records_session_id'), table_name='study_supervision_records')
    op.drop_index(op.f('ix_study_supervision_records_id'), table_name='study_supervision_records')
    op.drop_table('study_supervision_records')