# 错题管理功能优化实施计划

## Context

当前错题添加流程需要手动填写 8 个字段（科目、知识点、错误类型、难度、题目内容、正确答案、解析、错误原因），操作繁琐且无图片上传能力。本次优化旨在：简化添加流程、支持图片上传、接入 AI OCR 识别自动填充字段、并基于错题内容推荐同类题目。

数据库保留现有数据，通过 ALTER TABLE 添加新列。

## 实施步骤

### 步骤 1：安装 OCR 依赖

`rapidocr_onnxruntime==1.3.22` 已在 requirements.txt 中但未安装。运行 pip install 安装。首次使用时会自动下载 ONNX 模型文件（约 50MB）。

### 步骤 2：数据库迁移（保留数据）

**修改文件**: [backend/app/database.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/database.py)

在 `database.py` 中添加 `migrate_database()` 函数，使用 `ALTER TABLE mistakes ADD COLUMN image_path VARCHAR(500)` 添加图片路径列。在 [main.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/main.py) 的 `Base.metadata.create_all()` 之后调用。

现有 NOT NULL 列（knowledge_point, error_type, difficulty, answer）保持不变，由服务层提供默认值。

### 步骤 3：模型和 Schema 修改

**修改文件**: [backend/app/models/mistake.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/models/mistake.py)
- 添加 `image_path = Column(String(500), nullable=True)`

**修改文件**: [backend/app/schemas/mistake.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/schemas/mistake.py)
- `MistakeCreate`：除 `subject` 外所有字段改为 `Optional`，添加 `image_path`
- `MistakeResponse`：添加 `image_path: Optional[str]`，将 knowledge_point 等改为 `Optional[str]`
- 新增 `MistakeRecognizeRequest`、`MistakeRecognizeResponse`、`SimilarMistakeResponse` 三个 schema

### 步骤 4：新建 OCR 服务

**新建文件**: `backend/app/services/ocr_service.py`

使用 rapidocr_onnxruntime 实现：
- `extract_text(image_path)` — OCR 文本提取，惰性加载引擎（首次调用时初始化）
- `classify_subject(text)` — 基于关键词匹配科目（数学/英语/政治/专业课），返回 (科目, 置信度)
- `detect_knowledge_point(text, subject)` — 基于关键词匹配知识点子分类
- `recognize(image_path)` — 完整管线：OCR → 科目分类 → 知识点检测

关键词字典覆盖考研常见术语（如数学：极限/导数/积分/矩阵；英语：reading/cloze/translation；政治：马克思/唯物/辩证等）。

### 步骤 5：错题服务更新

**修改文件**: [backend/app/services/mistake_service.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/services/mistake_service.py)
- `create_mistake`：为 NOT NULL 字段提供默认值（difficulty 默认 "中等"，knowledge_point 默认 "未分类"，error_type 默认 "未分类"，answer 默认 ""），添加 `image_path` 字段
- 新增 `get_similar_mistakes(db, user_id, mistake_id, limit=5)` 方法：基于相同科目 + 知识点匹配 + 题目文本字符重叠度计算相似度评分

### 步骤 6：后端新 API 端点

**修改文件**: [backend/app/routers/mistakes.py](file:///d:/软件/trae_cn/projects/KaoYanXT/backend/app/routers/mistakes.py)

新增 3 个端点（注意：必须定义在 `/{mistake_id}` 路由之前，避免路径参数冲突）：
- `POST /api/mistakes/upload` — 接收图片文件，保存到 `uploads/mistakes/`，返回 image_path 和 image_url
- `POST /api/mistakes/recognize` — 接收 image_path，调用 OCR 服务返回识别结果（题目文本、建议科目、建议知识点、置信度）
- `GET /api/mistakes/{mistake_id}/similar` — 返回同类题推荐列表

### 步骤 7：前端 API 层更新

**修改文件**: [frontend/src/api/mistakes.ts](file:///d:/软件/trae_cn/projects/KaoYanXT/frontend/src/api/mistakes.ts)
- 更新 `Mistake` 接口添加 `image_path`
- 更新 `MistakeCreate` 接口：除 subject 外改为可选，添加 `image_path`
- 新增 `uploadMistakeImage(file)` — 使用 FormData + axios 上传（自动带 Authorization header）
- 新增 `recognizeMistake(imagePath)` — 调用 AI 识别端点
- 新增 `getSimilarMistakes(id)` — 获取同类题推荐

### 步骤 8：前端 Mistakes.vue 重构

**修改文件**: [frontend/src/views/Mistakes.vue](file:///d:/软件/trae_cn/projects/KaoYanXT/frontend/src/views/Mistakes.vue)

三处改动：

**8a. 添加对话框重构**
- 顶部放置图片上传区（el-upload，使用 `:before-upload` 拦截手动上传）
- 上传后显示图片预览 + "AI识别"按钮
- 点击 AI 识别调用 `/recognize` 端点，自动填充科目、知识点、题目内容
- 表单验证简化：仅科目必填，其余可选
- 添加 Picture 图标导入

**8b. 列表表格添加图片缩略图列**
- 在科目列后添加图片列，使用 el-image 组件显示缩略图（50x50），支持点击预览大图

**8c. 详情对话框增强**
- 添加题目图片展示区（el-image，支持点击放大）
- 添加"同类题推荐"面板，点击"加载推荐"按钮调用 `/similar` 端点
- 推荐列表显示科目标签、知识点标签、相似度百分比、题目摘要

## 关键设计决策

1. **图片上传认证**：使用 axios 的 `:before-upload` 拦截 + 手动 FormData 上传，而非 el-upload 的 `action` 属性，确保 Authorization header 自动注入
2. **OCR 惰性加载**：RapidOCR 引擎在首次 `/recognize` 请求时初始化（约 30 秒），不阻塞服务器启动
3. **相似度算法**：相同知识点 +0.5，知识点部分匹配 +0.3，题目文本字符集 Jaccard 相似度 ×0.5，无需外部 NLP 库
4. **数据库兼容**：ALTER TABLE 仅添加新列，不修改现有列约束；服务层为 NOT NULL 字段提供默认值

## 验证方案

1. 启动后端，确认数据库迁移成功（`PRAGMA table_info(mistakes)` 包含 image_path）
2. 测试 `POST /api/mistakes/upload` 上传图片，确认文件保存到 `uploads/mistakes/`
3. 测试 `POST /api/mistakes/recognize` OCR 识别，确认返回文本和分类建议
4. 测试 `POST /api/mistakes` 创建错题（仅传 subject + image_path），确认成功
5. 测试 `GET /api/mistakes/{id}/similar` 同类题推荐
6. 浏览器访问前端，验证：图片上传 → AI 识别 → 自动填充 → 添加错题 → 查看详情 → 同类题推荐 完整流程
