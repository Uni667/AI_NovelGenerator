# -*- coding: utf-8 -*-
from .prompt_builder import build_chapter_prompt
from .quality_checker import analyze_opening_hook, analyze_ending_hook, analyze_mid_section_quality, analyze_dialogue_voice
from .revision import rewrite_chapter_by_quality_feedback, revise_chapter_voice
