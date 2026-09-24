# 背诵功能升级（借鉴 ToastFish）设计文档

日期：2026-09-24
状态：已批准

## 背景与目标

KaoYanPT 现有「单词背诵」功能（WordModule.vue）采用三档评分（认识/模糊/不认识）+ 固定间隔 SRS，另有定时提醒弹横幅、AI 语音朗读。用户希望借鉴 [ToastFish](https://github.com/Uahh/ToastFish) 项目的四个核心能力：

1. **SM2+ 四档评分算法**：忘记/困难/一般/认识，间隔智能自适应
2. **站内沉浸式弹卡被动背诵**：网页内悬浮卡片定时弹词，标签在后台时升级为浏览器系统通知
3. **学后测验**：中译英 + 英译中选择题
4. **背诵记录导出与重新导入**：xlsx 记录，可重新导入复习

实施方式：**一次性整体重构**（思路 A，用户选定）。

## 第 1 部分：SM2+ 四档引擎与数据模型（地基）

### 评分四档

| 档位 | 分值 | 对照 ToastFish | 把握度显示 |
|---|---|---|---|
| 忘记 | 0.4 | Again | 陌生 |
| 困难 | 0.6 | Hard | 认识 |
| 一般 | 0.8 | Good | 熟悉 |
| 认识 | 1.0 | Easy | 掌握 |

### 卡状态机

`new → step1 → step2 → reviewed → relearn1 → relearn2`

**会话内分钟级延迟**（弹卡会话运行期间生效）：

| 当前状态 | 忘记 | 困难 | 一般 | 认识 |
|---|---|---|---|---|
| new / step1 | step1, +1min | step1, +5.5min | step2, +10min | reviewed（今日完成） |
| step2 | step1, +1min | step1, +5.5min | reviewed | reviewed |
| reviewed | relearn1, +10min | 维持 reviewed，按间隔公式更新天数 | 维持 reviewed，按间隔公式更新天数 | 维持 reviewed，按间隔公式更新天数 |
| relearn1 / relearn2 | 同状态, +10min | 同状态, +15min | 下一阶段 / reviewed | reviewed |

**跨会话天数**：升级为 `reviewed` 后，`next_review_date = 今天 + days_between_reviews`，并按难度加权公式自适应更新：

```
podue = min(2, 距上次复习天数 / days_between_reviews)   # 答对时
     = 1                                                 # 答错时
difficulty += podue * (8 - 10 * score) / 17              # 0~1 封顶
dfweight = 3 - 1.7 * difficulty
correct:  days_between_reviews *= (1 + (dfweight - 1) * podue * (0.95 + 0.1 * random))
wrong:    days_between_reviews *= 1 / (1 + 3 * difficulty)
```

### 数据模型变更（新 Alembic 迁移 `words_toastfish_features`）

- `user_words` 新增列：
  - `srs_status` String(20)，默认 `new`（枚举：new/step1/step2/reviewed/relearn1/relearn2）
  - `difficulty` Float，默认 0.3
  - `days_between_reviews` Float，默认 3.0
- **旧数据迁移**：已有 `srs_stage > 0` 的卡 → `srs_status='reviewed'`，按旧间隔序列 `[1,3,7,15]` 填 `days_between_reviews`；`srs_stage = 0` → `srs_status='new'`
- 新表 `study_records`：
  - id, user_id, session_id(String, 分组一次会话), word_id, word(冗余), rating(忘记/困难/一般/认识), quiz_result(Boolean 可空), source(card/push/quiz), created_at
- `users` 新增列：`push_settings_json` Text，结构：`{count: 10, interval_seconds: 60, category: str|null, auto_play: bool}`

### 接口变化

- `POST /api/words/study` 接受新四档；**兼容旧三档**一次性映射：认识→认识、模糊→困难、不认识→忘记
- `study_word` 内部实现改为 SM2+ 状态机（重写 `memory_curve.py`：`calculate_word_next_review` 废弃，新增 `SrsCard` 纯逻辑类，独立可测）

## 第 2 部分：沉浸式弹卡（被动背诵）

- **入口**：背诵页新增「弹卡背诵」tab（`PushCards.vue`）
- **配置**：弹卡数量、间隔秒数、词汇分类、自动发音 → 存 `push_settings_json`
- **会话队列**：`GET /api/words/session-cards?count&category`，SM2 出队顺序：新词 → 到期复习卡 → 会话内到期的阶段卡（对齐 ToastFish RecitationSM2）
  - 返回字段：word_id, word, phonetic, meaning, example, srs_status
- **弹卡交互**：右下角悬浮卡片；按间隔秒数弹出、N 秒后自动收起；按钮：忘记/困难/一般/认识 + 发音 + 暂停/继续 + 停止；进度条「本轮 X/N + 各档计数」
- **会话内重排**：评分后按第 1 部分会话内分钟延迟，前端定时器把卡重新入队（页面切换不影响）
- **背景升级**：`document.hidden` 且已授权 `Notification` → 弹系统通知（单词+释义+发音提示）；返回页面后继续
- **收尾**：`POST /api/words/session-complete` 写入 `study_records`、清会话

## 第 3 部分：学后测验（中译英 + 英译中）

- **触发点**：① 弹卡会话结束；② WordModule 每轮完成后自动弹出
- **出题**：`GET /api/words/quiz` 返回 quiz 题目数组。每题为 `{type: 中译英|英译中, prompt, options[4], correct, word_id}`；干扰项从同分类随机抽取（排除正确答案），后端生成
- **判分**：`POST /api/words/quiz/answer {word_id, selected, correct, session_id}` → 答对记 `study(一般)`，答错记 `study(忘记)` 并把该词重新入队，直到答对；写入 `study_records`（source='quiz', quiz_result）
- **UI**：测验卡片，即时反馈（对/错 + 正确项高亮）

## 第 4 部分：背诵记录导出 + 重新导入

- **记录查询**：`GET /api/words/records?page&page_size` → 会话列表（小组 `session_id`，展示时间、单词数、各档统计）
- **导出 xlsx**：`GET /api/words/records/export`；新增依赖 `openpyxl`；列：日期/会话ID/单词/音标/释义/评级/测验结果/掌握度/来源；附汇总 sheet（按会话聚合）
- **重新导入**：`POST /api/words/records/import`（上传 xlsx）
  - 按单词名匹配现有词（用户词 + 系统词）→ 生成/更新 `UserWord` 置为 `reviewed` + `next_review_date = 今天`
  - 库里不存在的词 → 自动建 `Word`（category='我的词书'，user_id 归属当前用户）
  - 返回导入数量 + 失败行明细
- **UI**：新增 `RecordsModule.vue`（会话表 + 导出/导入按钮）；Words.vue 加「背诵记录」tab

## 接口清单（新增/修改）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/words/study | 改：四档评分 + SM2+ 状态机 |
| GET | /api/words/session-cards | 新：弹卡会话队列 |
| POST | /api/words/session-complete | 新：结束会话、写记录 |
| GET | /api/words/quiz | 新：出测验题 |
| POST | /api/words/quiz/answer | 新：判分 |
| GET | /api/words/records | 新：会话列表 |
| GET | /api/words/records/export | 新：导出 xlsx |
| POST | /api/words/records/import | 新：导入 xlsx 复习 |
| GET/POST | /api/words/push-config | 新：弹卡配置读写 |

## 软件模块改动清单

- **后端**：
  - `backend/app/utils/memory_curve.py`：重写为 SM2+（SrsCard 状态机，纯函数可单测）
  - `backend/app/models/word.py`：UserWord 加 3 列；新增 `StudyRecord` 模型（与 `study_records` 迁移一致）
  - `backend/app/models/user.py`：User 加 `push_settings_json`
  - `backend/app/schemas/word.py`：新增四档/推送/测验/记录相关 schema
  - `backend/app/services/word_service.py`：SM2+ 集成、session-cards、quiz、records、export/import、push-config
  - `backend/app/api/words.py`：新增上述路由
  - `backend/alembic/versions/xxxx_words_toastfish_features.py`：新迁移
  - `backend/requirements.txt`：+ openpyxl
- **前端**：
  - `frontend/src/views/recitation/WordModule.vue`：四档按钮/统计/队列、轮次后测验、session 结构扩展
  - `frontend/src/views/recitation/PushCards.vue`：新组件（弹卡 + 通知升级）
  - `frontend/src/views/recitation/RecordsModule.vue`：新组件
  - `frontend/src/views/Words.vue`：加「弹卡背诵」「背诵记录」tab
  - `frontend/src/api/words.ts`：新接口函数与类型

## 测试策略

- 后端 SM2+ 状态机为主单元测试目标（RED→GREEN→REFACTOR，TDD 强制）：各状态×各档位的转移、间隔公式、旧三档映射
- quiz 出题（干扰项互斥、命中正确答案）、导出/导入解析逻辑
- 前端以 `npm run build`（vue-tsc）作为类型与构建校验；`backend` 跑 `pytest`

## 明确不做（YAGNI）

- 不做系统级 Web Push（Service Worker/VAPID），浏览器关闭也能推送——仅在站内弹卡 + 页面后台时升浏览器通知
- 不做 ToastFish 的「填空题」题型（只做中译英/英译中选择题）
- 不做政治背诵的推送/测验改造（本设计仅针对单词）
- 不重构现有 `get_today_words` 等旧接口（保留兼容返回），仅 `study` 升级