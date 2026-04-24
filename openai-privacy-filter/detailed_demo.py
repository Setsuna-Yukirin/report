#!/usr/bin/env python3
"""
OpenAI Privacy Filter - 详细输入输出演示
展示模型如何检测和处理 PII 信息
"""

from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import torch
import json

print("=" * 80)
print("OpenAI Privacy Filter - 详细工作原理演示")
print("=" * 80)

# ============================================================
# 第一部分：模型基本信息
# ============================================================

print("\n【1】模型基本信息")
print("-" * 80)

model_name = "openai/privacy-filter"
print(f"模型名称：{model_name}")

# 加载 tokenizer 和模型
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

print(f"词表大小：{tokenizer.vocab_size}")
print(f"模型层数：{model.config.num_hidden_layers}")
print(f"隐藏层维度：{model.config.hidden_size}")
print(f"注意力头数：{model.config.num_attention_heads}")
print(f"标签类别数：{model.config.num_labels}")
print(f"\n标签映射 (ID → 类别):")
for label_id, label_name in model.config.id2label.items():
    print(f"  {label_id} → {label_name}")

# ============================================================
# 第二部分：模型工作原理
# ============================================================

print("\n\n【2】模型工作原理")
print("-" * 80)
print("""
这个模型是一个 Token Classification（词元分类）模型，工作流程如下：

1. 输入文本 → 2. Tokenizer 分词 → 3. 模型推理 → 4. 输出每个 token 的标签

例如：
  输入："My name is Alice"
  
  分词后：["My", "name", "is", "Alice"]
            ↓       ↓       ↓        ↓
  预测标签：[O]     [O]     [O]    [B-person]
  
  其中：
  - O = Outside (非 PII)
  - B-xxx = Begin (PII 实体开始)
  - I-xxx = Inside (PII 实体中间)
  - E-xxx = End (PII 实体结束)
  - S-xxx = Single (单个 token 的 PII)
""")

# ============================================================
# 第三部分：详细输入输出演示
# ============================================================

print("\n\n【3】详细输入输出演示")
print("-" * 80)

# 测试输入
test_input = "My name is Alice Smith, email: alice@example.com"

print(f"\n【输入文本】")
print(f"  {test_input}")

# 1. 分词过程
print(f"\n【分词过程】")
tokens = tokenizer.tokenize(test_input)
print(f"  Tokenizer 输出：{tokens}")

# 2. 转换为 ID
token_ids = tokenizer.encode(test_input, add_special_tokens=False)
print(f"  Token IDs: {token_ids}")

# 3. 模型推理
print(f"\n【模型推理】")
inputs = tokenizer(test_input, return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predictions = logits.argmax(dim=-1)

print(f"  输入 shape: {inputs['input_ids'].shape}")
print(f"  输出 logits shape: {logits.shape}")
print(f"  预测标签 IDs: {predictions[0].tolist()}")

# 4. 每个 token 的预测详情
print(f"\n【每个 Token 的预测详情】")
input_tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])

print(f"  {'Token':<20} {'预测标签':<25} {'置信度'}")
print(f"  {'-'*60}")

# 获取每个 token 的置信度
for i, (token, pred_id) in enumerate(zip(input_tokens, predictions[0])):
    token_logits = logits[0, i]
    pred_id_int = int(pred_id)
    confidence = torch.softmax(token_logits, dim=0)[pred_id_int].item()
    label_name = model.config.id2label.get(pred_id_int, "UNKNOWN")
    print(f"  {token:<20} {label_name:<25} {confidence:.4f}")

# ============================================================
# 第四部分：使用 pipeline 的聚合输出
# ============================================================

print("\n\n【4】使用 Pipeline 的聚合输出（推荐用法）")
print("-" * 80)

classifier = pipeline(
    task="token-classification",
    model=model_name,
    aggregation_strategy="simple",  # 将 token 级预测聚合为实体
)

test_cases = [
    "My name is Alice Smith, email: alice@example.com",
    "Call me at +1-555-123-4567",
    "Card: 4111-1111-1111-1111",
]

for text in test_cases:
    print(f"\n【输入】{text}")
    results = classifier(text)
    
    print(f"【输出】JSON 格式:")
    # 手动格式化输出，避免 numpy 类型问题
    print("[")
    for i, r in enumerate(results):
        comma = "," if i < len(results) - 1 else ""
        print(f"  {{'entity_group': '{r['entity_group']}', 'word': '{r['word']}', 'score': {r['score']:.4f}}}{comma}")
    print("]")
    
    # 提取检测到的实体
    if results:
        entities = [r['entity_group'] for r in results]
        words = [r['word'] for r in results]
        scores = [f"{r['score']:.2%}" for r in results]
        
        print(f"\n【摘要】")
        print(f"  检测到 {len(results)} 个 PII 实体:")
        for i, (entity, word, score) in enumerate(zip(entities, words, scores), 1):
            print(f"    {i}. 类型：{entity:<20} 内容：{word:<25} 置信度：{score}")
    else:
        print("  未检测到 PII 实体")

# ============================================================
# 第五部分：脱敏处理演示
# ============================================================

print("\n\n【5】脱敏处理演示")
print("-" * 80)

def redact_pii_detailed(text, classifier):
    """
    详细的 PII 脱敏函数，展示处理过程
    """
    print(f"\n原始文本：{text}")
    
    # 获取检测结果
    results = classifier(text)
    
    if not results:
        print("  → 未检测到 PII，无需脱敏")
        return text
    
    print(f"  → 检测到 {len(results)} 个 PII 实体:")
    for r in results:
        print(f"     - [{r['entity_group']}] '{r['word']}' (位置：{r['start']}-{r['end']}, 置信度：{r['score']:.2%})")
    
    # 从后往前替换（避免索引偏移）
    redacted = text
    for entity in sorted(results, key=lambda x: x['start'], reverse=True):
        old_text = entity['word']
        new_text = f"[{entity['entity_group'].upper()}]"
        redacted = redacted[:entity['start']] + new_text + redacted[entity['end']:]
        print(f"     → 替换：'{old_text}' → '{new_text}'")
    
    print(f"\n脱敏后文本：{redacted}")
    return redacted

print("\n【脱敏示例 1 - 英文】")
redact_pii_detailed("Contact John Doe at john.doe@company.com or 555-1234", classifier)

print("\n\n【脱敏示例 2 - 中文】")
redact_pii_detailed("张三的电话是 138-0013-8000，住在北京市朝阳区", classifier)

print("\n\n【脱敏示例 3 - 混合敏感信息】")
sensitive_text = """
用户注册信息：
姓名：李明
邮箱：liming@example.com
手机号：+86-139-1234-5678
身份证号：110101199001011234
收货地址：上海市浦东新区世纪大道 1000 号
信用卡：4532-1234-5678-9012
"""
redact_pii_detailed(sensitive_text, classifier)

# ============================================================
# 第六部分：模型能力总结
# ============================================================

print("\n\n【6】模型能力总结")
print("-" * 80)
print("""
✅ 这个模型能够做什么：
   1. 检测文本中的个人身份信息 (PII)
   2. 识别多种类型的敏感信息（姓名、邮箱、电话、地址、账号等）
   3. 输出每个实体的类型、位置和置信度
   4. 支持 128K 长度的文本（无需分块处理）
   5. 可以在本地运行，数据不出境

✅ 典型应用场景：
   1. 数据脱敏：在分享/发布数据前移除敏感信息
   2. 合规检查：确保文本符合隐私保护法规（如 GDPR）
   3. 日志清洗：自动清理日志文件中的敏感信息
   4. API 网关：在转发请求前过滤敏感数据
   5. 内容审核：检测用户提交内容中的隐私信息

❌ 这个模型不能做什么：
   1. 不能生成文本（它只分类，不生成）
   2. 不能理解上下文语义（只能识别模式）
   3. 不能检测所有类型的敏感信息（如商业机密）
   4. 对某些特殊格式的 PII 可能识别不准确
""")

print("\n" + "=" * 80)
print("演示完成！")
print("=" * 80)
