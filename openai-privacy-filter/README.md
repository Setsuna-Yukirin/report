# OpenAI Privacy Filter - 本地部署与测试报告

## 📋 模型信息

| 特性 | 详情 |
|------|------|
| **模型名称** | `openai/privacy-filter` |
| **发布方** | OpenAI |
| **参数量** | 1.5B 总参数，50M 激活参数 (MoE 架构) |
| **模型类型** | Token Classification (PII 检测与脱敏) |
| **上下文长度** | 128,000 tokens |
| **许可证** | Apache 2.0 (可商用) |
| **架构** | 8 层 Transformer，稀疏 MoE (128 个专家，每 token 激活 4 个) |
| **Hugging Face** | https://huggingface.co/openai/privacy-filter |

## 🎯 功能用途

检测和模糊化文本中的**个人身份信息 (PII)**，包括：
- ✅ 姓名 (private_person)
- ✅ 邮箱地址 (private_email)
- ✅ 电话号码 (private_phone)
- ✅ 地址 (private_address)
- ✅ 账号/卡号 (account_number)
- ✅ 密钥/密码 (secret)
- ✅ 身份证号等

## 📁 目录结构

```
openai-privacy-filter/
├── agent_cli.py               # Agent CLI 接口（推荐）
├── privacy_filter_lib.py      # Python 模块库
├── privacy_filter_demo.py     # 基础示例脚本
├── detailed_demo.py           # 详细演示脚本
├── agent_example.py           # Agent 使用示例
├── install.sh                 # 安装脚本
└── README.md                  # 本文档
```

## 🚀 快速开始

### 安装

```bash
cd ~/privacy_filter_deploy
./install.sh
```

### 使用

```bash
# 激活虚拟环境
source venv/bin/activate

# 检测 PII
python agent_cli.py --text "My email is test@example.com" --pretty

# 脱敏文本
python agent_cli.py --text "My email is test@example.com" --redact-only --pretty
```

## 📊 测试结果

### 测试 1：个人敏感信息

**输入：**
```
我今年 13 岁了，这是我的邮箱：agujbf5@outlook.com。我就读于南阳理工学院。我的成绩位于全年级第二名。我上次考试就得了 93 分的好成绩。我的内网地址现在是 192.168.1.102。我的公网地址是 21.45.32.102。欢迎大家顺着网线来打我，哈哈哈我在河南的邮政银行里面存款是大约 24017 元。我还搞股票和比特币，现在比特币的价格是 1 万 3 左右，我现在有 0.6 枚比特币
```

**输出：**
```json
{
  "input": "我今年 13 岁了，这是我的邮箱：agujbf5@outlook.com。我就读于南阳理工学院。...",
  "output": "我今年 13 岁了，这是我的邮箱：[REDACTED:PRIVATE_EMAIL][REDACTED:PRIVATE_EMAIL]。我就读于南阳理工学院。...",
  "redacted": true,
  "entity_count": 2,
  "entities": [
    {
      "type": "private_email",
      "original": ".com",
      "replacement": "[REDACTED:PRIVATE_EMAIL]",
      "position": [32, 36]
    },
    {
      "type": "private_email",
      "original": "agujbf5@outlook",
      "replacement": "[REDACTED:PRIVATE_EMAIL]",
      "position": [17, 32]
    }
  ]
}
```

**结论：** 仅检测到邮箱地址，未检测到年龄、学校、IP 地址、存款金额、加密货币等敏感信息。

---

### 测试 2：复杂.env 文件（编程环境敏感信息）

**测试文件：** `test_complex.env` (6061 字符，166 行) - *未提交到仓库（包含测试假密钥）*

**包含的敏感配置项：** 30+ 个（API 密钥、数据库密码、云服务商密钥、加密货币私钥等）

#### ✅ 成功检测到的敏感信息（45+ 项）

| 配置项 | 类型 | 置信度 |
|--------|------|--------|
| `SECRET_KEY=sk_live_****` | `secret` | 99.96% |
| `DATABASE_URL=postgresql://admin:****@...` | `secret` | 83.92% |
| `DB_PASSWORD=****` | `secret` | 98.29% |
| `AWS_SECRET_ACCESS_KEY=wJalrX......` | `secret` | 99.93% |
| `AZURE_STORAGE_KEY=DefaultEndpointsProtocol=...` | `secret` | 98.34% |
| `GCP_API_KEY=AIzaSy......` | `secret` | 99.94% |
| `STRIPE_SECRET_KEY=sk_live_****` | `secret` | 99.94% |
| `JWT_SECRET=eyJhbG......` | `secret` | 99.85% |
| `GITHUB_TOKEN=ghp_****` | `secret` | 98.29% |
| `OPENAI_API_KEY=sk-****` | `secret` | 95.41% |
| `ANTHROPIC_API_KEY=sk-ant-****` | `secret` | 98.95% |
| `HUGGINGFACE_TOKEN=hf_****` | `secret` | 99.80% |
| `BITCOIN_PRIVATE_KEY=5Kb8kLf9zgWQnogidDA76Mz...` | `secret` | 96.92% |
| `ETHEREUM_PRIVATE_KEY=0x1234567890abcdef...` | `secret` | 97.79% |
| `ETH_WALLET_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f8bE21` | `account_number` | 98.63% |
| `SSH_PASSWORD=****` | `secret` | 99.67% |
| `VPN_PASSWORD=****` | `secret` | 86.83% |
| `ADMIN_PASSWORD=****` | `secret` | 91.35% |
| `USER_ID_CARD=110101199001011234` | `account_number` | 91.05% |
| `USER_ADDRESS=北京市朝阳区建国路 100 号` | `private_address` | 98.95% |
| `USER_BANK_ACCOUNT=6222001234567890123` | `account_number` | 96.25% |
| `ALIBABA_CLOUD_ACCESS_KEY_ID=LTAI1234567890ab` | `secret` | 93.73% |
| `TENCENT_CLOUD_SECRET_ID=AKID12......` | `secret` | 94.79% |

#### ❌ 未检测到的敏感信息

| 配置项 | 说明 |
|--------|------|
| `AWS_ACCESS_KEY_ID=AKIAIO...MPLE` | AWS 访问密钥 ID |
| `REDIS_URL=redis://:****@cache.example.com:6379/0` | Redis 连接字符串 |
| `REDIS_PASSWORD=****` | Redis 密码 |
| `BITCOIN_WIF=5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF` | 比特币 WIF 密钥 |
| `ENCRYPTION_KEY=AES256Key-1234567890abcdef...` | 加密密钥 |
| `USER_EMAIL=contact@example.com` | 用户邮箱 |
| `USER_PHONE=+86-138-0013-8000` | 用户电话 |
| `INTERNAL_IP=10.0.0.100` | 内网 IP |
| `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...` | Slack Webhook URL |

#### 📈 统计总结

| 指标 | 数值 |
|------|------|
| **总测试项** | 60+ |
| **成功检测** | ~45 项 |
| **未检测/误报** | ~15 项 |
| **检测率** | ~75% |

---

## 🔍 结论

### ✅ 模型擅长检测
- API 密钥（各种格式）
- 数据库密码/连接字符串
- 云服务商密钥（AWS/Azure/GCP/阿里云/腾讯云）
- 加密货币私钥
- 邮箱地址
- 物理地址
- 银行卡号/身份证号

### ❌ 模型不擅长/误报
- 某些 IP 地址（误报为 `private_url`）
- 部分连接字符串（如 Redis）
- 客户端 ID/公钥（部分未检测）
- 某些非标准格式的密钥
- 内部服务 URL

### 💡 建议
对于生产环境的 `.env` 文件检测：
1. 使用此模型作为基础检测
2. 添加正则表达式规则补充（如 IP 地址、特定格式的密钥）
3. 对未检测到的类型进行模型微调
4. 结合其他专用工具使用

---

## 📝 使用方法

### CLI 调用

```bash
# 检测 PII
python agent_cli.py --text "My email is test@example.com" --pretty

# 脱敏文本
python agent_cli.py --text "My email is test@example.com" --redact-only --pretty

# 批量处理
python agent_cli.py --json '{"texts": ["text1", "text2"], "redact": true}' --pretty
```

### Python 模块

```python
from privacy_filter_lib import PrivacyFilter

pf = PrivacyFilter()
result = pf.detect("My email is test@example.com")
print(result)
```

---

## 🔗 相关链接

- [Hugging Face 模型页面](https://huggingface.co/openai/privacy-filter)
- [OpenAI 官方文档](https://openai.com/)
- [Transformers 文档](https://huggingface.co/docs/transformers)

---
**测试日期**: 2025 年 4 月 24 日  
**测试环境**: WSL2 (Ubuntu 22.04.5 LTS), Python 3.10
