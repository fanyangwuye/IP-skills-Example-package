# Action Shot Patterns / 动作镜头模式库

Use this reference when the action scene needs richer shot design, varied movement grammar, or genre-specific choreography patterns.

## Core Rule

One 15-second node should have one primary action idea. Do not cram five fights, three camera moves, and two emotional reversals into one node. Seedance will turn that into noodle soup.

## Shot Size Patterns

### 1. Establishing Action Wide Shot

Use when: opening a fight, showing geography, showing multiple fighters.

Pattern:

```text
wide shot → show spatial relation → first movement begins → camera tracks the dominant direction
```

Good for:

- rooftop chase
- courtyard duel
- alley ambush
- battlefield standoff

Prompt cues:

```text
wide shot, clear spatial geography, both characters visible, camera tracks from left to right, ground and obstacles visible
```

Avoid:

```text
random close-up before audience knows where people stand
```

### 2. Medium Tracking Combat Shot

Use when: showing body mechanics and weapon arcs.

Pattern:

```text
medium shot → body turn → weapon/limb trajectory → impact/reaction → recover stance
```

Prompt cues:

```text
medium tracking shot, full upper body visible, weapon arc clearly visible, footwork visible, no jump cut
```

### 3. Low-Angle Power Strike

Use when: a character gains momentum or pressure.

Pattern:

```text
low angle → forward step → strike crosses frame → dust/rain/cloth reacts → opponent retreats
```

Prompt cues:

```text
low-angle tracking shot, powerful forward step, robe/coat reacts to movement, impact shown by opponent recoil, grounded physics
```

### 4. Close-Up Detail Beat

Use when: weapon grip, eye focus, wound, breath, hand tension, prop trigger.

Pattern:

```text
close-up → micro movement → cut/transition back to action pose
```

Prompt cues:

```text
close-up of hand tightening on sword hilt, rain drops on knuckles, shallow depth of field, then return to medium shot
```

Do not use close-up for the whole 15 seconds unless the scene is a tension beat, not an action beat.

### 5. Whip-Pan Impact Transition

Use when: fast direction change, surprise attack, chase turn.

Pattern:

```text
subject exits frame → whip pan follows motion → new position revealed → action lands
```

Prompt cues:

```text
fast whip pan following the sword arc, motion blur controlled, ends on stable stance
```

## Genre Patterns

### Wuxia / 武侠

Core visual logic:

- elegant but physically traceable movement
- robe / sleeve / hair / dust / leaves as motion evidence
- landings must have posture and ground reaction
- sword arcs should be visible and continuous

Prompt ingredients:

```text
robe sleeves flowing with momentum, sword arc cutting through rain, foot lands on wet stone with splash, body recovers into balanced stance
```

Avoid:

```text
floating forever, teleporting behind enemy, ten sword moves in one sentence
```

### Modern Fight / 现代格斗

Core visual logic:

- footwork, guard, weight shift, impact, recoil
- environment as obstacle: table, wall, car, stairs, doorframe
- camera can be handheld but not chaotic soup

Prompt ingredients:

```text
tight footwork, shoulder rotation, punch impact shown by head recoil, back hits concrete wall, handheld medium shot but faces remain clear
```

Avoid:

```text
real tactical instruction, weapon handling tutorial, detailed harm method
```

### Chase / 追逐

Core visual logic:

- geography first
- each node ends with a clear next starting position
- obstacles should escalate, not randomly appear

Prompt ingredients:

```text
narrow alley, wet ground, character vaults over fallen bicycle, camera follows from behind, ends at locked iron gate
```

### Sword Duel / 刀剑对决

Core visual logic:

- blade position is continuity anchor
- show block/parry/riposte as transformations
- weapon contact should create sparks/water/cloth response if appropriate

Prompt ingredients:

```text
right-hand sword held low, opponent cuts from upper left, protagonist raises blade to parry, sparks at contact, ends with both blades locked at chest height
```

## Camera Movement Density

Use at most 1-2 major camera movements per 15-second node.

Good:

```text
low-angle tracking shot follows her forward step, then settles into medium shot as she lands
```

Bad:

```text
drone shot, dolly zoom, whip pan, crane down, handheld shake, bullet time, 360 orbit all in 15 seconds
```

## Action Verb Bank

Prefer concrete verbs:

```text
sidestep, pivot, duck, parry, sweep, vault, recoil, stagger, recover, brace, slide, plant foot, twist waist, raise guard, lower blade, lock elbows, roll shoulder
```

Avoid empty verbs alone:

```text
fight fiercely, battle intensely, unleash power, perform amazing martial arts
```
