from .base import FormatAdapter, FormatAdapterSpec


class LongSeriesAdapter(FormatAdapter):
    format_name = "long_series"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "act", "episode", "scene", "beat"],
            default_aspect_ratio="16:9",
            default_episode_duration_sec=2700,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "episode_opens_with_clear_inciting_pressure_or_cold_open_question",
                "each_act_break_raises_stakes_reverses_information_or_changes_relationship_power",
                "a_story_and_b_story_must_progress_without_competing_for_the_same_function",
                "midpoint_changes_the_episode_problem_or_reveals_hidden_cost",
                "scene_dialogue_should_reveal_character_strategy_and_subtext_not_only_exposition",
                "episode_end_resolves_local_engine_while_preserving_season_arc_momentum",
            ],
            quality_checks=[
                "episode_engine_clear",
                "act_structure_visible",
                "a_story_b_story_tracks_clear",
                "character_arc_progression_visible",
                "act_break_hooks_present",
                "season_arc_not_contradicted",
                "causality_not_broken",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "video_key_scene_storyboard_ready",
            ],
            handoff_requirements={
                "image": ["character_refs", "world_refs", "recurring_location_refs", "episode_motif_refs", "default_aspect_ratio=16:9"],
                "video": ["key_scene_storyboard", "act_break_beats", "a_story_b_story_continuity", "spatial_continuity"],
                "music": ["season_theme", "episode_emotion_curve", "act_transition_cues"],
                "copy": ["episode_logline", "act_breaks", "a_story_b_story_tracks", "character_arc", "subplot_continuity_notes"],
            },
        )