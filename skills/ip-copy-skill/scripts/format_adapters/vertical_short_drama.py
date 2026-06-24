from .base import FormatAdapter, FormatAdapterSpec


class VerticalShortDramaAdapter(FormatAdapter):
    format_name = "vertical_short_drama"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "episode", "scene", "beat", "shot"],
            default_aspect_ratio="9:16",
            default_episode_duration_sec=90,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "first_3_seconds_state_conflict_or_reversal",
                "every_10_to_15_seconds_add_new_pressure_or_information",
                "each_scene_card_has_one_main_action_and_one_emotional_turn",
                "dialogue_short_enough_for_vertical_short_drama_delivery",
                "end_each_episode_or_test_clip_with_unresolved_question_or_action_handoff",
            ],
            quality_checks=[
                "opening_hook_visible",
                "character_identity_preserved",
                "causality_not_broken",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "video_storyboard_ready_action_beats",
            ],
            handoff_requirements={
                "image": ["character_refs", "scene_refs", "asset_goal", "default_aspect_ratio=9:16"],
                "video": ["storyboard_ready_visual", "duration_sec", "main_action", "emotional_turn"],
                "music": ["music_cue", "emotion_curve"],
            },
        )