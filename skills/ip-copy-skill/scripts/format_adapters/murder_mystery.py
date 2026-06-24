from .base import FormatAdapter, FormatAdapterSpec


class MurderMysteryAdapter(FormatAdapter):
    format_name = "murder_mystery"

    def spec(self) -> FormatAdapterSpec:
        return FormatAdapterSpec(
            format_name=self.format_name,
            structure_levels=["project", "phase", "round", "scene", "clue"],
            default_aspect_ratio="tabletop_packet",
            default_episode_duration_sec=14400,
            required_scene_card_fields=["visual", "voiceover", "duration_sec", "asset_goal"],
            required_script_scene_fields=["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
            rhythm_rules=[
                "opening_phase_locks_public_case_premise_character_objectives_and_table_rules",
                "each_round_reveals_new_clues_without_collapsing_the_truth_chain_too_early",
                "character_pov_packets_must_separate_public_facts_private_memory_and_hidden_objective",
                "clue_distribution_must_be_fair_traceable_and_not_depend_on_out_of_band_information",
                "discussion_phase_should_create_conflicting_interpretations_not_random_confusion",
                "revelation_phase_must_pay_off_motive_method_timeline_and_alibi_logic",
            ],
            quality_checks=[
                "truth_chain_complete",
                "clue_distribution_fair",
                "character_pov_separation_clear",
                "motive_method_timeline_alibi_consistent",
                "red_herrings_labeled_and_reversible",
                "round_progression_not_spoiling_final_reveal",
                "causality_not_broken",
                "no_unapproved_new_plot_facts",
                "image_handoff_fields_present",
                "host_script_ready",
            ],
            handoff_requirements={
                "image": ["character_refs", "location_refs", "prop_clue_refs", "relationship_board_refs", "default_aspect_ratio=tabletop_packet"],
                "video": ["intro_scene_storyboard", "clue_reveal_moments", "relationship_board_visuals", "host_explainer_beats"],
                "music": ["case_theme", "phase_mood_cues", "reveal_sting_cues"],
                "copy": ["truth_chain", "character_pov_packets", "clue_distribution", "round_structure", "host_script", "solution_logic"],
            },
        )