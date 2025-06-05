# RagFlow Service

一个简单的Flask服务，用于与RagFlow API进行交互。

## 功能特点

- 提供简洁的REST API接口
- 管理用户会话和上下文
- 与RagFlow API集成
- 支持会话过期和清理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制`.env.example`文件为`.env`，并根据您的环境进行配置：

```bash
cp .env .env
```

编辑`.env`文件，填入您的RagFlow API密钥和其他配置。

### 3. 运行服务

```bash
python app.py
```

服务将在`http://localhost:5000`上启动。

### 4. 使用Docker运行（可选）

```bash
docker build -t ragflow-service .
docker run -p 5000:5000 --env-file .env ragflow-service
```

## API接口

### 聊天接口

**请求**:
```
POST /api/chat
```

**请求体**:
```json
{
  "question": "您的问题",
  "session_id": "可选的会话ID",
  "user_id": "可选的用户ID",
  "context": {}
}
```

**响应**:
```json
{
  "session_id": "会话ID",
  "answer": "回答内容",
  "error": false,
  "ragflow_session_id": "RagFlow会话ID"
}
```

### 清除会话

**请求**:
```
DELETE /api/sessions/{session_id}
```

**响应**:
```json
{
  "status": "success",
  "message": "会话已清除"
}
```

### 清除所有会话

**请求**:
```
DELETE /api/sessions
```

**响应**:
```json
{
  "status": "success",
  "message": "所有会话已清除"
}
```

## 运行测试

```bash
python -m unittest discover tests
```

## 许可证

MIT