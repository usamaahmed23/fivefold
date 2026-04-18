"""Core Pydantic models for Fivefold."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Color = Literal["R", "G", "U", "W", "B", "C"]
Role = Literal["top", "jungle", "mid", "bot", "support"]
Phase = Literal["ban1", "pick1", "ban2", "pick2", "complete"]
Side = Literal["blue", "red"]
Action = Literal["ban", "pick"]
Level = Literal["none", "low", "medium", "high"]
ScalingLevel = Literal["early", "mid", "late"]
DamageProfile = Literal["ad", "ap", "mixed", "true", "tank"]
RangeLevel = Literal["melee", "short", "medium", "long"]


class StructuralTags(BaseModel):
    damage_profile: Optional[DamageProfile] = None
    range: Optional[RangeLevel] = None
    engage: Optional[Level] = None
    peel: Optional[Level] = None
    frontline: Optional[Level] = None
    waveclear: Optional[Level] = None
    scaling: Optional[ScalingLevel] = None


class ContextRule(BaseModel):
    condition: Literal["ally_has_champion", "enemy_has_champion"]
    value: str
    effect: Literal["add_main_color", "add_off_color", "remove_main_color"]
    color: Color


class Champion(BaseModel):
    id: str
    name: str
    colors_main: list[Color] = Field(default_factory=list)
    colors_off: list[Color] = Field(default_factory=list)
    contextual: bool = False
    ls_notes: Optional[str] = None
    source: Optional[str] = None
    roles: list[Role] = Field(default_factory=list)
    win_condition_tags: list[str] = Field(default_factory=list)
    structural_tags: Optional[StructuralTags] = None
    counter_tags: list[str] = Field(default_factory=list)
    strong_against_tags: list[str] = Field(default_factory=list)
    kit_tags: list[str] = Field(default_factory=list)
    context_rules: list[ContextRule] = Field(default_factory=list)


class Archetype(BaseModel):
    """A kit-based comp archetype. Members are champion IDs whose kits slot
    into this archetype (e.g. reliable knockup setups, global-ult map pressure,
    spell-shield counters to chain CC). Used for synergy + counter scoring."""
    id: str
    name: str
    kind: Literal["synergy", "counter"]
    description: str = ""
    members: list[str] = Field(default_factory=list)
    # For counter archetypes: the kit_tags on enemies that this archetype
    # punishes (e.g. "chain_cc", "scaling", "high_mobility").
    targets: list[str] = Field(default_factory=list)


class Archetypes(BaseModel):
    archetypes: list[Archetype] = Field(default_factory=list)


class MetaTiers(BaseModel):
    patch: str = ""
    updated_at: str = ""
    tiers: dict[Role, list[str]] = Field(default_factory=dict)


class DraftState(BaseModel):
    phase: Phase
    turn_index: int = 0
    blue_bans: list[str] = Field(default_factory=list)
    red_bans: list[str] = Field(default_factory=list)
    blue_picks: list[str] = Field(default_factory=list)
    red_picks: list[str] = Field(default_factory=list)
    side_to_act: Side
    action_to_take: Action
    first_pick_side: Side = "blue"

    @property
    def our_picks(self) -> list[str]:
        return self.blue_picks if self.side_to_act == "blue" else self.red_picks

    @property
    def enemy_picks(self) -> list[str]:
        return self.red_picks if self.side_to_act == "blue" else self.blue_picks

    @property
    def our_bans(self) -> list[str]:
        return self.blue_bans if self.side_to_act == "blue" else self.red_bans

    @property
    def enemy_bans(self) -> list[str]:
        return self.red_bans if self.side_to_act == "blue" else self.blue_bans

    @property
    def taken(self) -> set[str]:
        return set(self.blue_bans + self.red_bans + self.blue_picks + self.red_picks)


class AxisBreakdown(BaseModel):
    """Sub-components that built an axis score, for UI explanation."""
    notes: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    champion_id: str
    identity: float
    denial: float
    structural: float
    survivability: float
    meta_contribution: float
    total: float
    rationale: list[str] = Field(default_factory=list)
