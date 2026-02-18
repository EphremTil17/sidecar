from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ingestion.orchestrator import RecordingOrchestrator
    from core.ingestion.screen import ScreenCapture
    from core.intelligence.model import SidecarBrain
    from core.intelligence.skills import SkillManager


@dataclass
class ComponentRegistry:
    """
    Standardized container for core application components.
    Provides type-safety and eliminates magic-string lookups.
    """

    brain: "SidecarBrain"
    capture_tool: "ScreenCapture"
    recorder: "RecordingOrchestrator"
    skill_manager: "SkillManager"
