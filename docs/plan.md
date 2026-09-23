# 考研复习平台 - 详细实现计划

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts |
| 后端 | Python + FastAPI |
| 数据库 | SQLite（开发）/ PostgreSQL（演示） |
| OCR | RapidOCR |
| 全文检索 | Whoosh |
| 定时任务 | APScheduler |
| 文档解析 | PyPDF2 + python-docx |
| AI问答 | 本地部署开源大模型 |

## 开发阶段规划

### Phase 1: 基础框架搭建

| 任务 | 描述 |
|------|------|
| 1.1 | 创建项目目录结构 |
| 1.2 | 配置后端环境（虚拟环境、依赖安装） |
| 1.3 | 实现用户认证模块（注册/登录/登出） |
| 1.4 | 配置前端环境（Vue3 + TypeScript + Element Plus） |
| 1.5 | 实现基础布局和导航 |

### Phase 2: 错题管理与复习提醒系统

| 任务 | 描述 |
|------|------|
| 2.1 | 创建错题相关数据库模型 |
| 2.2 | 实现错题 CRUD API |
| 2.3 | 实现错题添加功能（手动录入、OCR、批量导入） |
| 2.4 | 实现记忆曲线算法和定时提醒 |
| 2.5 | 实现错题重做功能 |
| 2.6 | 前端错题管理页面 |

### Phase 3: 个性化题目推荐系统

| 任务 | 描述 |
|------|------|
| 3.1 | 创建推荐相关数据库模型 |
| 3.2 | 实现薄弱知识点分析算法 |
| 3.3 | 实现智能推荐算法 |
| 3.4 | 实现推荐题目跟踪功能 |
| 3.5 | 前端推荐页面 |

### Phase 4: 资料管理与智能问答系统

| 任务 | 描述 |
|------|------|
| 4.1 | 创建资料相关数据库模型 |
| 4.2 | 实现资料上传功能 |
| 4.3 | 实现全文检索系统（Whoosh） |
| 4.4 | 实现资料问答功能 |
| 4.5 | 前端资料管理页面 |

### Phase 5: 单词背诵与复习监督系统

| 任务 | 描述 |
|------|------|
| 5.1 | 创建单词相关数据库模型 |
| 5.2 | 导入考研词汇库 |
| 5.3 | 实现单词学习计划 |
| 5.4 | 实现记忆曲线复习提醒 |
| 5.5 | 实现多种记忆模式 |
| 5.6 | 实现学习报告生成 |
| 5.7 | 前端单词学习页面 |

### Phase 6: AI智能控制与问答系统

| 任务 | 描述 |
|------|------|
| 6.1 | 部署本地开源大模型 |
| 6.2 | 实现自然语言指令执行 |
| 6.3 | 实现 AI 智能问答 |
| 6.4 | 前端 AI 交互界面 |

### Phase 7: 集成测试与性能优化

| 任务 | 描述 |
|------|------|
| 7.1 | 集成测试 |
| 7.2 | 性能优化 |
| 7.3 | 安全加固 |
| 7.4 | 部署准备 |

## 数据库表设计

### users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String(50) | 用户名 |
| email | String(100) | 邮箱 |
| password | String(255) | 加密密码 |
| avatar | String(255) | 头像URL |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### mistakes 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| subject | String(50) | 科目 |
| knowledge_point | String(100) | 知识点 |
| error_type | String(50) | 错误类型 |
| difficulty | String(20) | 难度 |
| mastery_level | String(20) | 掌握程度 |
| question_text | Text | 题目文本 |
| answer | Text | 正确答案 |
| analysis | Text | 解析 |
| error_reason | Text | 错误原因 |
| next_review_date | Date | 下次复习日期 |
| review_count | Integer | 复习次数 |
| correct_count | Integer | 正确次数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### mistake_reviews 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| mistake_id | Integer | 错题ID |
| user_id | Integer | 用户ID |
| result | String(20) | 结果 |
| review_date | DateTime | 复习时间 |
| notes | Text | 备注 |

### words 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| word | String(50) | 单词 |
| phonetic | String(100) | 音标 |
| meaning | Text | 释义 |
| example_sentence | Text | 例句 |
| difficulty | Integer | 难度等级 |
| frequency | Integer | 出现频率 |
| exam_requirement | String(20) | 考纲要求 |

### user_words 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| word_id | Integer | 单词ID |
| mastery_level | String(20) | 掌握程度 |
| next_review_date | Date | 下次复习日期 |
| review_count | Integer | 复习次数 |
| correct_count | Integer | 正确次数 |
| last_study_date | DateTime | 上次学习时间 |

### resources 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| filename | String(255) | 文件名 |
| file_type | String(50) | 文件类型 |
| file_size | Integer | 文件大小 |
| storage_path | String(500) | 存储路径 |
| indexed | Boolean | 是否已建立索引 |
| upload_date | DateTime | 上传时间 |

### recommendations 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| subject | String(50) | 科目 |
| knowledge_point | String(100) | 知识点 |
| difficulty | String(20) | 难度 |
| question_text | Text | 题目内容 |
| answer | Text | 答案 |
| analysis | Text | 解析 |
| source | String(100) | 来源（真题/模拟题/专项） |
| completed | Boolean | 是否完成 |
| result | String(20) | 完成结果 |
| completion_time | DateTime | 完成时间 |
| created_at | DateTime | 创建时间 |

### user_weak_points 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| subject | String(50) | 科目 |
| knowledge_point | String(100) | 知识点 |
| weak_level | Integer | 薄弱等级(1-5) |
| mistake_count | Integer | 错误次数 |
| updated_at | DateTime | 更新时间 |

### ai_chat_history 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| message_type | String(20) | 消息类型（question/answer） |
| content | Text | 内容 |
| source | String(100) | 来源 |
| created_at | DateTime | 创建时间 |

### user_study_stats 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID |
| study_date | Date | 学习日期 |
| total_time | Integer | 学习时长(分钟) |
| words_studied | Integer | 单词学习数量 |
| mistakes_added | Integer | 新增错题数量 |
| questions_completed | Integer | 完成题目数量 |
| created_at | DateTime | 创建时间 |

## API 设计

### 认证模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/logout | 用户登出 |
| GET | /api/auth/me | 获取当前用户信息 |

### 错题管理模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/mistakes | 添加错题 |
| GET | /api/mistakes | 获取错题列表 |
| GET | /api/mistakes/{id} | 获取单条错题 |
| PUT | /api/mistakes/{id} | 更新错题 |
| DELETE | /api/mistakes/{id} | 删除错题 |
| POST | /api/mistakes/{id}/review | 重做错题 |
| GET | /api/mistakes/review/today | 今日待复习 |
| POST | /api/mistakes/import | 批量导入 |
| POST | /api/mistakes/ocr | OCR识别 |

### 题目推荐模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/recommend/analysis | 薄弱知识点分析 |
| POST | /api/recommend/generate | 生成推荐题目 |
| GET | /api/recommend/list | 获取推荐列表 |
| POST | /api/recommend/{id}/complete | 标记完成 |
| GET | /api/recommend/report | 评估报告 |

### 资料管理模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/resources/upload | 上传资料 |
| GET | /api/resources | 获取资料列表 |
| GET | /api/resources/{id} | 获取资料详情 |
| DELETE | /api/resources/{id} | 删除资料 |
| POST | /api/resources/search | 全文检索 |
| POST | /api/resources/qa | 资料问答 |

### 单词学习模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/words | 获取单词列表 |
| POST | /api/words/plan | 设置学习计划 |
| GET | /api/words/plan | 获取学习计划 |
| POST | /api/words/study | 学习单词 |
| GET | /api/words/review/today | 今日待复习 |
| GET | /api/words/report | 学习报告 |

### AI问答模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/ai/chat | AI智能问答 |
| POST | /api/ai/command | 自然语言指令 |