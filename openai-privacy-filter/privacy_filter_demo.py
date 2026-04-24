#!/usr/bin/env python3
"""
OpenAI Privacy Filter 本地部署示例脚本
模型：openai/privacy-filter
用途：检测和脱敏文本中的个人身份信息 (PII)
"""

# ============================================================
# 第一步：安装依赖
# ============================================================
# 在终端运行：
# pip install transformers torch accelerate sentencepiece

# ============================================================
# 第二步：基础用法示例
# ============================================================

from transformers import pipeline

print("=" * 60)
print("OpenAI Privacy Filter - PII 检测示例")
print("=" * 60)

# 加载模型（首次运行会自动下载，约 3GB）
print("\n正在加载模型...")
classifier = pipeline(
    task="token-classification",
    model="openai/privacy-filter",
    aggregation_strategy="simple",  # 将 token 级预测聚合为实体跨度
)

# 测试文本
test_texts = [
    "My name is Alice Smith and my email is alice@example.com",
    "Please call me at +1-555-123-4567 tomorrow",
    "My credit card number is 4111-1111-1111-1111",
    "The API key is sk-1234567890abcdef",
    "I live at 123 Main Street, New York, NY 10001",
]

# 运行检测
for text in test_texts:
    print(f"\n原文：{text}")
    results = classifier(text)
    if results:
        print("检测到的 PII 实体:")
        for entity in results:
            print(f"  - {entity['entity_group']}: {entity['word']} (置信度：{entity['score']:.4f})")
    else:
        print("未检测到 PII 实体")

# ============================================================
# 第三步：高级用法 - 手动脱敏
# ============================================================

def redact_pii(text, classifier, replacement="[REDACTED]"):
    """
    将文本中的 PII 替换为占位符
    """
    results = classifier(text)
    if not results:
        return text
    
    # 按位置排序，从后往前替换（避免索引偏移）
    results_sorted = sorted(results, key=lambda x: x['start'], reverse=True)
    
    redacted_text = text
    for entity in results_sorted:
        start = entity['start']
        end = entity['end']
        redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
    
    return redacted_text

print("\n" + "=" * 60)
print("PII 脱敏示例")
print("=" * 60)

sensitive_text = """
用户信息：
姓名：张三
邮箱：zhangsan@example.com
电话：+86-138-0013-8000
地址：北京市朝阳区建国路 100 号
身份证号：110101199001011234
"""

print(f"\n原始文本:\n{sensitive_text}")
redacted = redact_pii(sensitive_text, classifier)
print(f"\n脱敏后文本:\n{redacted}")

# ============================================================
# 第四步：批量处理（高吞吐量场景）
# ============================================================

from transformers import AutoModelForTokenClassification, AutoTokenizer
import torch

print("\n" + "=" * 60)
print("批量处理示例")
print("=" * 60)

# 加载模型用于批量处理
tokenizer = AutoTokenizer.from_pretrained("openai/privacy-filter")
model = AutoModelForTokenClassification.from_pretrained(
    "openai/privacy-filter",
    device_map="auto"  # 自动使用 GPU（如有）
)
model.eval()

# 批量文本
batch_texts = [
    "Contact John at john.doe@company.com",
    "Send payment to card 4532-1234-5678-9012",
    "No sensitive data here",
]

# 批量编码
inputs = tokenizer(
    batch_texts,
    padding=True,
    truncation=True,
    max_length=512,
    return_tensors="pt"
).to(model.device)

# 批量推理
with torch.no_grad():
    outputs = model(**inputs)
    predictions = outputs.logits.argmax(dim=-1)

print(f"批量处理完成，共处理 {len(batch_texts)} 条文本")

print("\n" + "=" * 60)
print("部署完成！")
print("=" * 60)
