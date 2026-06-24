from .base import FormatAdapter, FormatAdapterSpec


class FeatureFilmAdapter(FormatAdapter):
    format_name = "feature_film"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "act", "sequence", "scene", "beat"],
            default_aspect_ratio="2.39:1",
            default_episode_duration_sec=6600,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "act_one_establishes_theme_wound_goal_world_and_inciting_incident",
                "act_two_escalates_reversals_cost_relationship_pressure_and_midpoint_shift",
                "act_three_resolves_core_choice_theme_payoff_and_visual_climax",
                "each_sequence_has_setup_escalation_turn_and_handoff",
                "dialogue_should_subtext_character_choice_not_explain_plot_mechanically",
                "visual_storytelling_preferred_over_voiceover_exposition",
            ],
            quality_checks=[
                "three_act_structure_visible",
                "theme_question_and_character_wound_identified",
                "sequence_turns_clear",
                "causality_not_broken",
                "character_arc_trackable",
                "visual_payoff_setups_present",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "video_storyboard_ready_key_sequences",
            ],
            handoff_requirements={
                "image": ["character_refs", "world_refs", "key_location_refs", "visual_motif_refs", "default_aspect_ratio=2.39:1"],
                "video": ["key_sequence_storyboard", "turning_point_beats", "visual_motif_continuity", "spatial_continuity"],
                "music": ["theme_motif", "act_emotion_curve", "sequence_music_cues"],
                "copy": ["theme_question", "character_arc", "act_breaks", "sequence_turns", "subtext_dialogue_notes"],
            },
        )
