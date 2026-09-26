# 多角色与班级体系设计

日期：2026-09-24
状态：待评审

## 1. 背景与目标

当前平台只有一种用户：学生。`users` 表无角色概念，所有学习数据（错题、单词进度、学习统计、监督记录）均按 `user_id` 隔离，前端只有一套学生看板。

本次新增三种用户身份并建立"机构—班级"组织体系：

- **超级管理员（super_admin）**：集中创建机构、班级、教师和机构管理者账号；创建班级时生成固定入班码。
- **教师（teacher）**：查看自己所带班级中学生的学习情况（汇总统计 + 错题详情），可将学生移出班级。
- **机构管理者（institution_admin）**：只读查看本机构所有班级及学生情况。
- **学生（student）**：现有功能全部不变；可凭入班码自助加入一个或多个班级。

### 已确认的关键决策

1. 超管统一创建机构、班级、教师/机构管理者账号；学生仍自助注册（邮箱验证码流程不变）。
2. 班级是独立实体；教师与班级、学生与班级均为**多对多**（一个班 N 个老师、N 个学生；老师可带多个班，学生可加入多个班）。
3. 入班码在超管创建班级时生成，**固定不变**，教师只能查看、不能重置。
4. 教师/机构管理者可见范围：学习汇总统计与趋势 + 错题列表/详情；不可见 AI 聊天等隐私内容。
5. 教师除查看外，唯一写操作是把学生移出自己所带的班级；机构管理者完全只读。
6. 借鉴 Moodle 的成熟概念：**认证（账号）与入班（成员关系）分离**、自助选课密钥（Enrolment key）、退课只删成员关系而保留用户学习数据。
7. 不采用 Moodle 的"按上下文分配角色"（同一账号在 A 班是老师、B 班是学生），一期使用全局单一角色；成员表未来可平滑增加角色列以支持双重身份。

## 2. 总体方案

在现有 `users` 表增加 `role`、`institution_id` 两列，新增 4 张表：`institutions`、`classes`、`class_teachers`、`class_students`。前端按角色进入四套布局，后端通过角色依赖守卫与"授权学生集合"实现行级数据隔离。

选择该方案（单表加角色列 + 关联表）的原因：角色固定且少，与现有 JWT 单表认证、裸 Column 模型风格、`create_all` 启动建表方式完全兼容；存量学生数据零改动；避免独立档案表的联查复杂度和通用 RBAC 的过度设计。

## 3. 数据模型

### 3.1 users 表改动

文件：`backend/app/models/user.py`

| 列 | 类型 | 说明 |
|---|---|---|
| `role` | String(20) NOT NULL，默认 `student` | 枚举：`student` / `teacher` / `institution_admin` / `super_admin` |
| `institution_id` | Integer，FK → institutions.id，可空 | 教师、机构管理者所属机构；学生、超管为 NULL |

存量用户迁移后全部为 `student`。超管/教师等账号携带的学生专属配置列（daily_word_count 等）使用默认值，不影响功能。

角色常量统一定义在 `backend/app/models/organization.py`（如 `ROLE_STUDENT = "student"`），避免散字符串。

### 3.2 新增表

文件：`backend/app/models/organization.py`

**institutions（机构）**

| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | |
| name | String(100) NOT NULL，唯一 | 机构名称 |
| created_at | DateTime | |

**classes（班级，独立实体）**

| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | |
| name | String(100) NOT NULL | 班级名称，与 institution_id 组合唯一 |
| institution_id | Integer FK → institutions.id，NOT NULL，索引 | |
| join_code | String(8) NOT NULL，全局唯一，索引 | 6 位大写字母+数字，建班时生成后固定不变 |
| created_at | DateTime | |

唯一约束：`UniqueConstraint(institution_id, name)`；`join_code` 单独唯一索引。

**class_teachers（班级—教师，多对多）**

| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | |
| class_id | Integer FK → classes.id（级联删除） | |
| teacher_id | Integer FK → users.id（级联删除） | |
| created_at | DateTime | |

唯一约束：`(class_id, teacher_id)`。

**class_students（班级—学生，多对多）**

| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | |
| class_id | Integer FK → classes.id（级联删除） | |
| student_id | Integer FK → users.id（级联删除） | |
| joined_at | DateTime | 入班时间 |

唯一约束：`(class_id, student_id)`，防止重复入班。

### 3.3 关系与不变量

- 机构 1—N 班级；班级 N—N 教师、N—N 学生。
- 机构管理者经自身 `institution_id` 看到本机构全部班级。
- 教师经 `class_teachers` 得到班级，再经 `class_students` 得到可见学生。
- 学生入班 = 向 `class_students` 插入一行；**移出学生 = 删除该行，绝不删除 users 及任何按 user_id 归属的学习数据**；学生之后可凭入班码重新加入。
- 删除班级级联删除两张成员表，不影响成员账号与其学习数据。
- 入班码存储与比较均大写化，接口接受小写输入（去空格、upper 后比较）。

### 3.4 超级管理员账号

在 `backend/app/core/seed.py` 中新增种子：当不存在 super_admin 时创建 `superadmin@kaoyan.com`（用户名 `superadmin`，初始密码 `123456`）。沿用现有种子的明文初始密码风格；在登录返回与文档中提示尽快修改密码（一期不做强制改密）。现有 `admin@kaoyan.com` 种子保留并迁移为 student 角色。

## 4. 后端设计

### 4.1 角色守卫

文件：`backend/app/core/deps.py`

- `require_role(*roles: str)`：返回 FastAPI 依赖，校验 `current_user.role`，不符抛 403。
- 便捷封装：`require_super_admin`、`require_teacher`（允许 teacher 与 super_admin）、`require_institution_admin`（允许 institution_admin 与 super_admin）。
- 现有 `get_current_user` 及所有学生端接口行为不变。

### 4.2 组织服务

新建 `backend/app/services/organization_service.py`，单例 `organization_service`，承载所有组织逻辑与权限集合计算：

- `generate_join_code(db) -> str`：生成 6 位（大写字母去除易混字符 I/O，数字去除 0/1）随机码，冲突时重试（最多 5 次，仍冲突抛错）。
- `create_institution / list_institutions`
- `create_class(db, institution_id, name) -> Class`：生成唯一 join_code。
- `create_staff_user(db, ...) -> User`：超管创建教师/机构管理者账号，**跳过邮箱验证码**，校验用户名/邮箱唯一，角色限 teacher/institution_admin，必须带 institution_id。
- `assign_teacher(db, class_id, teacher_id)` / `unassign_teacher(...)`：校验教师角色与同机构归属。
- `join_class(db, student_id, code) -> Class`：码无效抛 ValueError；已是成员则幂等返回该班级。
- `get_teacher_class_ids(db, teacher_id) -> set[int]`
- `get_teacher_student_ids(db, teacher_id) -> set[int]`：经 class_teachers → class_students 去重。**所有教师侧统计/错题查询统一先取该集合再过滤。** 调用者为 super_admin 时返回全集标记（None 表示不限），绕过成员关系过滤，使其可经同一套只读接口查看任意班级/学生。
- `get_institution_student_ids(db, institution_id) -> set[int]`：机构管理者侧同理（取该机构下所有班级的学生并去重）；super_admin 同样返回全集标记。
- 归属校验统一规则：教师访问的 class_id 必须在其 class_ids 内、student_id 必须在其 student_ids 内，否则 403；super_admin 跳过该校验。
- `get_class_students(db, class_id) -> list`、`my_classes(db, student_id)`、`remove_student_from_class(db, teacher_id, class_id, student_id)`：仅班级任课教师（或超管）可操作，删除 class_students 行。

### 4.3 API

所有路由按前缀分组；同一 router 内静态路径定义在 `/{id}` 动态路径之前，避免通配抢占。

**超管 `/api/admin`（require_super_admin）**

- `POST   /institutions` 创建机构
- `GET    /institutions` 机构列表
- `POST   /classes` 创建班级（body: name, institution_id；返回含 join_code）
- `GET    /classes` 班级列表，可选 `institution_id` 过滤
- `GET    /classes/{class_id}` 班级详情（入班码、教师名单、学生名单）
- `POST   /users` 创建教师/机构管理者账号（username, email, password, role, institution_id）
- `GET    /users` 账号列表，可按 role / institution_id 过滤
- `POST   /classes/{class_id}/teachers` 分配教师（body: teacher_id）
- `DELETE /classes/{class_id}/teachers/{teacher_id}` 取消分配

**教师 `/api/teacher`（teacher + super_admin）**

- `GET    /classes` 我带的班级（含人数等概要）
- `GET    /classes/{class_id}/students` 班级学生名单及每人汇总指标
- `GET    /students/{student_id}/overview` 学生汇总统计与近期趋势
- `GET    /students/{student_id}/mistakes` 学生错题列表（支持 subject 等现有过滤参数）
- `GET    /students/{student_id}/mistakes/{mistake_id}` 学生错题详情
- `DELETE /classes/{class_id}/students/{student_id}` 移出学生

所有读取接口先做归属校验：班级必须在教师 class_ids 内；学生必须在教师 student_ids 内，否则 403。错题查询复用 `mistake_service.get_mistakes(db, owner_id=student_id, ...)` / `get_mistake_by_id`（这两个方法本就以 user_id 为资源属主参数），授权通过后以学生 id 调用，不新增数据访问路径。

**机构管理者 `/api/institution`（institution_admin + super_admin）**

- `GET    /classes` 本机构班级列表及各班汇总（人数、平均学习时长、错题总数、监督异常数）；institution_admin 固定取自身 institution_id；super_admin 调用须传 `institution_id` 查询参数（否则 400）
- `GET    /classes/{class_id}/students` 班级学生汇总（只读）
- `GET    /students/{student_id}/overview`、`GET    /students/{student_id}/mistakes`、`.../{mistake_id}`：与教师相同的只读口径，仅限本机构学生。

**学生 `/api/classes`（student）**

- `POST /join`：body `{ code }`，成功返回班级信息（名称、机构名）
- `GET  /my`：我加入的班级列表

### 4.4 统计口径

教师/机构看板的指标复用现有数据源，按学生集合聚合：

- 学习时长、单词学习数、错题数、做题数：`user_study_stats`（[study_stat.py](file:///home/rizard/software/KaoYanPT/backend/app/models/study_stat.py)）
- 错题掌握情况：`mistakes`
- 单词进度：`user_words`
- 监督异常：`study_supervision_records` 中非正常 status 计数

统计周期统一口径：班级/学生卡片中的累计值（错题总数、监督异常总数）取全量；学习时长、单词/做题等活跃度指标默认取**近 30 天**；学生 overview 趋势返回近 30 天按日序列。聚合查询在 organization_service（或新建只读 `stats_query_service`）中实现，统一接收 `student_ids` 集合参数（None 表示超管不限），保证授权条件不被绕过。

### 4.5 Schema

新建 `backend/app/schemas/organization.py`：

- `InstitutionCreate / InstitutionResponse`
- `ClassCreate / ClassResponse`（含 join_code、student_count、teacher 概要）
- `StaffUserCreate`（role 用 Literal 枚举校验）
- `JoinClassRequest / MyClassResponse`
- `StudentSummary`、`StudentOverview`、`ClassSummary`
- `UserResponse`（`backend/app/schemas/auth.py`）增加 `role: str`、`institution_id: Optional[int]`，前端登录与 /me 均可获取角色。

### 4.6 错误处理

| 场景 | 状态码 | 信息风格 |
|---|---|---|
| 入班码不存在 | 400 | 邀请码无效 |
| 重复入班 | 200 | 幂等成功，不报错 |
| 角色不符 | 403 | 无权限执行该操作 |
| 教师访问非所带班级/学生 | 403 | 无权限查看该班级/学生 |
| 机构管理者越机构 | 403 | 无权限查看该机构数据 |
| 用户名/邮箱重复（超管建号） | 400 | 用户名或邮箱已存在 |
| 班级不存在、教师不存在 | 404 | 对应资源不存在 |
| 向机构分配非教师账号/跨机构分配 | 400 | 明确中文原因 |

沿用现有路由层 `ValueError → HTTPException` 的中文提示模式。

## 5. 前端设计

### 5.1 登录与路由

- 登录后调 `/api/auth/me`，将 `role` 存入 [user store](file:///home/rizard/software/KaoYanPT/frontend/src/stores/user.ts) 并按角色跳转：
  - student → `/dashboard`
  - teacher → `/teacher`
  - institution_admin → `/institution`
  - super_admin → `/admin`
- [router/index.ts](file:///home/rizard/software/KaoYanPT/frontend/src/router/index.ts) 路由守卫升级为"token + 角色匹配"；角色与路径不匹配时重定向到其自身首页。角色由 store 持久化到 localStorage（刷新页面时守卫可同步读取，随后 /me 异步校正）。
- 注册页不变（注册结果恒为 student）。

### 5.2 学生端（改动最小）

- 现有 Dashboard 及所有学习页面零改动。
- 侧边栏新增"我的班级"菜单 → `views/student/ClassJoin.vue`：
  - 入班码输入框 + 加入按钮；成功提示班级名。
  - 已加入班级列表（班级名、所属机构、任课教师）。

### 5.3 教师端（views/teacher/，TeacherLayout.vue）

- `ClassList.vue`：所带班级卡片。
- `ClassDetail.vue`：学生表格（姓名、学习时长、单词数、错题数、监督异常数），每行"移出班级"按钮 + 二次确认弹窗。
- `StudentDetail.vue`：统计与趋势（Element Plus 图表/进度组件）+ 只读错题列表与详情，展示风格与现有错题页保持一致。

### 5.4 机构管理者端（views/institution/，InstitutionLayout.vue）

- `ClassOverview.vue`：本机构班级汇总卡片，可下钻。
- `ClassDetail.vue`：班级学生汇总表，纯只读（无移出按钮）。
- `StudentDetail.vue`：统计 + 错题详情，只读。

### 5.5 超管端（views/admin/，AdminLayout.vue）

- `Institutions.vue`：机构列表 + 新建。
- `Classes.vue`：班级列表（按机构筛选）、新建班级、展示/复制入班码、分配与移除教师、查看学生名单（只读复用）。
- `Users.vue`：创建教师/机构管理者账号（角色、所属机构、初始密码）与账号列表。

### 5.6 API 层与 UI 风格

- 新建 `frontend/src/api/organization.ts`，封装 admin/teacher/institution/学生入班接口，复用现有 axios 实例（自动带 token）。
- 四套布局沿用现有 Element Plus + 深色侧边栏风格（参考 [Dashboard.vue](file:///home/rizard/software/KaoYanPT/frontend/src/views/Dashboard.vue)），仅菜单与内容区不同。

## 6. 数据迁移

- 4 张新表由启动时 `Base.metadata.create_all()` 自动创建（需确保 `app.models.organization` 在 `models/__init__.py` 导入）。
- users 新增两列采用与项目既有轻量迁移一致的方式：在 `backend/app/core/` 下新增迁移函数（SQLite 用 `PRAGMA table_info(users)` 检查列存在性），不存在则执行：
  - `ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'student'`
  - `ALTER TABLE users ADD COLUMN institution_id INTEGER`
- 在 `main.py` 中 `create_all` 之后、`run_seed()` 之前调用；存量用户全部自动获得 student 角色。
- 同时新增一个 alembic 版本文件（`backend/alembic/versions/`）表达同样变更，保持迁移目录完整。
- 不修改任何现有列约束与现有数据。

## 7. 测试策略

遵循 TDD（先写失败测试再实现）。后端测试沿用 `backend/tests/` 的内存 SQLite + 可直接 `python3` 运行的风格，接口层用 fast.testclient 补充。

1. **角色与账号**：超管创建教师/机构账号，role 与 institution_id 正确；自助注册默认 student；超管种子存在。
2. **建班与入班码**：建班生成唯一码；重复机构内同名班级被拒；错误码入班 400；正确码入班成功；重复入班幂等；小写码等价。
3. **权限隔离（核心）**：
   - 教师只见所带班级；带 A 班教师访问 B 班学生 → 403。
   - 机构管理者只见本机构；跨机构访问 → 403。
   - 学生访问 /api/teacher、/api/admin → 403。
   - 未带该班教师不能移出该班学生；移出后名单不含该生，但其错题/统计数据仍在；可凭码重新加入。
4. **统计正确性**：构造 user_study_stats / mistakes / 监督记录后，班级学生汇总与学生 overview 数字正确，且仅统计授权集合内学生。
5. **回归**：现有学生端接口（错题 CRUD、单词等）在新角色列存在时行为不变。

前端通过浏览器手工走通主链路：超管建机构 → 建班（得入班码）→ 建教师账号并分配 → 教师登录看班 → 学生注册/登录输码入班 → 教师查看统计与错题、移出学生 → 机构管理者查看全机构只读看板。

## 8. 一期范围边界

不做：班级公告/作业/资源、教师手动添加学生、机构管理者任何写操作、入班码重置/时效/次数限制、成员 Active/Suspended 状态、按上下文的双重角色、访客与付费选课、强制首次登录改密、学生现有学习功能的任何改动。

## 9. 受影响文件清单（预估）

后端：

- 改：`app/models/user.py`、`app/models/__init__.py`、`app/schemas/auth.py`、`app/core/deps.py`、`app/core/seed.py`、`app/main.py`、`app/api/__init__.py`
- 新：`app/models/organization.py`、`app/schemas/organization.py`、`app/services/organization_service.py`、`app/api/admin.py`、`app/api/teacher.py`、`app/api/institution.py`、`app/api/classes.py`（学生入班）、轻量迁移模块、alembic 版本文件、相关测试

前端：

- 改：`src/router/index.ts`、`src/stores/user.ts`、`src/views/Dashboard.vue`（仅加菜单项）、`src/api/auth.ts` 类型
- 新：`src/api/organization.ts`、`src/views/student/ClassJoin.vue`、`src/views/teacher/*`、`src/views/institution/*`、`src/views/admin/*`（各含布局与页面）
