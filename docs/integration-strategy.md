# 两人团队开发集成策略

## 分支结构

```
master
├── feature/testing-workflow     # 测试工程师分支
└── feature/local-llm-deployment # LLM部署工程师分支
```

## 工作流隔离规则

### 测试工程师 (`feature/testing-workflow`)
- **职责**: 测试现有功能、修复bug、优化测试用例
- **环境**: 端口8000(后端)/5173(前端), 数据库`kaoyan_xt_test.db`
- **禁止**: 修改AI服务核心逻辑、添加新的LLM依赖

### LLM部署工程师 (`feature/local-llm-deployment`)
- **职责**: 部署本地开源大语言模型、优化推理性能
- **环境**: 端口8080(后端)/5180(前端), 数据库`kaoyan_xt_llm.db`
- **禁止**: 修改业务逻辑、改动测试用例

## 集成流程

### Step 1: 功能完成检查
1. 测试工程师确认所有测试通过
2. LLM部署工程师确认本地模型服务正常运行

### Step 2: 创建集成分支
```bash
git checkout master
git pull origin master
git checkout -b feature/integration
```

### Step 3: 合并测试分支
```bash
git merge --no-ff feature/testing-workflow
git commit -m "merge: integrate testing workflow changes"
```

### Step 4: 合并LLM部署分支
```bash
git merge --no-ff feature/local-llm-deployment
git commit -m "merge: integrate local LLM deployment"
```

### Step 5: 集成测试
1. 运行完整测试套件
2. 验证AI功能在本地LLM和远程API模式下都能正常工作
3. 检查数学公式渲染是否正确

### Step 6: 推送到主分支
```bash
git checkout master
git merge --no-ff feature/integration
git push origin master
```

### Step 7: 删除临时分支
```bash
git branch -d feature/testing-workflow
git branch -d feature/local-llm-deployment
git branch -d feature/integration
git push origin --delete feature/testing-workflow feature/local-llm-deployment
```

## 配置合并策略

### AI服务配置 (.env)
- `USE_LOCAL_LLM`: 默认为`false`，生产环境使用远程API
- `AI_BASE_URL`: 保留远程API地址作为默认值
- `LLM_MODEL_NAME`: 保留本地模型配置，用于开发环境

### 端口配置
- 生产环境: 前端5173, 后端8000
- 开发环境: 根据需求选择

## 回滚策略

如果集成出现问题，使用以下命令回滚：

```bash
git revert <merge-commit-hash>
```

## 沟通协调

1. 每日站会同步进度
2. 合并前互相通知
3. 冲突解决优先考虑主分支逻辑
4. AI服务接口变更需提前沟通
