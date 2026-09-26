# KaoYanPT

考研陪伴平台（FastAPI + Vue 3 / Element Plus + SQLite）。

## 目录结构

```
KaoYanPT/
├── backend/
│   ├── app/
│   │   ├── api/          # 路由层（auth/teacher/institution/admin/classes）
│   │   ├── core/         # 数据库、依赖鉴权、表驱动迁移
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── schemas/      # Pydantic 模型
│   │   └── services/     # 业务逻辑
│   ├── alembic/          # Alembic 迁移
│   └── tests/            # 接口测试
├── frontend/
│   └── src/
│       ├── api/          # axios 封装
│       ├── components/   # 共用组件
│       ├── router/       # 路由（按角色守卫）
│       ├── stores/       # Pinia
│       └── views/        # admin / institution / teacher / student 四端页面
└── docs/                 # 设计与计划文档
```

## 开发与验证

- Python 环境：conda `kaoyanpt`（`/mnt/data_d/conda_envs/kaoyanpt/bin/python`）
- 后端测试：`cd backend && /mnt/data_d/conda_envs/kaoyanpt/bin/python tests/test_organization_api.py`
- 前端构建：`cd frontend && npm run build`
- 改动完成后先跑测试与构建，再向用户声明完成

## 角色模型

- 超级管理员（super_admin）：机构管理 + 员工账号管理；无班级管理写权限
- 机构管理者（institution_admin）：本机构班级、入班码、教师账号管理
- 教师（teacher）：所任班级的成员、公告、作业管理与学生数据查看
- 学生（student）：学习功能 + 加入班级、查看公告作业并提交

员工账号可同时具备学生身份（双重角色），登录后切换身份。
