# 多角色与班级体系实施计划

设计文档：`docs/superpowers/specs/2026-09-24-multi-role-class-system-design.md`

## 任务 1：数据模型与迁移（后端地基）

- 新建 `backend/app/models/organization.py`
  - 角色常量 `ROLE_STUDENT/TEACHER/INSTITUTION_ADMIN/SUPER_ADMIN`
  - `Institution`、`Class`（含 join_code）、`ClassTeacher`、`ClassStudent` 四模型，唯一约束与级联删除按设计文档
- 改 `backend/app/models/user.py`：加 `role`（默认 student）、`institution_id`
- 改 `backend/app/models/__init__.py`：导入新模型
- 新建 `backend/app/core/migrations_org.py`：启动时检查 users 列并 ALTER TABLE（SQLite PRAGMA 方式）
- 新建 alembic 版本文件（down_revision 指向当前 head `a3b4c5d6e7f8`）
- 改 `backend/app/core/seed.py`：补超管种子 `superadmin@kaoyan.com / 123456`
- 改 `backend/app/main.py`：create_all 后执行轻量迁移
- 验证：重启后端，PRAGMA 确认新列/新表，超管可登录

## 任务 2：Schema、角色守卫与组织服务

- 改 `backend/app/schemas/auth.py`：`UserResponse` 加 role、institution_id
- 新建 `backend/app/schemas/organization.py`：机构/班级/员工账号/入班/学生汇总等 schema
- 改 `backend/app/core/deps.py`：`require_role(*roles)` 及三个便捷依赖
- 新建 `backend/app/services/organization_service.py`：
  - 入班码生成（去易混字符 + 唯一重试）
  - 机构/班级/员工账号 CRUD、教师分配
  - 入班（幂等）、我的班级、移出学生（只删成员关系）
  - 授权集合：`get_teacher_class_ids / get_teacher_student_ids / get_institution_student_ids`（超管返回 None=全集）

## 任务 3：统计聚合（只读）

- 在组织服务或新建 `stats_query_service`：
  - 学生汇总：近 30 天学习时长/单词/做题、累计错题数、监督异常数
  - 学生 overview：近 30 天按日趋势 + 错题掌握分布
  - 班级/机构聚合：人数、平均时长、错题总数、异常数
  - 所有查询统一接收 student_ids（None 不限），杜绝越权

## 任务 4：四组 API

- 新建 `backend/app/api/admin.py`（/api/admin，仅超管）：机构、班级、员工账号、教师分配
- 新建 `backend/app/api/teacher.py`（/api/teacher）：我的班级、学生名单、学生 overview/错题、移出学生
- 新建 `backend/app/api/classes.py`（/api/classes，学生）：POST /join、GET /my
- 机构只读端点开在 teacher 同结构的 `backend/app/api/institution.py`（/api/institution）
- 改 `main.py` 注册路由；静态路由先于 /{id}
- 错题查看复用 `mistake_service.get_mistakes/get_mistake_by_id`（以学生 id 为属主）

## 任务 5：后端测试

- 新建 `backend/tests/test_organization.py`（内存 SQLite，可直接 python3 运行）：
  - 建机构/班/员工账号、入班码唯一、错误码 400、重复入班幂等、小写等价
  - 权限隔离：A 班教师看不到 B 班；跨机构 403；学生访问管理端 403
  - 移出学生后成员关系消失但错题/统计仍在、可重新入班
  - 统计聚合数字正确且仅限授权集合

## 任务 6：前端基础设施

- 改 `stores/user.ts`：role 持久化到 localStorage
- 改 `api/auth.ts`：User 类型加 role/institution_id
- 新建 `api/organization.ts`：admin/teacher/institution/入班接口封装
- 改 `router/index.ts`：新增四套路由，守卫升级为 token + 角色匹配
- 改 `views/Login.vue`：登录后按 role 跳转各自首页

## 任务 7：四个角色的页面

- 学生：`views/student/ClassJoin.vue` + Dashboard 侧边栏"我的班级"菜单
- 教师：`views/teacher/`：TeacherLayout、ClassList、ClassDetail（含移出确认）、StudentDetail（趋势+只读错题）
- 机构：`views/institution/`：InstitutionLayout、ClassOverview、ClassDetail（只读）、StudentDetail
- 超管：`views/admin/`：AdminLayout、Institutions、Classes（入班码复制/教师分配）、Users（建员工账号）
- 统一沿用现有 Element Plus 深色侧边栏风格；`npm run build` 通过

## 任务 8：端到端联调

超管建机构→建班（拿码）→建教师并分配→教师登录看班→学生输码入班→教师看统计/错题/移出→机构管理者全机构只读。

## 执行原则

- 后端先行、分任务验证；每个任务完成即汇报
- 不改动学生现有学习功能；存量数据零影响
- 一期范围严格按设计文档第 8 节
