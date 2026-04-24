#!/usr/bin/env python3
"""
OpenAI Privacy Filter - Agent CLI 接口
支持命令行参数和 JSON 输入输出，便于 agent 调用

用法：
  # 1. 命令行参数
  python agent_cli.py --text "My email is test@example.com"
  
  # 2. JSON 输入（支持批量）
  python agent_cli.py --json '{"texts": ["text1", "text2"]}'
  
  # 3. 从 stdin 读取
  echo "My email is test@example.com" | python agent_cli.py --stdin
  
  # 4. 仅脱敏模式
  python agent_cli.py --text "..." --redact-only
"""

import argparse
import json
import sys
from transformers import pipeline

# 全局缓存，避免重复加载
_classifier = None

def get_classifier():
    """获取或加载分类器（单例模式）"""
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            task="token-classification",
            model="openai/privacy-filter",
            aggregation_strategy="simple",
        )
    return _classifier

def detect_pii(text):
    """
    检测文本中的 PII
    
    Args:
        text: 输入文本
        
    Returns:
        dict: 检测结果
    """
    classifier = get_classifier()
    results = classifier(text)
    
    # 转换为纯 Python 类型（便于 JSON 序列化）
    entities = []
    for r in results:
        entities.append({
            "type": r["entity_group"],
            "text": r["word"].strip(),
            "start": int(r["start"]),
            "end": int(r["end"]),
            "confidence": float(r["score"])
        })
    
    return {
        "input": text,
        "entities": entities,
        "entity_count": len(entities)
    }

def redact_pii(text, replacement_template="[REDACTED:{type}]"):
    """
    脱敏文本中的 PII
    
    Args:
        text: 输入文本
        replacement_template: 替换模板，支持 {type} 占位符
        
    Returns:
        dict: 脱敏结果
    """
    classifier = get_classifier()
    results = classifier(text)
    
    if not results:
        return {
            "input": text,
            "output": text,
            "redacted": False,
            "entities": []
        }
    
    # 从后往前替换（避免索引偏移）
    # 先收集所有需要替换的信息
    replacements = []
    entities = []
    for r in sorted(results, key=lambda x: x["start"], reverse=True):
        entity_type = r["entity_group"]
        # 获取原始文本中的实际内容（使用 start/end 索引）
        original = text[r["start"]:r["end"]]
        replacement = replacement_template.format(type=entity_type.upper())
        replacements.append((int(r["start"]), int(r["end"]), replacement))
        entities.append({
            "type": entity_type,
            "original": original.strip(),
            "replacement": replacement,
            "position": [int(r["start"]), int(r["end"])]
        })
    
    # 执行替换
    output = text
    for start, end, replacement in replacements:
        output = output[:start] + replacement + output[end:]
    
    return {
        "input": text,
        "output": output,
        "redacted": True,
        "entity_count": len(entities),
        "entities": entities
    }

def process_single(text, redact_only=False):
    """处理单个文本"""
    if redact_only:
        return redact_pii(text)
    else:
        return detect_pii(text)

def process_batch(texts, redact_only=False):
    """处理批量文本"""
    results = []
    for text in texts:
        results.append(process_single(text, redact_only))
    return results

def main():
    parser = argparse.ArgumentParser(
        description="OpenAI Privacy Filter - Agent CLI 接口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检测单个文本
  python agent_cli.py --text "My email is test@example.com"
  
  # 脱敏文本
  python agent_cli.py --text "My email is test@example.com" --redact-only
  
  # 批量处理（JSON 输入）
  python agent_cli.py --json '{"texts": ["text1", "text2"], "redact": true}'
  
  # 从 stdin 读取
  echo "My email is test@example.com" | python agent_cli.py --stdin
        """
    )
    
    parser.add_argument("--text", "-t", type=str, help="要处理的单个文本")
    parser.add_argument("--json", "-j", type=str, help="JSON 格式输入")
    parser.add_argument("--stdin", "-s", action="store_true", help="从 stdin 读取文本")
    parser.add_argument("--redact-only", "-r", action="store_true", help="仅脱敏模式（不返回检测结果）")
    parser.add_argument("--pretty", "-p", action="store_true", help="格式化 JSON 输出")
    
    args = parser.parse_args()
    
    try:
        # 确定输入来源
        if args.text:
            input_data = args.text
            result = process_single(input_data, args.redact_only)
        elif args.json:
            data = json.loads(args.json)
            texts = data.get("texts", [data.get("text", "")])
            redact = data.get("redact", args.redact_only)
            if len(texts) == 1:
                result = process_single(texts[0], redact)
            else:
                result = {"batch": True, "results": process_batch(texts, redact)}
        elif args.stdin:
            input_data = sys.stdin.read().strip()
            if not input_data:
                print(json.dumps({"error": "No input provided"}))
                sys.exit(1)
            # 支持多行输入（每行一个文本）
            lines = [l for l in input_data.split("\n") if l.strip()]
            if len(lines) == 1:
                result = process_single(lines[0], args.redact_only)
            else:
                result = {"batch": True, "results": process_batch(lines, args.redact_only)}
        else:
            parser.print_help()
            sys.exit(1)
        
        # 输出结果
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))
        
    except Exception as e:
        error_result = {"error": str(e), "type": type(e).__name__}
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
