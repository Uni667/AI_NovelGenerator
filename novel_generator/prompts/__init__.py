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
)

from .state_update import (
    summary_prompt,
    update_character_state_prompt,
    update_plot_arcs_prompt,
    Character_Import_Prompt,
)

import os
import json

def get_prompt_template(project_id: str, prompt_key: str) -> str:
    """
    Retrieves the prompt template. First checks project config for custom overrides.
    If none found, returns the default python template.
    """
    # Load defaults from this module dynamically
    default_prompt = globals().get(prompt_key, "")
    
    if not project_id:
        return default_prompt
        
    # Read project config
    try:
        from backend.app.services.project_service import get_project_config
        config = get_project_config(project_id)
        if config and "custom_prompts" in config:
            return config["custom_prompts"].get(prompt_key, default_prompt)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error loading custom prompt: {e}")
        pass
        
    return default_prompt


