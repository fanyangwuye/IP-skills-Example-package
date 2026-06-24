from .base import FormatAdapter, FormatAdapterSpec


class InteractiveFilmGameAdapter(FormatAdapter):
    format_name = "interactive_film_game"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "node", "choice", "branch", "consequence"],
            default_aspect_ratio="16:9",
            default_episode_duration_sec=3600,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "root_node_establishes_player_goal_world_rule_and_immediate_choice_pressure",
                "each_choice_must_have_clear_visible_stakes_and_distinct_consequences",
                "branches_must_track_state_changes_inventory_relationships_and_hidden_flags",
                "convergence_points_must_preserve_choice_memory_without_erasing_player_agency",
                "failure_or_dead_end_nodes_must_be_earned_by_prior_choice_logic_not_random_punishment",
                "endings_must_pay_off_core_theme_player_strategy_and_branch_history",
            ],
            quality_checks=[
                "branch_tree_integrity_clear",
                "choice_consequence_mapping_complete",
                "state_flags_trackable",
                "convergence_points_defined",
                "multiple_endings_supported",
                "player_agency_not_fake",
                "causality_not_broken",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "video_node_storyboard_ready",
            ],
            handoff_requirements={
                "image": ["character_refs", "location_refs", "choice_ui_refs", "key_item_refs", "default_aspect_ratio=16:9"],
                "video": ["node_storyboards", "choice_moment_beats", "branch_transition_beats", "consequence_visual_states"],
                "music": ["state_based_music_cues", "choice_tension_cues", "ending_theme_variants"],
                "copy": ["node_graph", "choice_consequence_map", "state_flags", "convergence_points", "ending_conditions", "replay_notes"],
            },
        )