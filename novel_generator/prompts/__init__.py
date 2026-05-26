from .architecture import (
    core_seed_prompt,
    character_dynamics_prompt,
    world_building_prompt,
    plot_architecture_prompt,
    initial_global_summary_prompt,
    initial_plot_arcs_prompt,
    create_character_state_prompt,
    architecture_section_polish_prompt,
)

from .blueprint import (
    chapter_blueprint_prompt,
    chunked_chapter_blueprint_prompt,
    blueprint_polish_prompt,
)

from .chapter import (
    summarize_recent_chapters_prompt,
    first_chapter_draft_prompt,
    next_chapter_draft_prompt,
    platform_chapter_guidance_prompt,
)

from .knowledge import (
    knowledge_search_prompt,
    knowledge_filter_prompt,
)

from .revision import (
    de_ai_style_revision_prompt,
    chapter_quality_rewrite_prompt,
    mid_section_quality_prompt,
    dialogue_voice_check_prompt,
    enrich_prompt,
    interactive_rewrite_prompt,
    chapter_comprehensive_quality_check_prompt,
)

from .state_update import (
    summary_prompt,
    compress_global_summary_prompt,
    update_character_state_prompt,
    update_plot_arcs_prompt,
    Character_Import_Prompt,
    graph_extraction_prompt,
    single_chapter_summary_prompt,
)

from .brainstorming import (
    reader_agent_prompt,
    villain_agent_prompt,
    director_agent_prompt,
)

import os
import json

# Registry for dynamic lookup
prompt_registry = {
    "core_seed_prompt": core_seed_prompt,
    "character_dynamics_prompt": character_dynamics_prompt,
    "world_building_prompt": world_building_prompt,
    "plot_architecture_prompt": plot_architecture_prompt,
    "initial_global_summary_prompt": initial_global_summary_prompt,
    "initial_plot_arcs_prompt": initial_plot_arcs_prompt,
    "create_character_state_prompt": create_character_state_prompt,
    "architecture_section_polish_prompt": architecture_section_polish_prompt,

    "chapter_blueprint_prompt": chapter_blueprint_prompt,
    "chunked_chapter_blueprint_prompt": chunked_chapter_blueprint_prompt,
    "blueprint_polish_prompt": blueprint_polish_prompt,

    "summarize_recent_chapters_prompt": summarize_recent_chapters_prompt,
    "first_chapter_draft_prompt": first_chapter_draft_prompt,
    "next_chapter_draft_prompt": next_chapter_draft_prompt,
    "platform_chapter_guidance_prompt": platform_chapter_guidance_prompt,

    "knowledge_search_prompt": knowledge_search_prompt,
    "knowledge_filter_prompt": knowledge_filter_prompt,

    "de_ai_style_revision_prompt": de_ai_style_revision_prompt,
    "chapter_quality_rewrite_prompt": chapter_quality_rewrite_prompt,
    "mid_section_quality_prompt": mid_section_quality_prompt,
    "dialogue_voice_check_prompt": dialogue_voice_check_prompt,
    "enrich_prompt": enrich_prompt,
    "interactive_rewrite_prompt": interactive_rewrite_prompt,
    "chapter_comprehensive_quality_check_prompt": chapter_comprehensive_quality_check_prompt,

    "summary_prompt": summary_prompt,
    "compress_global_summary_prompt": compress_global_summary_prompt,
    "update_character_state_prompt": update_character_state_prompt,
    "update_plot_arcs_prompt": update_plot_arcs_prompt,
    "graph_extraction_prompt": graph_extraction_prompt,
    "single_chapter_summary_prompt": single_chapter_summary_prompt,
    
    "reader_agent_prompt": reader_agent_prompt,
    "villain_agent_prompt": villain_agent_prompt,
    "director_agent_prompt": director_agent_prompt,

    "Character_Import_Prompt": Character_Import_Prompt,
}

def get_prompt_template(project_id: str, prompt_key: str) -> str:
    """
    Retrieves the prompt template. First checks the project's custom_prompts.json for
    user overrides. If none found, returns the built-in default template string.
    """
    default_prompt = globals().get(prompt_key, "")

    if not project_id:
        return default_prompt

    try:
        from backend.app.database import get_db
        with get_db() as conn:
            row = conn.execute("SELECT filepath FROM project WHERE id=?", (project_id,)).fetchone()
        if row:
            custom_file = os.path.join(row["filepath"], "custom_prompts.json")
            if os.path.exists(custom_file):
                with open(custom_file, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                if prompt_key in custom and custom[prompt_key].strip():
                    return custom[prompt_key]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[Prompt] Failed to load custom prompt '{prompt_key}': {e}")

    return default_prompt


