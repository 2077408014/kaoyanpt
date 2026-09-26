"""class content (announcements/assignments), join-code policy, member status, force password change

Revision ID: d5e7f9a1b3c6
Revises: c4d6e8f0a2b5
Create Date: 2026-09-24 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e7f9a1b3c6'
down_revision: Union[str, Sequence[str], None] = 'c4d6e8f0a2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # users：管理员创建账号首次登录强制改密
    op.add_column(
        'users',
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )

    # classes：入班码时效 / 次数限制
    op.add_column('classes', sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('classes', sa.Column('code_max_uses', sa.Integer(), nullable=True))
    op.add_column(
        'classes',
        sa.Column('code_uses', sa.Integer(), nullable=False, server_default='0'),
    )

    # class_students：成员状态 active/suspended
    op.add_column(
        'class_students',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
    )

    # 班级公告
    op.create_table(
        'class_announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_class_announcements_id'), 'class_announcements', ['id'], unique=False)
    op.create_index(op.f('ix_class_announcements_class_id'), 'class_announcements', ['class_id'], unique=False)

    # 作业
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_assignments_id'), 'assignments', ['id'], unique=False)
    op.create_index(op.f('ix_assignments_class_id'), 'assignments', ['class_id'], unique=False)

    # 作业提交
    op.create_table(
        'assignment_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('graded_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['graded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_student'),
    )
    op.create_index(op.f('ix_assignment_submissions_id'), 'assignment_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_assignment_submissions_assignment_id'), 'assignment_submissions', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_assignment_submissions_student_id'), 'assignment_submissions', ['student_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_assignment_submissions_student_id'), table_name='assignment_submissions')
    op.drop_index(op.f('ix_assignment_submissions_assignment_id'), table_name='assignment_submissions')
    op.drop_index(op.f('ix_assignment_submissions_id'), table_name='assignment_submissions')
    op.drop_table('assignment_submissions')

    op.drop_index(op.f('ix_assignments_class_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_id'), table_name='assignments')
    op.drop_table('assignments')

    op.drop_index(op.f('ix_class_announcements_class_id'), table_name='class_announcements')
    op.drop_index(op.f('ix_class_announcements_id'), table_name='class_announcements')
    op.drop_table('class_announcements')

    with op.batch_alter_table('class_students') as batch:
        batch.drop_column('status')
    with op.batch_alter_table('classes') as batch:
        batch.drop_column('code_uses')
        batch.drop_column('code_max_uses')
        batch.drop_column('code_expires_at')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('must_change_password')
