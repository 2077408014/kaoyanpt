"""multi role + organization/class system

Revision ID: c4d6e8f0a2b5
Revises: a3b4c5d6e7f8
Create Date: 2026-09-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d6e8f0a2b5'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # users 表：角色与所属机构（SQLite 仅加列，不强制外键约束）
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='student'))
    op.add_column('users', sa.Column('institution_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_institution_id', 'users', ['institution_id'], unique=False)

    # 机构
    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_institutions_name'),
    )
    op.create_index(op.f('ix_institutions_id'), 'institutions', ['id'], unique=False)

    # 班级
    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('join_code', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('institution_id', 'name', name='uq_class_institution_name'),
    )
    op.create_index(op.f('ix_classes_id'), 'classes', ['id'], unique=False)
    op.create_index(op.f('ix_classes_institution_id'), 'classes', ['institution_id'], unique=False)
    op.create_index(op.f('ix_classes_join_code'), 'classes', ['join_code'], unique=True)

    # 班级-教师（多对多）
    op.create_table(
        'class_teachers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_id', 'teacher_id', name='uq_class_teacher'),
    )
    op.create_index(op.f('ix_class_teachers_id'), 'class_teachers', ['id'], unique=False)
    op.create_index(op.f('ix_class_teachers_class_id'), 'class_teachers', ['class_id'], unique=False)
    op.create_index(op.f('ix_class_teachers_teacher_id'), 'class_teachers', ['teacher_id'], unique=False)

    # 班级-学生（多对多）
    op.create_table(
        'class_students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_id', 'student_id', name='uq_class_student'),
    )
    op.create_index(op.f('ix_class_students_id'), 'class_students', ['id'], unique=False)
    op.create_index(op.f('ix_class_students_class_id'), 'class_students', ['class_id'], unique=False)
    op.create_index(op.f('ix_class_students_student_id'), 'class_students', ['student_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_class_students_student_id'), table_name='class_students')
    op.drop_index(op.f('ix_class_students_class_id'), table_name='class_students')
    op.drop_index(op.f('ix_class_students_id'), table_name='class_students')
    op.drop_table('class_students')

    op.drop_index(op.f('ix_class_teachers_teacher_id'), table_name='class_teachers')
    op.drop_index(op.f('ix_class_teachers_class_id'), table_name='class_teachers')
    op.drop_index(op.f('ix_class_teachers_id'), table_name='class_teachers')
    op.drop_table('class_teachers')

    op.drop_index(op.f('ix_classes_join_code'), table_name='classes')
    op.drop_index(op.f('ix_classes_institution_id'), table_name='classes')
    op.drop_index(op.f('ix_classes_id'), table_name='classes')
    op.drop_table('classes')

    op.drop_index(op.f('ix_institutions_id'), table_name='institutions')
    op.drop_table('institutions')

    op.drop_index('ix_users_institution_id', table_name='users')
    op.drop_column('users', 'institution_id')
    op.drop_column('users', 'role')
