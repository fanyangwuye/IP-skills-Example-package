# Style Presets

Use `style_preset` in a task JSON when the user has not provided a custom style card.

Current presets:

- `realistic_short_drama`: actor-like realism, lower AI gloss, modern short-drama look
- `dark_underworld_film`: realistic dark fantasy for underworld or weird-revival IP
- `character_design_board`: readable production asset sheet style
- `cinematic_concept_art`: polished cinematic concept art

Priority order:

1. `style_preset` loads one built-in baseline.
2. `style_card_path` can add project-specific details on top.
3. Task fields describe the current character, scene, asset target, and interaction state.

When `style_preset` is set, the skill does not auto-load the `ip_id` default style card. This prevents old project cards from accidentally polluting a new style test. Pass `style_card_path` explicitly when you want to merge an IP card with a preset.

For user-provided visual references, pass local files with `style_reference_paths` or public URLs with `reference_image_urls`.
