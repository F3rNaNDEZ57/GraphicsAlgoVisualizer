from dataclasses import dataclass


@dataclass
class PlaybackState:
    playing: bool = False
    delay_ms: int = 150
