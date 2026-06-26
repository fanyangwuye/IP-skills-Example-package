# 视频风格预设库 (Video Style Presets)

本目录存放视频生成管线的风格预设 JSON 文件。每个预设定义了特定视觉风格的完整参数集，管线在构建 prompt 时自动加载并注入。

## 目录结构

```
video_style_presets/
├── README.md                    ← 本文件
├── wong_kar_wai.json            ← 王家卫风格
├── food_documentary.json        ← 舌尖上的美味（美食纪录片）
├── one_take_cinematic.json      ← 一镜到底（电影级）
├── industrial_product_commercial.json  ← 工业产品商业宣传片
├── miniature_world.json         ← 微缩世界
├── new_product_tvc.json         ← 新品视觉TVC广告宣传
├── miyazaki_animation.json      ← 宫崎骏动画大师
├── shinkai_style.json           ← 新海诚风格
├── nolan_director_style.json     ← 诺兰导演风格
├── drama_short_sound.json       ← 剧情短片音色
├── ancient_sweet_short_drama.json← 古风甜宠短剧
├── story_driven_storyboard.json ← 故事驱动型故事板
├── art_film_mood.json           ← 文艺片情绪氛围
├── dimension_breaking_interactive.json ← 次元破壁互动玩法
├── immersive_interactive_girlfriend.json ← 沉浸式互动女友
├── world_cup_traversal.json     ← 穿越世界杯
├── one_take_ad.json             ← 一镜到底广告短片
├── immersive_handheld_tracking.json ← 沉浸式手持跟拍
├── million_dollar_one_take.json ← 百万运镜一镜到底
├── first_person_pov.json        ← 第一人称POV
├── video_analysis_remaking.json  ← 视频拉片复刻
└── source/                      ← 原始文本参考（人工可读的完整风格说明）
    ├── one-take/
    ├── director-style/
    ├── genre/
    ├── commercial/
    ├── interactive/
    ├── technique/
    └── _index.md
```

## JSON Schema 字段说明

### 基础字段（与 ip-image-skill 图片预设兼容）

| 字段 | 类型 | 说明 |
|------|------|------|
| `style_direction` | string | 风格方向总述 |
| `primary_palette` | string | 主色调描述 |
| `positive_prompt_fragments` | string[] | 正向质感提示词片段 |
| `realism_constraints` | string[] | 真实感约束 |
| `forbidden_elements` | string[] | 禁止出现的元素 |
| `negative_prompt_fragments` | string[] | 负向提示词 |

### 视频专用字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `camera_language` | object | 运镜语言配置 |
| `camera_language.movement_preference` | string | 运镜偏好（手持/稳定器/推拉等） |
| `camera_language.framing_preference` | string | 构图偏好（框架式/三分法/对称等） |
| `camera_language.lens_bias` | string | 镜头焦距偏好 |
| `camera_language.shot_type_distribution` | object | 景别分布比例 {close_up, medium, wide} |
| `rhythm` | object | 节奏配置 |
| `rhythm.cuts_per_15s` | integer | 每15秒切镜数 |
| `rhythm.avg_shot_duration_sec` | number | 平均单镜时长（秒） |
| `rhythm.pacing_description` | string | 节奏描述 |
| `rhythm.transition_style` | string | 转场风格 |
| `prompt_rules` | object | 提示词构建规则 |
| `prompt_rules.language` | string | 提示词语言 (zh/en) |
| `prompt_rules.structure_template` | string | 提示词结构模板 |
| `prompt_rules.mandatory_elements` | string[] | 必须包含的元素 |
| `prompt_rules.forbidden_phrases` | string[] | 禁止出现的短语 |
| `pipeline_config` | object | 管线配置 |
| `pipeline_config.preferred_model` | string | 首选模型 (seedance_2 / seedance_2_fast) |
| `pipeline_config.resolution` | string | 分辨率 (720p / 1080p) |
| `pipeline_config.clip_duration_sec` | integer | 单片段时长（秒） |
| `pipeline_config.handoff_mode` | string | 片段交接模式 (last_frame / sequential / last_frame_strict) |
| `audio_direction` | object | 音频方向 |
| `audio_direction.bgm_style` | string | 背景音乐风格 |
| `audio_direction.voice_character` | string | 音色/语速特征 |
| `audio_direction.ambient_sound` | string | 环境音效描述 |

### 可选关联字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `linked_image_preset` | string | 关联的 ip-image-skill 预设名称，加载时自动合并 |

## 调用方式

在 task JSON 中指定 `video_style_preset` 字段：

```json
{
  "mode": "build_video_handoff",
  "title": "黄泉饭店",
  "video_style_preset": "wong_kar_wai",
  ...
}
```

加载优先级（高 → 低）：
1. `style_card_path`（项目级自定义覆盖）
2. `video_style_preset`（视频风格预设）
3. `style_preset`（图片风格预设，作为基础）

## 当前预设清单（共21个）

| 预设名 | 显示名 | 分类 | 状态 |
|--------|--------|------|------|
| `wong_kar_wai` | 王家卫风格 | director-style | ✅ 已实现 |
| `food_documentary` | 舌尖上的美味 | genre | ✅ 已实现 |
| `one_take_cinematic` | 一镜到底（电影级） | one-take | ✅ 已实现 |
| `shinkai_style` | 新海诚风格 | director-style | ✅ 已实现 |
| `nolan_director_style` | 诺兰导演风格 | director-style | ✅ 已实现 |
| `miyazaki_animation` | 宫崎骏动画大师 | director-style | ✅ 已实现 |
| `ancient_sweet_short_drama` | 古风甜宠短剧 | genre | ✅ 已实现 |
| `art_film_mood` | 文艺片情绪氛围 | genre | ✅ 已实现 |
| `drama_short_sound` | 剧情短片音色 | genre | ✅ 已实现 |
| `story_driven_storyboard` | 故事驱动型故事板 | genre | ✅ 已实现 |
| `one_take_ad` | 一镜到底广告短片 | one-take | ✅ 已实现 |
| `million_dollar_one_take` | 百万运镜一镜到底 | one-take | ✅ 已实现 |
| `immersive_handheld_tracking` | 沉浸式手持跟拍 | one-take | ✅ 已实现 |
| `industrial_product_commercial` | 工业产品商业宣传片 | commercial | ✅ 已实现 |
| `new_product_tvc` | 新品视觉TVC广告宣传 | commercial | ✅ 已实现 |
| `miniature_world` | 微缩世界 | commercial | ✅ 已实现 |
| `dimension_breaking_interactive` | 次元破壁互动玩法 | interactive | ✅ 已实现 |
| `immersive_interactive_girlfriend` | 沉浸式互动女友 | interactive | ✅ 已实现 |
| `world_cup_traversal` | 穿越世界杯 | interactive | ✅ 已实现 |
| `first_person_pov` | 第一人称POV | technique | ✅ 已实现 |
| `video_analysis_remaking` | 视频拉片复刻 | technique | ✅ 已实现 |
