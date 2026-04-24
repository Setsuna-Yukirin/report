#!/usr/bin/env python3
"""
Agent 使用示例 - 如何在 agent 代码中集成 Privacy Filter

这个脚本展示了 agent 可以如何使用 Privacy Filter 来处理用户输入
"""

import subprocess
import json

def run_privacy_filter(text, mode="detect"):
    """
    调用 Privacy Filter CLI
    
    Args:
        text: 要处理的文本
        mode: "detect" (检测) 或 "redact" (脱敏)
        
    Returns:
        dict: 处理结果
    """
    cmd = [
        "python", "agent_cli.py",
        "--text", text,
        "--pretty"
    ]
    
    if mode == "redact":
        cmd.insert(-1, "--redact-only")
    
    result = subprocess.run(
        cmd,
        cwd="/home/vanilla0302/privacy_filter_deploy",
        capture_output=True,
        text=True
    )
    
    return json.loads(result.stdout)

def check_and_redact(user_input):
    """
    Agent 工作流：检查并脱敏用户输入中的敏感信息
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        dict: 包含检测结果和脱敏后的文本
    """
    # 第一步：检测 PII
    detect_result = run_privacy_filter(user_input, mode="detect")
    
    # 第二步：如果有 PII，进行脱敏
    if detect_result["entity_count"] > 0:
        redact_result = run_privacy_filter(user_input, mode="redact")
        return {
            "has_pii": True,
            "pii_count": detect_result["entity_count"],
            "pii_types": list(set(e["type"] for e in detect_result["entities"])),
            "safe_text": redact_result["output"],
            "original_text": user_input
        }
    else:
        return {
            "has_pii": False,
            "pii_count": 0,
            "pii_types": [],
            "safe_text": user_input,
            "original_text": user_input
        }

# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Agent Privacy Filter 使用示例")
    print("=" * 70)
    
    # 示例 1：检测模式
    print("\n【示例 1】检测用户输入中的 PII")
    print("-" * 70)
    user_input = "My name is Alice, email: alice@example.com"
    print(f"用户输入：{user_input}")
    
    result = run_privacy_filter(user_input, mode="detect")
    print(f"\n检测结果:")
    print(f"  - 发现 {result['entity_count']} 个 PII 实体")
    for e in result["entities"]:
        print(f"  - [{e['type']}] {e['text']} (置信度：{e['confidence']:.2%})")
    
    # 示例 2：脱敏模式
    print("\n【示例 2】脱敏后存储/转发")
    print("-" * 70)
    user_input = "Contact John at john@company.com or 555-1234"
    print(f"用户输入：{user_input}")
    
    result = run_privacy_filter(user_input, mode="redact")
    print(f"\n脱敏后文本：{result['output']}")
    print(f"脱敏实体数：{result['entity_count']}")
    
    # 示例 3：完整工作流
    print("\n【示例 3】完整工作流 - 检查并脱敏")
    print("-" * 70)
    test_inputs = [
        "My email is test@example.com",
        "No sensitive data here",
        "Call me at 138-0013-8000",
    ]
    
    for text in test_inputs:
        print(f"\n输入：{text}")
        result = check_and_redact(text)
        if result["has_pii"]:
            print(f"  ⚠️  检测到 {result['pii_count']} 个 PII ({', '.join(result['pii_types'])})")
            print(f"  ✅ 安全文本：{result['safe_text']}")
        else:
            print(f"  ✅ 无敏感信息，可直接使用")
    
    print("\n" + "=" * 70)
    print("示例完成！")
    print("=" * 70)
