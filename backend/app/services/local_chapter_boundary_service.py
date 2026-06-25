import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Pattern to match chapters
CHAPTER_PATTERNS = [
    re.compile(r'^\s*第[零一二三四五六七八九十百千万\d]+[章回节]\s*(.*)'),
    re.compile(r'^\s*Chapter\s*\d+\s*(.*)', re.IGNORECASE),
    re.compile(r'^\s*(楔子|序章|番外|尾声|引子)\s*(.*)')
]

# Pattern to match volumes
VOLUME_PATTERNS = [
    re.compile(r'^\s*第[零一二三四五六七八九十百千万\d]+[卷部]\s+(.*)'),
    re.compile(r'^\s*卷[零一二三四五六七八九十百千万\d]+\s+(.*)'),
    re.compile(r'^\s*Volume\s*\d+\s*(.*)', re.IGNORECASE)
]

def is_match(line: str, patterns: List[re.Pattern]) -> bool:
    for p in patterns:
        if p.match(line):
            return True
    return False

def parse_book_file(file_path: str, encoding: str) -> Dict[str, Any]:
    """
    流式读取小说文件，识别卷和章节的边界，记录字节级偏移量（offset）。
    避免将大文件一次性加载到内存中。
    """
    volumes = []
    chapters = []
    
    current_volume = None
    current_chapter = None
    
    # 辅助变量
    byte_offset = 0
    total_words = 0
    
    # 防止编码错误导致中断
    errors_handling = 'replace'
    
    try:
        with open(file_path, 'rb') as f:
            for raw_line in f:
                line_length = len(raw_line)
                try:
                    line = raw_line.decode(encoding, errors=errors_handling)
                except Exception:
                    # 如果还是解码失败，就忽略该行内容，但 offset 必须继续累加
                    line = ""
                
                stripped_line = line.strip()
                
                # Check for Volume
                if stripped_line and is_match(line, VOLUME_PATTERNS) and len(stripped_line) < 100:
                    # Close previous volume if any (just conceptually, volumes just group chapters)
                    # Create a new volume record
                    current_volume = {
                        "title": stripped_line,
                        "chapters": []
                    }
                    volumes.append(current_volume)
                    
                # Check for Chapter
                elif stripped_line and is_match(line, CHAPTER_PATTERNS) and len(stripped_line) < 100:
                    # Close previous chapter
                    if current_chapter:
                        current_chapter["end_offset"] = byte_offset
                    
                    # Create new chapter
                    current_chapter = {
                        "title": stripped_line,
                        "start_offset": byte_offset,
                        "end_offset": -1, # To be determined
                        "word_count": 0,
                        "volume_index": len(volumes) - 1 if volumes else -1
                    }
                    chapters.append(current_chapter)
                    if current_volume is not None:
                        current_volume["chapters"].append(len(chapters) - 1)
                else:
                    # Add to current chapter word count
                    if current_chapter:
                        # calculate pure text length roughly (excluding whitespace)
                        words = len(re.sub(r'\s+', '', line))
                        current_chapter["word_count"] += words
                        total_words += words
                
                byte_offset += line_length
                
        # Close the final chapter
        if current_chapter:
            current_chapter["end_offset"] = byte_offset

    except Exception as e:
        logger.error(f"Error parsing book file {file_path}: {e}")
        return {
            "volumes": [],
            "chapters": [],
            "total_words": 0,
            "confidence": 0.0,
            "error": str(e)
        }
        
    # Calculate parsing confidence
    confidence = 1.0
    num_chapters = len(chapters)
    
    if num_chapters == 0:
        confidence = 0.0
    else:
        avg_words = total_words / num_chapters
        if avg_words > 50000:
            # Chapter average is way too large, maybe parsing failed
            confidence -= 0.5
        elif avg_words < 500:
            # Chapter average is too small
            confidence -= 0.3
            
        # Check for max chapter size
        max_words = max([ch["word_count"] for ch in chapters]) if chapters else 0
        if max_words > 100000:
            confidence -= 0.4
            
    confidence = max(0.0, min(1.0, confidence))

    return {
        "volumes": volumes,
        "chapters": chapters,
        "total_words": total_words,
        "confidence": confidence,
        "error": None
    }
