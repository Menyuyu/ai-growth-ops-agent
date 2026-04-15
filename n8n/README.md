# n8n 增长运营工作流

## 快速开始

### 1. 安装 n8n Desktop

- 下载地址：https://n8n.io/download/
- Windows 用户直接下载桌面版，一键安装
- 安装后启动，默认地址：http://localhost:5678

### 2. 启动 Python API 服务

```bash
# 复制并编辑 .env 文件，填入你的 API Key
cp .env.example .env

# 启动 FastAPI 服务
cd api
uvicorn server:app --host 0.0.0.0 --port 8000
```

> API 服务运行在 `http://localhost:8000`，n8n 通过 HTTP 请求调用

### 3. 导入工作流

1. 打开 n8n Desktop
2. 点击右上角 **+** 创建新工作流
3. 点击右下角 **...** 菜单 → **Import from File**
4. 选择 `growth-loop.workflow.json`
5. 点击 **Activate** 激活工作流

### 4. 运行工作流

- 点击 **Execute Workflow** 按钮
- 工作流会依次执行：
  1. **漏斗诊断** → 识别流失最严重的环节
  2. **用户分层** → 定位高优先级用户群体
  3. **策略推荐** → 生成增长策略
  4. **内容生成** → 生成多版内容变体
  5. **等待 A/B 数据** → 暂停（测试时可跳过）
  6. **A/B 测试分析** → 判断获胜版本
  7. **知识沉淀** → 记录实验结果

### 5. A/B 测试数据回传（高级）

实际部署时，A/B 测试数据通过 Webhook 回传：

1. 在 n8n 中添加 Webhook 节点，URL 设置为 `http://localhost:5678/webhook/ab-test-callback`
2. 业务系统在完成 A/B 测试后 POST 数据到该 Webhook
3. 工作流从 Wait 节点恢复，继续执行分析

## 节点说明

| 节点 | 调用 API | 说明 |
|------|---------|------|
| 1. 漏斗诊断 | `POST /api/diagnose` | 自动分析用户漏斗，找到最严重的流失环节 |
| 2. 用户分层 | `POST /api/segment` | 基于诊断结果定位高优先级目标用户 |
| 3a. 策略推荐 | `POST /api/strategy` | 根据漏斗问题和用户分层推荐增长策略 |
| 3b. 内容生成 | `POST /api/generate` | 基于策略生成多个内容变体 |
| 等待 A/B 数据 | Wait Node | 暂停工作流，等待真实 A/B 数据 |
| 4. A/B 测试分析 | `POST /api/abtest` | 输入实验数据，返回获胜版本 |
| 5. 知识沉淀 | `POST /api/memory/record` | 记录实验结果到知识库 |

## 面试演示建议

### 3 分钟演示脚本

1. **开场**（30秒）："这是一个增长运营自动化系统，把日常的增长工作流程化、自动化"
2. **展示 n8n 工作流**（30秒）："用 n8n 搭建可视化工作流，6个阶段一目了然"
3. **触发执行**（1分钟）："点击执行，系统自动调用 Python API——RFM分层、统计检验、LLM策略引擎"
4. **查看结果**（30秒）："每个节点的输入输出都可以在 n8n 界面直接查看"
5. **总结**（30秒）："从发现问题到验证效果到知识沉淀，整个闭环自动化完成"

### 关键截图清单

- [ ] n8n 工作流全景图（6个阶段完整链路）
- [ ] 漏斗诊断节点详情（输入/输出）
- [ ] 用户分层节点详情（用户画像）
- [ ] 内容生成节点详情（3版变体）
- [ ] A/B测试分析节点详情（获胜版本+报告）
- [ ] Python API 代码片段（RFM模型、Z-test）

## 故障排查

| 问题 | 解决 |
|------|------|
| HTTP Request 节点报 404 | 确认 Python API 服务已启动在 8000 端口 |
| API 返回 500 | 检查 `.env` 中的 API Key 是否正确 |
| Wait 节点不恢复 | 点击 "Execute Workflow" 手动恢复，或配置 Webhook |
| n8n 无法连接 localhost:8000 | 检查防火墙是否放行 8000 端口 |
