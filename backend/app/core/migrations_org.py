"""多角色与班级体系的轻量启动迁移。

项目主要使用 SQLite 并以 Base.metadata.create_all() 启动建表。
create_all 只会创建缺失的表，不会给已存在的表补列，
因此这里在启动时检查并 ALTER TABLE 添加后续版本引入的列。
存量数据由列默认值自动补齐。
"""
from sqlalchemy import text
from .database import engine

# 表 -> (列名, ALTER 片段)
_PENDING_COLUMNS = {
    "users": [
        ("role", "VARCHAR(20) NOT NULL DEFAULT 'student'"),
        ("institution_id", "INTEGER"),
        ("must_change_password", "BOOLEAN NOT NULL DEFAULT 0"),
    ],
    "classes": [
        ("code_expires_at", "DATETIME"),
        ("code_max_uses", "INTEGER"),
        ("code_uses", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "class_students": [
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'"),
    ],
    "assignments": [
        ("images", "TEXT NOT NULL DEFAULT '[]'"),
    ],
    "assignment_submissions": [
        ("images", "TEXT NOT NULL DEFAULT '[]'"),
    ],
}


def _existing_columns(conn, table: str) -> set[str]:
    if engine.dialect.name == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {r[1] for r in rows}
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table"
        ),
        {"table": table},
    ).fetchall()
    return {r[0] for r in rows}


def run_org_migration() -> None:
    with engine.begin() as conn:
        for table, pending in _PENDING_COLUMNS.items():
            columns = _existing_columns(conn, table)
            if not columns:
                # 表尚不存在：全新库由 create_all 按新模型建表
                continue
            for column, ddl_type in pending:
                if column not in columns:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                    )
