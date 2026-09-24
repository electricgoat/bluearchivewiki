# Skill mechanics: reverse-engineering notes

These notes cover what we know so far about how Blue Archive stores skill mechanics. They back the EXPERIMENTAL skill description generator (`generate.py -skill_mechanics`), which writes English descriptions from the game's mechanics data instead of from translated JP text.

Code:
- `classes/SkillMechanics.py`: walks a skill's timeline and describes its structure (targets, conditions, tiers, triggers, forms, summons).
- `classes/SkillEffects.py`: words a single LogicEffect row as an English clause.
- `shared/skill_glossary.py`: English names for enum values, and number formatting.
- `shared/battle_schema.py` and `shared/battle_schema.json`: resolve integer enum values to the game's names.
- `translation/SkillEffects.json`: names the game does not localize: character-unique effects (by `TemplateId`) and character forms (by `FormId`). A base for translation work.

Tools (in `scripts/`, which is gitignored, so add them with `git add -f`):
- `build_battle_schema.py <schemata dir>`: regenerates `shared/battle_schema.json` from a game code dump.
- `skill_mechanics_check.py`: compares generated descriptions against JP descriptions and writes `out/skill_mechanics_check.txt`. `-raid` checks raid bosses instead (§8.2). JP values match generated ones within the precision JP shows, closest value first, so a whole number does not consume a decimal another value needs.
- `skill_effect_names.py`: mines names of unique effects and forms from skill descriptions into `translation/SkillEffects.json`. It only fills empty names and never changes a name already in the file.

Status as of 2026-09-18, across 1,477 skills of released students:
- For 93.1% of skills, every number in the JP description also appears in the generated text.
- 95.2% of all JP values are found.
- 2 skills still contain mechanics the generator does not explain, both with empty descriptions (see §11).

---

## 1. Data sources

| Data | Location in ba-data `jp/` | Notes |
|---|---|---|
| Skill timelines | `LevelSkill/<SkillDataKey>.json` | One file per skill group (not per level). File names are case-folded against `SkillDataKey`. A few referenced skills have no file (`CH0173ExtraPassive02`, `SM008101Passive02`, `SM032601ExtraPassive01`). |
| Effect values | `DB/LogicEffect_PC.json` | Current. A flat list of rows, one per `GroupId` + `Level`, with **integer enums**. Holds student effects and their summons' effects. |
| Enemy effects | `DB/LogicEffect_NPC.json` | Current. Bosses, raids, events and challenges. Shares no `GroupId`s with the PC file. Useful later for raid boss skills. |
| Old effect values | `DB/LogicEffectData.json`, `Battle/logiceffectdata.json` | **Stale, last updated April 2025.** They use string enums. `data.logiceffectdata` and the old, broken `Skill.effect_data` still read them. |
| Skill rows | `DB/SkillExcelTable.json` | Per level: `SkillDataKey`, `SkillCost`, `CoolTime` (ms, the cooldown shown in descriptions), `LocalizeSkillId`, tooltips. |
| Skill lists | `DB/CharacterSkillListExcelTable.json` | Keyed by (list id, `MinimumGradeCharacterWeapon`, `MinimumTierCharacterGear`, `FormIndex`). Forms are separate rows (see §8). Also lists `NormalSkillGroupId` and `HiddenPassiveSkillGroupId`. |
| Vehicle summons | `DB/TacticalSupportSystemExcelTable.json` | `Id` is the summon's character Id. `SummonedTime` is in ms. `SummonSkilllGroupId` is the EX skill that summons it. |
| Effect icons | `DB/LogicEffectCommonVisualExcelTable.json` | `StringID` = xxhash32 of a TemplateId (`shared.functions.hashkey`). An icon means players see the effect, which is how visible unique effects are told apart from internal flags. |
| Effect names | `DB/LocalizeSkillEffectExcelTable.json` | Only 11 entries, in Korean. Useless for naming unique effects. |
| Voice lines | `DB/VoiceLogicEffectExcelTable.json` | Voice lines played on an effect, keyed by hash. Not relevant. |
| Character tags | `CharacterExcelTable.Tags` | Obfuscated tag names (see §2). |

## 2. Enums

Both LevelSkill and LogicEffect data serialize many enums as bare ints, and some as strings. There is no enum dump in ba-data.

- **Source:** the private ba-cdn repo has `schemata/<version>/il2cpp.cs` (an Il2CppInspectorRedux dump) and `schema-db.fbs`. Battle enums and DAO classes are in the `MX.GameData.DAO.Battle`, `MX.Logic.Data`, `MX.Logic.Skills*` and `MX.Logic.BattleEntities` namespaces. Excel enums (`StatType`, `LogicEffectCategory`, `EndCondition` and so on) are in the fbs. **bluearchivewiki must not load these files.** `build_battle_schema.py` copies the needed parts into `shared/battle_schema.json`.
- **Resolving values:** the schema keeps each DAO class's enum-typed and class-typed fields, including inherited ones. The resolver follows declared field types down from each object's `$type`, so the same field name can map to different enums in different classes. For example, `StatChangeEffectDAO.RemoveCondition` is an `EndCondition`, while `DamageByHitEffectDAO.RemoveCondition` is a `DamageByHitRemoveCondition`. Ints an enum does not name, such as combined flags, stay ints.
- **Parsing the dump:** type names are namespace-qualified. Types outside any namespace, such as `AutoUseRuleDAO`, follow `MX` blocks and get attributed to the preceding namespace. Short names are unambiguous among the kept types.
- **Obfuscated tags:** `FlatData.Tag` names are obfuscated. A tag number maps to its name in base 52 over `AaBbCc…Zz` (0 → `A`, 1 → `a`, 67 → `ah`, 1000 → `jG`), which is what `CharacterExcelTable.Tags` contains. Meanings have to be inferred from who carries the tag:
  - Size tags are mostly on enemies: 288 = boss, 29 and 67 = medium-sized (67 is on every student too), 26/68/69 = large, 30 = extra-large. These were matched against JP descriptions.
  - Club and group tags: 324 = Ninjutsu Research Department, 412 = from Arius Squad (includes Azusa and Hiyori), 777 = Arius Squad.
- **Enums worth knowing:**
  - `ComparisonOperator`: Equal, NotEqual, Less, LessOrEqual, Greater, GreaterOrEqual.
  - `DiffOperatorType`: None, GreaterOrEqual, LessOrEqual, Equal, NotEqual.
  - `IncludeType`: None, Include, Exclude.
  - `ModifierCheckTarget`: Caster, Target, CasterAlly, CasterEnemy, All, CasterAllyExceptCaster.
  - `PassiveSkillTargetType`: None, UseTriggerSource, UseTriggerTarget, UseSkillEntityTargetingRule, UseTriggerTargetExceptSelf.
  - `CoverState`: None, NotCovered, Covered.

## 3. Units and formatting

- **Rates** are in 1/100ths of a percent (10000 = 100%). JP descriptions truncate to 1 decimal, and often to whole numbers (`19075` → "190%"). The two-decimal efficiency stats are the exception (`EnhanceMysticRate` "36.29%").
- **Durations:** LogicEffect durations are in ms. Timeline values (`Frame`, `HitFrames`, `StartDelay`, entity `Duration`, aura `Interval`, `AutoUseRule` `Interval`, periodic trigger parameters) are frames at **30 fps**.
- **Flat stat amounts** (`BaseAmount`) are shown raw, even for ratio stats. For example, weapon passives say "Critical Damage +2000" and "Attack Speed +1400". Only the elemental-efficiency and damage-ratio stats show `BaseAmount` as a percentage.
- **Stat change values** come from one of three places:
  - `TargetCoefficientAmount`: % of the target's own stat.
  - `BaseAmount`: flat.
  - `CasterCoefficientAmount` with `CasterStatType`: % of the caster's stat. Summons inherit stats this way ("19.4% of Hifumi's Attack").
- **General description:** the max level text, with values that differ from level 1 shown as `start~end`. When higher levels add clauses (Momiji's Sub skill widens normal attacks from level 7), values pair up in order by the words right before and after them. Tiered values merge only when both levels have the same number of tiers.

## 4. Timelines

**Root types:**
- `TimelineSkillActionDAO`: EX and Normal (Public) skills.
- `PassiveSkillDAO`: Passive, Sub (ExtraPassive), weapon and gear passives, hidden passives.
- `NormalAttackSkillActionDAO`: normal attacks, which use `ShotFrames` instead of `EntityTimeline`.
- `SelectExSkillActionDAO`: selectable EX skills (`SelectableExSkillList`).
- `BundledTimelineActionDAO`: rare.

**Structure:**
- **Entities:** `EntityTimeline[]` entries (`Tag`, `Frame`, `DamageDistributeRate`) each spawn an `Entity`. Entities nest through `SplashAreaEntityData`, `SkillEntitySpawnerData`, `AreaSpawnerData`, spawner `EntityTimeline`s and so on. **`MainEntityData` is a preview copy** of what the timeline spawns, so skip it when `EntityTimeline` or `ShotFrames` exist.
- **Abilities:** `Abilities`, `AreaAbilities` and `InitialAbilities` hold `LogicEffectGroupIds` and `Modifiers` (conditions).
- **Effect levels:** the effect row used is the skill level, clamped to the rows available. Hidden passives often have a single row.

**Hits:**
- Every hit deals `rate × DamageDistributeRate / 10000`. `HitFrames` on an area entity multiply the hits.
  - Except for sweeping areas: an area with `CollisionProperty.TransformType` (`RadiusIncrement`/`Decrement`, `FanClockWise`/`CounterClockWise`, `ObbCenterIncrement`) changes shape on each of its `TransformCount` hit frames: a growing ring, a turning fan, a rectangle moving forward. Each frame covers a different part, so an enemy is hit once per area. Counting every frame overstated Hina's EX 3× (1908% vs JP 636%) and Zunko's 5×.
- **JP descriptions are inconsistent.** Sometimes they give the total over all hits (Shiroko EX: 10 hits × 1000 = 400%). Sometimes each area or projectile deals the full rate (5 areas × 10000, JP gives the per-area value). Sometimes the rate is split across shards and JP gives one shard's share. The generator shows the total and the per-hit value.
- JP also often **adds up damage from several effect groups** hitting the same target (CH0056 EX: 533% over 12 hits + 532% = "1065%"). The generator shows the parts and adds "(X% in total)".

**Areas:**
- Area shapes come from the entity type: `CircleAreaEntityDAO`, `FanAreaEntityDAO`, `ObbAreaEntityDAO` (rectangular, JP says "straight line"), `DonutAreaEntityDAO` (ring or arch).
- An area with `Duration` > ~1s keeps effects that have no duration of their own "while in the area".
- An aura (`CircleAuraEntityDAO`) applies its abilities every `Interval` frames for `Duration` frames: "heal every 5s for 30s".

**Other structures:**
- **Bounces:** `TargetBounceProjectileEntityDAO` nests `BounceProjectileEntity` copies, one per bounce. Nested levels can apply different groups than the first hit (a 78% bounce after a 293% hit, or damage dropping 10% per bounce).
- **Spawners:** `SkillEntitySpawnerTimelineDAO` entries have `SpawnCondition` + `SpawnConditionParameter` + `SpawnConditionCheckTarget`, which act as conditions (template present, HP rate, rate, tags, form).
  - With `SpawnRule` `SpawnOnlyOne`, the entries are variants and the first one whose condition holds spawns. Sub skills use this to widen normal attacks. The Sub skill grants a level-specific marker (`Dummy_CH0126_NormalSkill_AreaCheck_Lv07` from level 7), and the normal attack has an area variant for that marker with a larger `Radius` than the variant used without it (150 vs 100).
  - JP gives the radius as a multiple of the standard splash radius of 100, which every other grenade and rocket launcher normal attack uses (Yuzu, Chise, Chise (Swimsuit), Momiji without the Sub skill).
  - The generator divides the radius of the normal attack area that requires the marker by 100: "Normal attacks: area radius ×1.5". Only normal attacks are checked, since other areas have no standard size.
  - Sena (Casual) and Shigure (CH0082, CH0122) already have a 150 area without their Sub skill. The Sub skill's area is 150 at levels 1–9 and 200 at level 10, which JP describes as ×1.5 and ×2 against the standard radius. This is treated as intentional: they start with the wider area.
- **Delays:** `StartDelay` on abilities is mostly animation timing. Only delays of about 5s or more are meaningful ("20 seconds later, increase Attack").

## 5. Targeting

- **Rule inheritance:** `EssentialCandidateRule` has `TargetSide`, `TargetingType`, `MaxTargetCount` (-1 = all) and `ApplyEntityType`. An entity with `TargetSide: None` inherits its parent's rule, and the root rule is the skill's.
- **Filters:** `OptionalCandidateRule` narrows targets by squad type (Striker/Special), role, school, weapon, bullet type, range, tags, personality, HP rate and cover. Most of these constraints are unset in practice.
- **Priority:** `TargetSortRule` (`IsValid`, `SortCriteria`, `OrderBy`, `SortStat`, `SortParameter`) sets which targets come first: lowest HP, highest Attack, farthest (Distance + Highest), or those with a given effect (`LogicEffectTemplateCount` + `SortParameter`).
- **Passives:** a passive without targeting of its own uses `SkillTargetType`. `UseSkillEntityTargetingRule` means the entity's rule, or self. `UseTriggerTarget`/`UseTriggerTargetExceptSelf` means the enemy hit or the ally healed. `UseTriggerSource` means whoever triggered it, which is self when the trigger source rule is `Self`.
- **Spawned units:** `InitialAbilities` of a spawned unit or object apply to that unit, such as a summon's stat inheritance or an obstacle's HP.
- **Excluding self:** `TargetSide` `Ally_Except_Self` becomes "other ally" ("one other ally" for a single target). JP is less precise: 36 single-target skills that exclude self say only 味方1人, the same as the 6 `Ally` ones that can pick self (Hanae's and Chinatsu's lowest HP ally). 自身を除 appears only with `Ally_Except_Self`, apart from 2 skills that move to a position first. So the data decides "other", not the JP text.
- **Same targets:** entities with their own targeting pick targets anew. Entities without it share the targets of the entity (or skill) above them, picked once. A clause about the same single target as the clause right before it joins it in one sentence, referring to the target as their/them: "Deal 221.7% of Attack as damage to one enemy and reduce their Evasion by 17.7%".
  - Clauses with conditions ("(against Heavy Armor targets)", "(50% chance)") or bouncing damage stay separate sentences and say "the target". A joined sentence would make the condition seem to apply to all of it, or make "them" ambiguous.
  - Target text carries a hidden mark of the entity that picked it (`Application.mention`). Merging tiers, joining stat changes and dropping duplicates ignore the mark, and `refer_back` resolves the marks once the clauses are final.
  - Plural targets ("allies in a circular area", "up to 3 enemies") are repeated as they are.

## 6. Effects (LogicEffect rows)

**General fields:**
- `$type` is the effect kind (`StatChangeEffectDAO`, `DamageEffectDAO`, …).
- `TemplateId` is the effect's identity for conditions and dispels.
- `Category` is Attack, Heal, Buff, Debuff, CrowdControl or Dummy.
- `ApplyRate` < 10000 is a chance.

**Common kinds and their key fields:**
- **Damage:** `BonusRateFirst` of `BonusSourceFirst`. `CriticalCheck` Always means guaranteed critical. `DefensePenetrationRate` < 10000 means it ignores `10000 − x` of Defense (7200 → "ignores 28%").
- **Heal and heal over time:** `BonusRate` of `BonusSource`, with `Duration`/`Period` for the over-time version.
- **StatChange:** see §3. `EndCondition` + `EndConditionArgumentFirst` means Duration (ms), UseExSkillCount, AmmoCount, AmmoHit or HitCount. `StackSameEffectApplied` + `StackSameEffectCount` sets stacking.
- **Shield:** `CasterCoefficientAmount` of `CasterStatType`. `ShieldId` Tactical is a tactical shield.
- **StatusAdd:** `TargetStatus` is a `HeroStatus` (Stunned, Taunted, ConcentratedTarget…).
- **DamageOverTime:** the kind is the last part of TemplateId (Burn, Chill, Poison, ElectricShock).
- **DamageByHit, HealByHit:** trigger on hits, and `RemoveCondition` TriggerCountOver limits the count.
- **Cost:** `AddSkillCost` gives `Amount` / 10000 cost. `SkillCostChange` uses `Coefficient` (%) or `BaseAmount`.
- **Penalties on oneself:** a stat change the skill's user puts on itself reads "own" when it hurts, since "reduce Attack" alone reads as aimed at enemies: "Reduce own Attack by 28.8%" (Tsukuyo), "Increase own Damage Taken by 9.6%" (Wakamo (Swimsuit)), "each stack will reduce own Defense by 5.3%" (Aru (New Year)'s Bad Deed). The game's `Category` is `Debuff` for these, and self buffs that lower something (`Buff_StatChange_DamagedRatio2Decrease_Self`, "reduce Damage Taken") stay as they are. Stats carried by a marker are categorized `Dummy`, so there the direction decides: lowering a stat, or raising a damage-taken stat.
- **Piercing shots:** a projectile with `Piercing` loses `ReduceDamageRatePerHit` of its damage per enemy it goes through, down to `MaxReducedDamageRate`: "(damage −45% for each enemy pierced, down to 10%)" (Hina (Dress), Haruna).
- **Ignoring Stability:** a damage effect with `ApplyStability` false always rolls maximum damage: "(always deals maximum damage)".
- **Other:** `ReloadAmmo`, `AddCurrentAmmo`, `Knockback` (direction Caster is self movement), `Dispel` (`DispelCount` debuffs), `DispelLogicEffectTemplate` (removes a template, `DispelCount` ≥ 10 effectively means all), `Immune`, `Accumulate`, `FormConversion` (§8).

**Internal kinds** only feed other mechanics and have nothing to describe on their own: `Dummy` (markers, §7), blackboard counters (`BlackBoardSet/Add/AlarmOnReach`, `WriteEntityToBlackboard`, `AddDamageToBlackBoard`), `ResetAutoUseRule`, `AccumulateDamageFromTargets`, `StackDamage`, `ImmediateKill`, `ApplyLogicDispelCount`, `ExSkillCardRedrawGauge` (except redraw stacks).

## 7. Character-unique effects (markers)

Unique mechanics are built from **markers**: effects whose TemplateId contains `Dummy` (mostly `Dummy` DAOs, sometimes `StatChange` with category Dummy). Other abilities check them through conditions, triggers or spawn conditions.

- **Visible or internal:** a marker counts as visible if it has a name in `translation/SkillEffects.json` or an icon (hash in LogicEffectCommonVisual). Otherwise it is visible only if it stacks, judged by its own effect group. Everything else is an internal flag.
  - **Templates are reused.** The same TemplateId can be used by unrelated effect groups. `Dummy_Effect` is used by about 100 groups across students, enemies, raids and events. Judging by TemplateId across all data made generic flags look visible, because some unrelated group stacks.
  - A template used by groups of 3 or more different owners (first part of the GroupId) counts as generic, so it is internal unless it has an icon.
  - A template only counts as stacking if every group using it stacks.
- **Names** are not in the game data. JP descriptions quote them in 「」, and existing EN translations usually quote them too. `skill_effect_names.py` pairs a skill's only unnamed visible marker with its only quoted name. It ignores quoted skill names and the names of other markers the skill involves. TemplateIds are poor names ("Dummy_Kokona_Original_ExtraPassive_CheckStatchange" is the Hanamaru Stamp).

**Patterns found:**
- **Stack counters:** a marker gained per event, with a trigger on reaching a count. Kokona's Hanamaru Stamp: the Sub skill fires on `AddLogicEffectTemplate` with `TryCount` 5, then dispels all stamps. Aru (New Year)'s "Bad deed" is a StatChange marker, so each stack reduces Defense.
- **Stack tiers:** one ability per stack count, gated by `CountLogicEffectTemplateModifier` (Aru EX: 1…6 stacks → 0.5…3 cost), then dispel all.
- **Level or stage markers:** `…_Lv0/1/2` (Aris's gauge, which gives ×1.5/×2) or `…Check01/02/03` (penlight stages). Abilities check each level.
- **Per-level gating across skills:** an EX applies `Dummy_CH0060_NormalAttack02Check_Lv{EX level}`, and the alternate normal attack has one ability per level checking it. Other normal attacks check the EX level directly through `SkillLevelModifier` on `ExSkill01`.
- **Unlock markers:** an EX or Sub skill applies a marker, and abilities in the **normal attack or hidden passives** only work while it is present. CH0067: the normal attack deals +9.4% for 30s. CH0124: an enhanced bullet every 3 attacks. The description of the skill that applies the marker should include them. Normal attacks and hidden passives have no descriptions of their own.
- **Once-per-battle flags:** an internal marker with no end, applied to self, where the skill's abilities require not having it (Ayane's Relief Supplies). It must never be required as present or removed elsewhere, or it is something else.
- **Use counters:** markers `UseCount01` → `02` → `03`, each applied while having the previous one, with abilities gated on the last. This means "every 3rd use" (CH0069's meteor).
- **Temporary tagging:** a short (1s) marker put on targets matching a condition (Heavy Armor allies), then counted with `CountListLogicEffectGroupIdModifier` (CH0306: +44 Cost Recovery per Heavy Armor ally).
- **Area marking:** a marker on enemies in an area, counted with `CountEntityListCombined` (CH0079: damage tiers by 0–4/5–9/10+ enemies).
- **Stage chains:** unnamed `…_Lv1/2/3` markers the skill applies to its user, each while having the previous one. Wakamo (Swimsuit): "60秒毎に…（全3段階）", every 60 seconds a new stage.
  - Stage 1's ability requires having none of the *later* stages, not "not having Lv1".
  - Having `Lv(n)` means this use advances to stage n+1. Having the last marker means staying at the last stage.
  - Other skills checking the markers read "at stage 3" / "before stage 3".
- **Hit counters:** a marker a skill puts on the enemies it hits and counts on the same targets. Hibiki's gear skill: every repeated hit on a target deals less damage ("with 0/1/2+ earlier hits on the same target"). CH0072: a 2s flag so each target is only debuffed once.
- **Consumed-stack flags:** an internal flag set while having a named marker that the same skill removes. Having the flag means a stack was consumed: CH0302 deals bonus damage "if a 水圧 stack was consumed".
- **Display mirrors:** unnamed markers that only show another marker's count as an icon. Saori (Dress)'s hidden counter `Dummy_CH0259_PublicCheck` ("Battle Sense") is shown by `Dummy_CH0259_BattleSense` (1-2 pips) and `Dummy_CH0259_BattleSense_Max`. A marker is a mirror when every application of it depends only on other markers the same skill applies, and nothing in the character's skills or effects checks or points to it (removing it doesn't count). Mirrors and their removals are not described (`mirror_templates`).
- **Form flags:** internal markers applied by a skill that converts form, which other skills check to know the form is active. Also markers put on targets by skills that only exist in an alternate form: CH0092's Sub skill adds damage to targets hit by Nonomi (Swimsuit)'s alternate normal attack. Flags a skill checks itself keep their plain wording.

### 7.1 Unnamed markers: breakdown

On 2026-09-17, 19 skills (14 marker templates) came out with "unique effect". They fell into three groups:

**1. Name in the text, but the miner couldn't attribute it:**

| Template | Skill(s) | Why the miner missed it | Resolution |
|---|---|---|---|
| `Dummy_CH0259_PublicCheck` | Saori (Dress) Normal skill and Sub skill | The Normal skill involves 3 markers. This is the 3-stack counter; `BattleSense`/`BattleSense_Max` only control display. The Sub skill references it through an effect group, which the miner didn't scan. | Miner scans timeline strings for GroupIds. Mined: 「戦場の感覚」 "Battle Sense". |
| `Dummy_CH0156_GearPublic_Dummy` | Iroha gear skill, and her vehicle's Normal skill | The description also quotes a skill name (「主砲照準、発射」). | Miner ignores quoted skill names. Mined: 「榴弾装填」 "High Explosive shell loaded". |
| `Dummy_CH0368_Check` | Kokoro EX1 and EX2 | The only quoted names are the two EX skill names. The marker is a 1-second check that the target has the other EX's buff. | Not a name: the flag only exists to decide whether the ExtraPassive applies. Left unnamed and hidden as a borrowed marker (§8, referenced skill slots). |
| `Dummy_CH0302_ExCheck` | Renge (Swimsuit) EX | Internal flag, not a name. | Consumed-stack role: "if a 水圧 stack was consumed". |

**2. Name in the text without quotes:**

| Template | Skill(s) | Text | Resolution |
|---|---|---|---|
| `Dummy_Effect_CH0204_CheckDummy` | Ui (Swimsuit) Sub skill and Normal skill | 手がかりを1個獲得 ("gain 1 Clue") | Manual entry "Clue" |
| `Dummy_Maki_PublicDummy` | Maki Sub skill | マーク状態の敵 ("marked enemies") | Manual entry "Mark" |
| `Dummy_CH0300_PublicCheck` | Kikyou (Swimsuit) Normal skill | ハンモック… (the hammock) | Manual entry "Hammock" |

**3. Internal mechanics described by role instead of a name:**

| Template | Skill(s) | What it is | Resolution |
|---|---|---|---|
| `Dummy_Wakamo_Swimsuit_Lv1..3`, `…GearPublic_Lv1..3` | Wakamo (Swimsuit), 4 skills | Stages (全3段階) | Stage chains: "29.6%/50.3%/71.1% at stage 1/2/3", "(at stage 3)" |
| `Dummy_Nonomi_Swimsuit_ExtraPassiveCheck` | Nonomi (Swimsuit) Sub skill | 100ms flag her alternate normal attack puts on targets | Form flags: "if the target was hit by an attack made in an alternate state" |
| `Dummy_Hibiki_GearPublicDummy` | Hibiki gear skill | Hit counter per target | Hit counters |
| `Dummy_Effect` | CH0072 and CH0115 gear skills | Generic template, used here as a short "already affected" flag | Generic templates are internal: flag hidden, duplicate clause dropped |

After these fixes, and hiding abilities that belong to other skills (§8), no skill shows "unique effect".

### 7.2 Internal markers named from their TemplateId

Recorded 2026-09-18, not acted on. 83 marker templates across 43 released students show up in generated text under a name made from their TemplateId ("Trigger", "Check01", "Public01 Coin") instead of a real name. They are plumbing: flags a character sets on itself so its own skills can find each other.

**Why they appear at all,** by how the name reaches the text:
- **Only inside a condition (55 of 76 character/name pairs):** conditions name any template through `effect_name`, whether the marker is notable or not: "while not having "Form Can Use Skill Duration"", "(if a "Use" was consumed)".
- **Described as an effect (5):** the marker is notable because it stacks or has a buff icon, so `describe_marker` gives it a clause of its own: Kasumi's "Count Skill", Natsu (Band)'s "Fillin", Haruna (Sportswear)'s "Hit Count", Momoi (Maid)'s "Check01", Umika's "Count".
- **Both, or inside a trigger header (16):** "When gaining "Departure Signal"" (Hikari), "(with 0/1 "Gauge")" (Arisu).

**What the markers do,** with the characters affected:
- **Trigger flags** — a skill sets a flag, a passive of the same character fires on gaining or losing it: Erika, Kei, Kikyou (Swimsuit), Niko, Yakumo, Subaru, Hikari ("Trigger"), Kurumi ("Form Release"), Koyuki (Pajama) ("Dispel").
- **Counters** — one stack per use, hit or heal, read by a tier condition: Kasumi ("Count Skill", "Count Skill02"), Konoka ("Heal Count"), Haruna (Sportswear) ("Hit Count", "Heal", "Upgrade"), Neru (School Uniform) ("Count", "Stack Count", "Count Check02/03"), Umika ("Count"), Kotori (Cheerleader) ("Public01 Apply Target Count"), Eimi (Battle) ("Form2 Ammo Count", "Use"), Seia and Yukari (Swimsuit) ("Use"), Kikyou ("Ally Check02").
- **State checks** — a flag standing for "the form is active" or "the skill was used": Hina (Dress) ("Form Can Use Skill Duration"), Momoi (Maid) and Ako (Dress) ("Check01", the latter misspelled "Hiddne Passive01 Check01" in the data), Konoka ("Cost Change"), Satsuki (Swimsuit) ("Passive01 UVBlock"), Mari (Sportswear) ("Mari02").
- **Target marks** — a mark put on a target so another ability can find it: Akane (School Uniform), Himari (Battle) ("Target"), Otogi ("Lock On"), Makoto (Swimsuit) ("Public01 Coin"), Mashiro ("Effect01").

**Ideas for later:**
- `proxy_flag` (§8.1) already replaces a condition on a self-flag with the condition that sets it. The same idea could cover trigger flags: "when gaining "Trigger"" is really "when the Normal skill is used".
- Counters could read as what they count, the way `unit_counter` does for allies: "(with 3 EX skill uses)" instead of "(with 3 "Count Skill" on self)".
- Some of these are real effects that only lack a translation ("Sweet Potato", "Departure Signal", "Fillin", "Lock On", "Firework"). Those belong in `translation/SkillEffects.json` instead, and the two groups need telling apart before hiding anything.
- Notability (`is_notable_marker`) decides only whether a marker gets its own clause; conditions name templates regardless, so hiding these needs a rule in `template_condition` too.

## 8. Forms, summons and other skills

- **Forms:** `FormConversionEffectDAO` (`FormIndex`, `NormalAttackIndex`, end condition). The form's skills are the skill list row `(list id, 0, 0, FormIndex)`. Compare it with row 0 to see what changes, usually the normal attack or the Normal skill. `DispelLogicEffectTemplate` of `Buff_FormConversion` ends the form early.
- **Form names:** the game calls all of these forms (`FormConversion`, `FormIndex`, `FormIndexCheckModifier`, `ReleaseFormConversion`), but has no localized names for them. JP descriptions name about a third of them, as a state (潜水状態, 戦術防御状態, 対戦状態), a stance (集中射撃体勢, 連射態勢, 指定射撃姿勢) or a mode (アビ・エシュフモード).
  - Generated text says "state": "enter the Submerged state", "exit the Concentrated Fire state", or "enter an alternate state" when a form has no name. A name that already says what it is keeps its own word ("the Duel state", "the Abi-Eshuh mode").
  - Names live in `translation/SkillEffects.json` under a `FormId` made of the character part of the effect group id and the form index (`CH0368_1`, `CH0355_01_1`, `Shun_1`). Exiting a form uses the form index of the skill list row the exiting skill belongs to.
  - `skill_effect_names.py` adds an entry for every form, empty if no name is found. JP names come from `…状態/体勢/態勢/姿勢/モード` followed by になり/に転換/に変更/を維持/解除, and EN names from "enter/switch to/assume/maintain/exit … state/stance/mode" in `translation/Skills.json`. A skill's text must name exactly one form.
  - Forms still unnamed are either not named in JP (Shun, Tsurugi, Momoi (Maid)) or named in other words: CH0182's turret 強化状態 "Enhanced state", CH0309 フルオート射撃 "full-auto fire", CH0355_01 「つぼみ」 "Flower Bud". Fill those in by hand.
- **Summoned units:** `CharacterEntityDAO.UniqueName` = `CharacterExcelTable.DevName` (e.g. `SM005801`). That character's costume gives its skill list (Normal, Public, Passive, ExtraPassive), and its effects are in LogicEffect_PC.
  - Summons have no localized names ("LocalizeError").
  - Vehicle durations come from TacticalSupportSystem. Other units use entity `Duration` in frames, which is approximate (32.33s vs JP "32s").
- **Placed objects:** `BattleItemEntityDAO` (mines, thrown items), `ObstacleEntityDAO`, `BarrierObstacleEntityDAO` (cover shields). Their `InitialAbilities` apply to the object, such as HP inherited from the caster.
- **Select EX:** the selectable skills appear as their own EX tooltips on the wiki.
- **Form EX skills:** a form row's `ExSkillGroupId` lists the EX skill used in that form, e.g. Kokoro `['EmptySkill', 'CH0368Ex02']` against row 0's `['CH0368Ex01', 'EmptySkill']`. It is described as `(EX skill changes to "<name>")` on the form switch. On `Buff_FormConversion` removal in a form's own EX skill, the name is row 0's EX skill. A form's normal attack that only deals 100% of Attack is not described, only what else it does.
- **Referenced skill slots:** `SkillAbilityDAO.IsReferenceSkillSlot` + `ReferenceSkillSlot` make an ability use another slot's skill level. There are 25 such abilities in released students. Two kinds:
  - A described skill (EX, Normal skill, Sub skill, Passive) hosts abilities of another described skill. Kokoro's EX timeline grants her ExtraPassive's EX damage buff and "Safety Certificate" marker. JP describes these in the other skill only. The generator skips them, and treats as borrowed the markers they grant plus flags set depending on those markers (repeated to a fixpoint). Abilities requiring a borrowed marker, removals of it, and "not having" conditions on it are dropped as well.
    The skill they belong to describes them instead, at its own level (`hosted_applications`): Kurumi's EX carries her Sub skill's Cost Recovery, and her Sub skill is where it shows.
  - Normal attacks and hidden passives referencing a described skill (Eimi (Battle)'s form normal attack scales with EX level, CH0355_01 passives use HiddenPassive levels). These are described as usual, by the skill that gives them.
- **Removing another skill's effects:** `DispelLogicEffectGroupId` targets groups named `<char>_<slot><n>_EffectXX`. When that skill isn't the current one, this becomes `remove the "<skill name>" effect`. Kokoro's EX1 and EX2 each end the other's buff, and JP says 「上がります！」の効果を解除. Removals within the same skill stay internal.
- **Animation locks:** `StatusAdd` of a `Disable*` status in the `Dummy` category lasting up to 1 second only locks input during the skill's animation, and isn't described.

### 8.1 Complex mechanics

Mechanics that span several skills of one character, worked out on Ibuki (Swimsuit), Iroha (Swimsuit), Rio and Shun (Swimsuit) but implemented generically.

- **Several picked targets:** a `BundledTimelineActionDAO` repeats its entities per `TargetContainerIndex`, one player-picked target each. The root rule's single target becomes "up to N". Entities of later containers add no hits, and `BundledMainEntityDatas` are preview copies.
- **Temporary tags:** a marker lasting 1 second or less, put without conditions on picked targets ("the ally with the highest Critical Damage"), only lets later abilities find them again ("all allies if the target has the tag"). Those abilities take the tagged targets instead (`tag_applications`). Iroha (Swimsuit): "Grant one other Attacker ally with the highest Critical Damage "Partner"".
- **Blackboard targets:** `OptionalCandidateRule.BlackboardConstraint.KeyString` limits targets to a unit written by `WriteEntityToBlackboard`. The marker given in the same ability names it: "one other ally with "Partner"".
- **Timers:** a Normal skill used when an internal marker is removed (`AutoUseRule` `RemoveLogicEffectTemplateId`) is periodic when a passive triggered by using that skill starts the marker again. The period is the marker duration plus the frame it is applied at (34 s + 29 frames = "every 35 seconds"). Timers started by other skills (Subaru's full-auto fire) stay "when X ends".
- **Battle start:** `AutoUseRule` `Interval` of a frame or so with `MaxTriggerCount` 1 is "at the start of battle".
- **Counters:** `BlackBoardAdd` raises a per-owner counter, usually together with a stacking marker that shows it. `BlackBoardAlarmOnReach` applies `AlarmEffectGroupIdList` when the counter reaches `AlarmValue`. The counter is named after the marker the same character adds with it: "When "Seashell" reaches 12 stacks, enter an alternate state…, remove all "Seashell" and gain "Seashell Flower"".
- **Damage storage:** `AccumulateDamageFromTargets` stores `AccumulateRate` of the damage dealt by holders of `TargetLogicEffectGroupId`'s marker, and applies its `ExecuteLogicEffectGroupId0N` damage when it expires or is removed. `ObjectLogicEffectGroupId` is the visible marker (the Suitcase), described as part of this clause. The cap comes from `LimitSourceBlackboardKeyString`, a key filled by `AddDamageToBlackBoard` (EX skill damage) times `LimitSourceBlackboardRate`. Copies without an object only drive visuals.
- **Card copying:** `SkillCardCopyTarget` (`EndCondition` `TriggerCount` = uses) turns the caster's card into the copy through `ChangeSkillCardToCopiedCard` (`CopiedCardCostModifyByAmount`, relative to the copied skill's cost). The card stays in hand: "Replace this card with a copy of the EX skill card of one other ally (usable once; costs 1 less than the original, minimum 0)".
- **Cards staying in hand:** when a form switch with `ExSkillCardRedrawInHand` changes the EX skill, the new skill's card replaces the used one in hand instead of the next card in the deck coming in: "(EX skill changes to "Surfacing!"; the card stays in hand)".
  - JP calls this drawing the EX skill immediately (「EXスキルをすぐに1回ドロー」), but only for some skills (Neru (School Uniform), Ibuki (Swimsuit), CH0334). Toki, Kokoro, Kisaki (Swimsuit), Noa (Pajama) and Shun (Swimsuit) Kid have identical form switch data and don't mention it.
  - Without an EX skill change, the flag has no visible effect.
- **Card draw:** `ExSkillCardRedrawGauge` draws cards on later EX skill uses ("immediately draw 1 EX skill card on next EX skill use").
- **EX stages:** an EX skill whose form switch changes the EX skill into one with the same name, for good, is a stage of itself. When every stage deals damage and the damage changes by the same amount: "Each use reduces the damage of this skill by 290% of Attack for the rest of the battle (up to 3 times)". Untranslated stages borrow the EN name of a translated skill with the same JP name.
- **Numbered marker families:** markers numbered by level (`Dummy_CH0355_01_Flower_Icon01..03`) whose base has a name in `translation/SkillEffects.json` are levels of that effect. A level applied while having the previous one grows: "After 3.8 seconds, "Flower Bud" grows to level 2".
- **Timing details** are dropped from conditions: "not having" one of the skill's own timers that has always run out by then, and "not having" a brief (1 second or less) lock set by another skill.
- **Visual-only markers** (`Visual`, `_FX`, `Emoji` in the TemplateId) are internal, and so are exclusions of dead or incapacitated targets.
- **Fallback picks:** a tag picked again when the first pick found nobody (condition: no other ally has the tag) is a fallback for the same targets: "one other Attacker ally with the highest Critical Damage (or, if there is none, one other ally with the highest Critical Damage)".
- **Role variants:** a marker given next to another one only when the target has a class (`CountListTacticRole` on the target) marks that class among its holders. Ibuki (Swimsuit)'s `Dummy_CH0347_PlayFriend_Dealer` is "Friend" for Attackers. The grants are not described, and counts of them read "with 1/2 Attacker "Friend" among other allies" (`role_variant`).
- **Proxy flags:** an internal permanent flag a character sets on itself depending on one condition about others stands for that condition. Shun (Swimsuit) Kid's `CheckAddCostAlly` is set when another ally has tag 872, so her Normal skill reads "unless another ally is Shun" (`proxy_flag`).
- **Unit counters:** a stacking marker a character gives itself once per unit it tagged, plus a fixed offset, counts those units. Shun (Swimsuit) Kid's "Count Ally" is one per other ally plus one: "with 1/2/3/4/5/6+ allies (including self)" (`unit_counter`).
- **Hidden card draws:** a hidden passive's `ExSkillCardRedrawGauge` that draws on any EX skill use, with a draw ready from the start, is described with the character's base EX skill ("Immediately draw an EX skill card"), not the Passive skill hosting it. This excludes skills that already keep or replace the card in hand. Slot-specific gauges (Arisu (Battle)'s charge skills) and gauges filled by other mechanics (Hanako (Swimsuit)'s water gauge) are left out.
- **Summoned units' abilities:** a marker a skill puts on a unit its character summons can enable abilities in that unit's skills, the same way markers unlock normal attacks and hidden passives. Reisa (Magical)'s Normal skill flags Thermite Pink, whose hidden passive then runs a second aura: "The summon: increase Critical Damage of other allies in a circular area by 16.3% for 22 seconds". The trigger is not repeated when it is the flag the describing skill applies.
- **Tags of one's own summon:** a tag carried by one student and a unit she summons picks out that unit, so the target reads "the summon" rather than "one other ally who are Reisa" (Reisa (Magical) hands her "Sugar Magical Power" stacks over when she deploys).
- **Levels carried across:** a character's hidden passive can give itself one marker per level (`Dummy_CH0326_PublicLevelCheck_Lv01…Lv10`), which another character's skill checks to pick the matching effect. Those markers resolve to the level being described, so one value shows instead of ten tiers.

### 8.2 Raid bosses

`skill_mechanics_check.py -raid` checks the skills shown for bosses of Total Assault, Grand Assault, Multi-Floor Raid and World Raid stages. It checks each skill once per set of boss tags (difficulty), 968 pairs in all (`out/skill_mechanics_check_raid.txt`).

- **Difficulty variants:** one skill often holds every difficulty's variant, such as Kurokage's EX summoning `…_Normal` through `…_Lunatic`.
  - The variants are gated by `IncludeTag`/`ExcludeTag` spawn conditions, whose `SpawnConditionParameter` names the tag (`Raid_Lunatic`) and `SpawnConditionParameterForTag` gives its number (696). `TagConditional` modifiers use the number only.
  - Each difficulty's boss character carries its tag in `CharacterExcelTable.Tags`, obfuscated (`gK` = 696, see `tag_number`).
  - `SkillMechanics.from_data(caster=character)` settles every tag condition on the caster and keeps only the summons of that difficulty.
- **Groggy gauge** (`GroggyGauge`): `Amount` in points of the boss's own `GroggyGauge` stat (Goz: 250000000 of 2000000000 = JP's 12.5%). Shown as a percentage when the caster is known.
- **Damage transfer** (`DamageTransfer`): the holder passes `TransferRatio` of the damage it takes on to the caster (Perorozilla's minions), through `TransferredDamageEffectGroupId`.
- **Crowd control gauge** (`CrowdControlGauge`): crowd control durations on the holder add up; at `MaxGaugeValue` ms the `MaxGaugeLogicEffectGroupIdList` effects apply. Hod: "at 6 seconds, increase the groggy gauge by 25% and reduce ATG by 50". `IsCalculateOppression` means higher CC Strength fills it faster, and `GaugeReduceValuePerSecond` drains it.
- **ATG** (`AddCurrentATG`): the boss skill gauge, raised or lowered by `Amount`.
- `TargetSide` `-1` (obstacle areas of EN0009) means no rule of its own.

## 9. Conditions (ability modifiers)

Every modifier has `CheckTarget` (whose state is checked) and usually `IncludeType`.

- **Count modifiers** (`Count(List)LogicEffectTemplate`, `CountListLogicEffectGroupId/Category/Type`, `CountEntityListCombined`, `CountListTacticRole`, `CountSquadAbsence`): `CountMin..CountMax`. A max of 99 or more, or -1, means unbounded.
  - An unbounded 1+ range means having any.
  - **Exclude inverts the range:** "exclude 0..2" = 3+, "exclude 1..99" = 0.
  - Omitted `CountMin`/`CountMax` fields are 0.
- **Tag counts:** `CountTagConditional` uses `Count` + `DiffOperator`.
- **School:** `SchoolConditional` uses `SchoolConstraint` (with its own IncludeType, so "Trinity student" vs "not a Trinity student") and `CountConstraint`.
- **Single checks:** `LogicEffectTemplate`, `LogicEffectCategory`, `TagConditional`, `ArmorCondition`, `BulletTypeCondition`, `CoverStateConditional`, `StatusConditional` (Dead/Dying), `CharacterIdConditional`, `PersonalityIdConditional`, `FormIndexCheck`, `TargetSideConditional`, `TacticEntityConditional`.
- **HP:** `HpRate` uses Operator + HpRate.
- **Damage scaling:** `HpRateDamage` (×min…max by target HP), `StatValueDamage`, `TargetDistanceDamage`, `CoverStateDamage`, `TacticEntityDamage`.
- **Skill level:** `SkillLevel` uses SkillSlot + Operator + SkillLevel, and may check a different skill's level. Resolve it when that level is known, otherwise use tiers ("at Sub skill level 1/2/…").
- **Tiers:** abilities identical except for a count or level condition form tiers. Merge them into one clause with every value, a per-unit step when the values grow evenly, and a multiplier when levels multiply cleanly. Several abilities at the same tier (base damage + bonus damage) add up.

## 10. Triggers

**Passives** (`TriggerCondition`):
- `Event` is a `PassiveTriggerEvent` and `Parameters` depends on the event:
  - Skill slot(s) for UseSkillStart/UseSkillEnd, DamageHit, Heal.
  - A TemplateId for Add/Remove/AppliedLogicEffectTemplate.
  - A GroupId for the …GroupId events.
  - A category for the …Category events.
  - A frame interval for `Battle_Periodic` and `BattleEntityState_NotMoving`.
- `ConditionExpression` is a small expression language: `GetHPRate() <= 3000`, `GetFormIndex() = 1`, `HasLogicEffectTemplate(X) == false`, `GetCurrentBehavior() == [BehaviorType.UseExSkill01]`, `IsReloading() == true`, joined with `&&`/`||`. `BattleEntityState_OnOff` means "while the expression holds".
- `TryCount` > 1 means every N events. `TriggerSourceFindRule.EssentialCandidate.TargetSide` says whose events count ("every 6 enemies defeated **by allies**"). `TriggerRate` is a chance. `MaxTriggerCount` > 0 is a per-battle limit.
- Common events: `Immediate` = always active. `BattleEntity_NormalAttack` and `BattleEntity_DamageHit` (any hit, JP "攻撃時") are different events.

**Normal skills** (`AutoUseRule`):
- `ConditionType` is an `AutoUseConditionType`: Interval (frames), HpUnder, AmmoCountUnder, OnAttackIng, KillTarget, CriticalAttack, UseSkill, HitLogicEffectTemplateId, …
- `ConditionCheckTarget` CasterAlly means the event counts for allies. `TryCount` and `MaxTriggerCount` work as for passives.
- **Cooldown:** SkillExcelTable `CoolTime` applies to passives and to non-interval Normal skills.

## 11. Remaining gaps

- **Unnamed markers:** none left (§7.1), and every name in `translation/SkillEffects.json` now has both JP and EN. New students will add more: rerun `skill_effect_names.py`, then add unquoted names and English by hand. 20 of 30 forms are still unnamed (§8).
- **Missing timelines:** `CH0173ExtraPassive02`, `SM008101Passive02` and `SM032601ExtraPassive01` have skill list entries but no `LevelSkill` file, so rendering logs a KeyError for them.
- **Empty descriptions:** 2 skills produce nothing. They are form-only skills triggered by internal state.
- **Damage figures:** JP simplifies damage, and the generated text keeps the detail on purpose, so some values won't match:
  - Sums of several parts (CH0056 EX: 533.4% + 532.6% vs JP 1065%).
  - Extra damage instead of totals per tier (CH0138 Normal skill).
  - One arm of overlapping areas (CH0225's cross-shaped EX).
  - Chance hits folded into a total (CH0172 Normal skill).
  - Truncating per hit before multiplying (Hina (Dress) EX 2/3: 324% vs 325.7%).
  - Arisu (Battle)'s charged EX stages are separate skills holding the multiplied damage (1330% → 2660% → 3991%), while JP prints the base numbers once with "×2 or ×3 by charge stage". The generated text gives each stage's real damage but never the multiplier.
  - Her EX's line damage sums the 8 rectangles it spawns (800% against JP's 200%): the data does not say how many of them can overlap one enemy.
  - Separately, CH0243's cost-spent tiers still combine conditions into misleading totals.
- **Complex characters (§8.1):**
  - Rio also has a hidden EX draw gauge besides the card copy. It isn't mentioned, as JP's draw for her means the card stays in hand.
- **Raid boss skills (§8.2):** 51.2% fully matched and 43.3% of JP values found, against 92.1% and 94.8% for students.
  - **Still unhandled effects:** `DeadlyAttack` (77), `MaxHPCapGaugeValue` (61), `ChangeStatLogicApplicationGauge(RecoverOverTime)` (33), `StartStatusLevelIndicator` (16), `ChangeGaugeUIType`, `RemoveVisualEffects`, `ImmuneInvokerWithLogicEffectId`.
  - **Still unhandled conditions:** `CountListSquadType` (48), `CountLogicEffectType` (45).
  - **Names:** boss status names are unmapped (`Hit`, `ImmuneDamageAll`, `ImmuneGroggyGaugeAdd`), summons show dev names or none, and tags checked on targets remain unnamed (`tagged 792`).
  - **Stat direction:** Hod's `DamagedRatio` `BaseAmount` -3000 reads "reduce Damage Taken by 30%" while JP says damage taken rises by 300%.
  - **Other:** JP boss text uses 味方 for the player's students (the generator says "enemies"), and passive rules like Binah's reduced damage to units in cover live in the EX skills.
  - **Missing data:** EN0010's per-difficulty passives have no LevelSkill files (32 of the checked pairs).
