# VideoSum API接口文档

> REST API接口定义和使用说明。

---

## 1. 基础信息

**Base URL**: `http://localhost:8000/api`

**Content-Type**: `application/json`

**认证**: 无（本地应用）

---

## 2. 接口列表

### 2.1 视频处理

#### POST /api/video/summarize

视频总结接口

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 视频URL或本地文件路径 |
| language | string | 否 | 输出语言（zh/en/de），默认zh |

**请求示例**：

```json
{
    "url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "language": "zh"
}
```

**响应示例**：

```json
{
    "task_id": "abc12345",
    "status": "completed",
    "summary": "# 视频总结\n\n## 主要内容\n\n视频讲述了...",
    "key_points": ["要点1", "要点2", "要点3"],
    "processing_time": 45.2,
    "token_count": 1234
}
```

**错误响应**：

```json
{
    "detail": "URL格式错误"
}
```

---

#### POST /api/video/qa

视频问答接口

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |
| question | string | 是 | 用户问题 |

**请求示例**：

```json
{
    "task_id": "abc12345",
    "question": "视频主要讲了什么？"
}
```

**响应示例**：

```json
{
    "answer": "视频主要讲述了...",
    "source_segments": [
        {
            "start": 10.5,
            "end": 25.3,
            "text": "..."
        }
    ]
}
```

---

#### GET /api/video/{task_id}

获取任务状态

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务ID |

**响应示例**：

```json
{
    "task_id": "abc12345",
    "status": "completed",
    "progress": 100,
    "video_metadata": {
        "url": "https://...",
        "title": "视频标题",
        "duration": 300.5,
        "uploader": "UP主"
    },
    "transcription": {
        "segments": [...],
        "language": "zh",
        "duration": 300.5
    },
    "summary": {
        "full_summary": "# 视频总结...",
        "key_points": ["要点1", "要点2"],
        "total_tokens": 1234,
        "processing_time": 45.2
    },
    "cost": {
        "asr_cost": 0.0,
        "llm_cost": 0.0,
        "total_cost": 0.0
    }
}
```

---

### 2.2 配置管理

#### GET /api/config

获取当前配置

**响应示例**：

```json
{
    "app": {
        "output_dir": "~/Videos/SummaryOutput",
        "temp_dir": "~/tmp/videosummary",
        "language": "zh"
    },
    "asr": {
        "backend": "local",
        "local": {
            "model_size": "large-v3",
            "device": "auto"
        }
    },
    "llm": {
        "backend": "deepseek",
        "deepseek": {
            "model": "deepseek-chat",
            "temperature": 0.3
        }
    }
}
```

---

#### POST /api/config

更新配置

**请求参数**：

```json
{
    "llm": {
        "backend": "deepseek",
        "deepseek": {
            "api_key": "sk-xxx",
            "model": "deepseek-chat"
        }
    }
}
```

**响应示例**：

```json
{
    "status": "ok",
    "message": "配置已保存"
}
```

---

#### POST /api/config/test-asr

测试ASR连接

**响应示例**：

```json
{
    "status": "ok",
    "message": "ASR连接成功",
    "details": {
        "backend": "local",
        "model": "large-v3"
    }
}
```

---

#### POST /api/config/test-llm

测试LLM连接

**响应示例**：

```json
{
    "status": "ok",
    "message": "LLM连接成功",
    "details": {
        "provider": "deepseek",
        "model": "deepseek-chat"
    }
}
```

---

### 2.3 任务管理

#### GET /api/tasks

获取任务列表

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 按状态筛选 |
| limit | int | 返回数量，默认100 |
| offset | int | 偏移量，默认0 |

**响应示例**：

```json
{
    "tasks": [
        {
            "task_id": "abc12345",
            "title": "视频标题",
            "status": "completed",
            "progress": 100,
            "created_at": "2026-05-31T10:00:00",
            "updated_at": "2026-05-31T10:01:30"
        }
    ],
    "total": 1
}
```

---

#### DELETE /api/tasks/{task_id}

删除任务

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务ID |

**响应示例**：

```json
{
    "status": "ok",
    "message": "任务已删除"
}
```

---

### 2.4 日志管理

#### GET /api/logs

获取日志

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| level | string | 日志级别筛选 |
| limit | int | 返回数量，默认1000 |
| offset | int | 偏移量，默认0 |

**响应示例**：

```json
{
    "logs": [
        {
            "time": "2026-05-31 10:00:00",
            "level": "INFO",
            "logger": "videosum.scheduler",
            "message": "任务 abc12345 开始处理"
        }
    ],
    "total": 150
}
```

---

#### DELETE /api/logs

清空日志

**响应示例**：

```json
{
    "status": "ok",
    "message": "日志已清空"
}
```

---

### 2.5 插件管理

#### GET /api/plugins

获取插件列表

**响应示例**：

```json
{
    "plugins": [
        {
            "name": "vision",
            "version": "0.1.0",
            "description": "视觉增强插件",
            "enabled": true,
            "installed": true
        }
    ]
}
```

---

#### POST /api/plugins/{name}/toggle

启用/禁用插件

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 插件名称 |

**响应示例**：

```json
{
    "status": "ok",
    "enabled": false,
    "message": "插件已禁用"
}
```

---

#### POST /api/plugins/{name}/install

安装插件

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 插件名称 |

**响应示例**：

```json
{
    "status": "ok",
    "message": "插件安装成功"
}
```

---

## 3. 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 4. 使用示例

### 4.1 cURL

```bash
# 视频总结
curl -X POST http://localhost:8000/api/video/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx411c7mD", "language": "zh"}'

# 获取配置
curl http://localhost:8000/api/config

# 获取任务列表
curl http://localhost:8000/api/tasks
```

### 4.2 Python

```python
import requests

# 视频总结
response = requests.post(
    "http://localhost:8000/api/video/summarize",
    json={"url": "https://...", "language": "zh"}
)
result = response.json()
print(result["summary"])
```

### 4.3 JavaScript

```javascript
// 视频总结
const response = await fetch('http://localhost:8000/api/video/summarize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ url: 'https://...', language: 'zh' })
})
const result = await response.json()
console.log(result.summary)
```

---

*文档更新时间：2026-05-31*
