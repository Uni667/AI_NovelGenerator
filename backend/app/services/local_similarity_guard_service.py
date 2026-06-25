import os
import json
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_NGRAM_OVERLAP_THRESHOLD = 0.05
DEFAULT_MAX_CONSECUTIVE_WORDS = 50
DEFAULT_LONG_SENTENCE_THRESHOLD = 3 # 允许最多3个长句完全重复
DEFAULT_PROPER_NOUN_OVERLAP_THRESHOLD = 10 # 最多重合10个专有名词

def build_ngrams(text: str, n: int = 4) -> set:
    words = list(text.replace(" ", "").replace("\n", ""))
    ngrams = set()
    for i in range(len(words) - n + 1):
        ngrams.add("".join(words[i:i+n]))
    return ngrams

def get_consecutive_overlap(text1: str, text2: str) -> str:
    # A simple longest common substring or just check if any 50-char chunk of text1 is in text2
    # To be safe and fast, we check chunks of 50
    t1 = text1.replace(" ", "").replace("\n", "")
    t2 = text2.replace(" ", "").replace("\n", "")
    chunk_size = 50
    if len(t1) < chunk_size:
        return ""
    for i in range(len(t1) - chunk_size + 1):
        chunk = t1[i:i+chunk_size]
        if chunk in t2:
            return chunk
    return ""

def extract_long_sentences(text: str, min_length: int = 15) -> set:
    sentences = re.split(r'[。！？.!?]+', text)
    return set(s.strip() for s in sentences if len(s.strip()) >= min_length)

def mock_extract_proper_nouns(text: str) -> set:
    # Since we might not have jieba, we'll mock proper noun extraction
    # by looking for words inside quotes or typical capitalized English words,
    # or just a placeholder logic.
    # In a real app, use jieba.posseg
    nouns = set(re.findall(r'「(.*?)」|“(.*?)”|《(.*?)》', text))
    # Flatten the tuples from findall
    flat_nouns = set(item for sublist in nouns for item in sublist if item)
    return flat_nouns

def analyze_similarity(generated_text: str, reference_texts: List[str], project_id: str) -> Dict[str, Any]:
    """
    Perform a similarity check between generated text and reference texts.
    Returns a report dictionary.
    """
    if not reference_texts:
        return {
            "needs_rewrite": False,
            "max_ngram_overlap_ratio": 0.0,
            "long_sentence_matches": [],
            "proper_noun_overlap": [],
            "rewrite_instruction": "",
            "message": "No reference texts provided."
        }
        
    combined_ref_text = "\n".join(reference_texts)
    
    # 1. N-Gram Overlap
    gen_ngrams = build_ngrams(generated_text, n=4)
    ref_ngrams = build_ngrams(combined_ref_text, n=4)
    overlap_ngrams = gen_ngrams.intersection(ref_ngrams)
    
    ngram_overlap_ratio = len(overlap_ngrams) / len(gen_ngrams) if gen_ngrams else 0.0
    
    # 2. Consecutive words
    consecutive_match = get_consecutive_overlap(generated_text, combined_ref_text)
    
    # 3. Long sentence matches
    gen_sentences = extract_long_sentences(generated_text)
    ref_sentences = extract_long_sentences(combined_ref_text)
    sentence_matches = list(gen_sentences.intersection(ref_sentences))
    
    # 4. Proper noun overlap
    gen_nouns = mock_extract_proper_nouns(generated_text)
    ref_nouns = mock_extract_proper_nouns(combined_ref_text)
    noun_overlap = list(gen_nouns.intersection(ref_nouns))
    
    # 5. Embedding similarity (reserved)
    embedding_similarity = 0.0 # Placeholder
    
    needs_rewrite = False
    reasons = []
    
    if ngram_overlap_ratio > DEFAULT_NGRAM_OVERLAP_THRESHOLD:
        needs_rewrite = True
        reasons.append(f"n-gram 相似度过高 ({ngram_overlap_ratio:.2f})")
        
    if consecutive_match:
        needs_rewrite = True
        reasons.append("存在超过 50 字的连续原文复制")
        
    if len(sentence_matches) > DEFAULT_LONG_SENTENCE_THRESHOLD:
        needs_rewrite = True
        reasons.append(f"长句重复过多 ({len(sentence_matches)} 句)")
        
    if len(noun_overlap) > DEFAULT_PROPER_NOUN_OVERLAP_THRESHOLD:
        needs_rewrite = True
        reasons.append(f"专有名词重合过多 ({len(noun_overlap)} 个)")
        
    rewrite_instruction = ""
    if needs_rewrite:
        rewrite_instruction = (
            "【防照抄重写指令】\n"
            "系统检测到当前生成的正文与参考书籍的原文相似度过高，可能存在照抄或雷同风险。\n"
            f"违规原因：{', '.join(reasons)}。\n"
            "请你彻底打碎这段文字的表述方式，使用本项目独立的世界观、角色设定和行文习惯，对相关情节进行重新叙述。严禁直接使用原参考书中的连续短语或特殊名词！"
        )
        
    return {
        "needs_rewrite": needs_rewrite,
        "max_ngram_overlap_ratio": ngram_overlap_ratio,
        "long_sentence_match_count": len(sentence_matches),
        "proper_noun_overlap_count": len(noun_overlap),
        "embedding_similarity": embedding_similarity,
        "rewrite_instruction": rewrite_instruction,
        "reasons": reasons
    }

def save_similarity_report(filepath: str, report: Dict[str, Any], chapter_number: int):
    # 报告不包含原文内容（只记录相似度数值和命中位置）
    safe_report = {
        "chapter_number": chapter_number,
        "needs_rewrite": report["needs_rewrite"],
        "max_ngram_overlap_ratio": report["max_ngram_overlap_ratio"],
        "long_sentence_match_count": report["long_sentence_match_count"],
        "proper_noun_overlap_count": report["proper_noun_overlap_count"],
        "embedding_similarity": report["embedding_similarity"],
        "reasons": report["reasons"],
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    report_file = os.path.join(filepath, f"chapter_{chapter_number}_similarity_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(safe_report, f, ensure_ascii=False, indent=2)
