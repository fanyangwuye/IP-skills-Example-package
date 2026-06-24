from .base import FormatAdapter, FormatAdapterSpec


class OverseasShortDramaAdapter(FormatAdapter):
    format_name = "overseas_short_drama"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "season", "episode", "scene", "beat"],
            default_aspect_ratio="9:16",
            default_episode_duration_sec=360,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "first_5_seconds_state_relationship_conflict_or_high_concept_hook",
                "every_20_to_30_seconds_add_new_emotional_pressure_or_plot_information",
                "scene_context_must_be_culturally_clear_without_long_exposition",
                "dialogue_must_be_translation_ready_and_natural_for_overseas_short_drama",
                "episode_end_should_hold_a_choice_reversal_secret_or_relationship_pressure",
            ],
            quality_checks=[
                "opening_hook_visible",
                "relationship_and_status_clear",
                "cultural_context_clear",
                "dialogue_translation_ready",
                "causality_not_broken",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "video_storyboard_ready_action_beats",
            ],
            handoff_requirements={
                "image": ["character_refs", "scene_refs", "asset_goal", "default_aspect_ratio=9:16", "culture_safe_visual_context"],
                "video": ["storyboard_ready_visual", "duration_sec", "main_action", "emotional_turn", "relationship_blocking"],
                "music": ["music_cue", "emotion_curve", "localized_mood_reference"],
                "copy": ["translation_ready_dialogue", "relationship_status_terms", "culture_safe_surface_wording"],
            },
        )
