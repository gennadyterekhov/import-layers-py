from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    violations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
