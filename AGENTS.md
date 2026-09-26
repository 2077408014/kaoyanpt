# KaoYanPT 项目说明

考研陪伴平台：FastAPI 后端 + Vue 3 / Element Plus 前端。

## 环境

- Python 依赖安装在 conda 的 `kaoyanpt` 环境（解释器 `/mnt/data_d/conda_envs/kaoyanpt/bin/python`）
- 真实数据库为项目根目录的 `kaoyan_xt.db`（SQLite，已被 git 忽略，勿提交）
- 后端开发：`uvicorn app.main:app --port 8000 --reload`（在 `backend/` 下）
- 前端开发：`npm run dev`（在 `frontend/` 下，Vite 5173 代理 `/api` 到 8000）

## 验证

- 后端测试：`cd backend && /mnt/data_d/conda_envs/kaoyanpt/bin/python tests/test_organization_api.py`
- 前端构建（含 vue-tsc 类型检查）：`cd frontend && npm run build`

## 约定

- 代码改动后须跑后端测试与前端构建再交付
- 不要执行 git commit / push，除非用户明确要求
