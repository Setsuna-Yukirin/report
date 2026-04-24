#!/usr/bin/env python3
"""
OpenAI Privacy Filter - Python 模块接口
可直接 import 使用，便于 agent 和其他程序调用

用法:
    from privacy_filter_lib import PrivacyFilter
    
    # 创建实例
    pf = PrivacyFilter()
    
    # 检测 PII
    result = pf.detect("My email is test@example.com")
    print(result)
    
    # 脱敏
    result = pf.redact("My email is test@example.com")
    print(result["output"])
    
    # 批量处理
    results = pf.batch_detect(["text1", "text2"])
"""

from transformers import pipeline

class PrivacyFilter:
    """OpenAI Privacy Filter 封装类"""
    
    def __init__(self, model_name="openai/privacy-filter"):
        """
        初始化 PrivacyFilter
        
        Args:
            model_name: 模型名称或路径
        """
        self.model_name = model_name
        self._classifier = None
    
    def _get_classifier(self):
        """懒加载分类器"""
        if self._classifier is None:
            self._classifier = pipeline(
                task="token-classification",
                model=self.model_name,
                aggregation_strategy="simple",
            )
        return self._classifier
    
    def detect(self, text):
        """
        检测文本中的 PII
        
        Args:
            text: 输入文本
            
        Returns:
            dict: 检测结果
                - input: 输入文本
                - entities: 实体列表
                - entity_count: 实体数量
        """
        classifier = self._get_classifier()
        results = classifier(text)
        
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
    
    def redact(self, text, replacement_template="[REDACTED:{type}]"):
        """
        脱敏文本中的 PII
        
        Args:
            text: 输入文本
            replacement_template: 替换模板，支持 {type} 占位符
            
        Returns:
            dict: 脱敏结果
                - input: 输入文本
                - output: 脱敏后文本
                - redacted: 是否进行了脱敏
                - entities: 被脱敏的实体列表
        """
        classifier = self._get_classifier()
        results = classifier(text)
        
        if not results:
            return {
                "input": text,
                "output": text,
                "redacted": False,
                "entities": []
            }
        
        # 从后往前替换
        replacements = []
        entities = []
        for r in sorted(results, key=lambda x: x["start"], reverse=True):
            entity_type = r["entity_group"]
            original = text[r["start"]:r["end"]]
            replacement = replacement_template.format(type=entity_type.upper())
            replacements.append((int(r["start"]), int(r["end"]), replacement))
            entities.append({
                "type": entity_type,
                "original": original.strip(),
                "replacement": replacement,
                "position": [int(r["start"]), int(r["end"])]
            })
        
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
    
    def batch_detect(self, texts):
        """
        批量检测多个文本
        
        Args:
            texts: 文本列表
            
        Returns:
            list: 检测结果列表
        """
        return [self.detect(text) for text in texts]
    
    def batch_redact(self, texts, replacement_template="[REDACTED:{type}]"):
        """
        批量脱敏多个文本
        
        Args:
            texts: 文本列表
            replacement_template: 替换模板
            
        Returns:
            list: 脱敏结果列表
        """
        return [self.redact(text, replacement_template) for text in texts]


# 便捷函数
def detect(text):
    """快速检测 PII"""
    pf = PrivacyFilter()
    return pf.detect(text)

def redact(text, replacement_template="[REDACTED:{type}]"):
    """快速脱敏"""
    pf = PrivacyFilter()
    return pf.redact(text, replacement_template)


# CLI 入口（当直接运行时）
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = detect(text)
        print(f"检测到 {result['entity_count']} 个 PII 实体:")
        for e in result["entities"]:
            print(f"  - [{e['type']}] {e['text']} (置信度：{e['confidence']:.2%})")
    else:
        print("用法：python privacy_filter_lib.py <文本>")
        print("或直接 import 使用:")
        print("  from privacy_filter_lib import PrivacyFilter")
        print("  pf = PrivacyFilter()")
        print("  result = pf.detect('Your text here')")
