"""Versioned appearance recipe for the layered adult character kit.

Separate from gender and legacy avatar identity. None on Entity means use the
existing complete sprite sheet until the approved layered kit is available.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CharacterAppearance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    base: Literal["male", "female"]
    skin: Literal["fair", "light", "medium", "tan", "brown", "deep"] = "medium"
    face: Literal["oval", "round", "angular"] = "oval"
    eyes: Literal["brown", "hazel", "green", "blue", "grey"] = "brown"
    hair: Literal["short", "cropped", "tied", "long", "bald"] = "short"
    hair_color: str = Field(default="#493629", pattern=r"^#[0-9a-fA-F]{6}$")
    clothing: Literal["tunic", "workwear", "dress"] = "tunic"
    clothing_color: str = Field(default="#526d61", pattern=r"^#[0-9a-fA-F]{6}$")
    footwear: Literal["boots", "shoes", "sandals"] = "boots"
    facial_hair: Literal["none", "stubble", "beard"] = "none"
