from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Beat:
    id: str
    kind: str
    cue: str
    parenthetical: str
    start: str
    end: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Beat":
        return cls(
            id=data["id"],
            kind=data["kind"],
            cue=data["cue"],
            parenthetical=data.get("parenthetical") or "",
            start=data.get("start") or "",
            end=data.get("end") or "",
            text=data.get("text") or "",
        )


@dataclass
class Scene:
    number: int
    heading: str
    start: str
    end: str
    beats: list[Beat] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "heading": self.heading,
            "start": self.start,
            "end": self.end,
            "beats": [beat.to_dict() for beat in self.beats],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        return cls(
            number=int(data["number"]),
            heading=data.get("heading") or "",
            start=data.get("start") or "",
            end=data.get("end") or "",
            beats=[Beat.from_dict(beat) for beat in data.get("beats") or []],
        )


@dataclass
class Episode:
    number: int
    logline: str
    continuity: str
    source_file: str
    scenes: list[Scene] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def beats(self) -> list[Beat]:
        return [beat for scene in self.scenes for beat in scene.beats]

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "logline": self.logline,
            "continuity": self.continuity,
            "source_file": self.source_file,
            "warnings": self.warnings,
            "scenes": [scene.to_dict() for scene in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Episode":
        return cls(
            number=int(data["number"]),
            logline=data.get("logline") or "",
            continuity=data.get("continuity") or "",
            source_file=data.get("source_file") or "",
            scenes=[Scene.from_dict(scene) for scene in data.get("scenes") or []],
            warnings=list(data.get("warnings") or []),
        )
