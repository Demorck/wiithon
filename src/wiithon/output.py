"""
What a conversion should produce.

The format is carried by the type rather than by a string, so a setting that only exists for one container can't
be handed to another and it's cleaner
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsoOutput:
    """
    A plain vanilla ISO, byte for byte what the disc holds

    What every tool reads and the reference every other container has to be able to reproduce.
    """