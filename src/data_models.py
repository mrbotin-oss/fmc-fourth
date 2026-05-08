"""
DATA MODELS - Makati 15-Minute Observatory
============================================

Encapsulates all structured data and result objects using dataclasses.

Classes:
    - VerdictTone: Enum for verdict classification
    - AccessStatus: Results of analyzing one function
    - FunctionScore: Scored and narrativized function
    - ContextMetric: Local support metric
    - Assessment: Complete evaluation result

Author: Marita R. Botin
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List, Tuple
from enum import Enum


class VerdictTone(Enum):
    """Enum for verdict classification.
    
    Attributes:
        GOOD: All 6 functions ready + transit >= 68 + overall >= 68
        CLOSE: 5+ functions ready + transit >= 46 + overall >= 55
        BAD: Otherwise
    """
    GOOD = "good"
    CLOSE = "close"
    BAD = "bad"


@dataclass
class AccessStatus:
    """
    Encapsulates access analysis for a single function/lens.
    
    Measures how well a location satisfies one daily-life function
    (living, working, supplying, caring, learning, enjoying) within
    an isochrone catchment.
    
    Attributes:
        lens_id (str): Function identifier (e.g., 'living', 'working')
        minute (Optional[int]): First reachable destination (5, 10, 15 min, or None)
        count_by_minute (Dict[int, int]): Mapping of minutes to count of destinations
        categories (Set[str]): Set of place type labels
        examples (List[str]): Up to 3 example place names
        access_score (int): Composite score (0-100)
    """
    lens_id: str
    minute: Optional[int] = None
    count_by_minute: Dict[int, int] = field(
        default_factory=lambda: {5: 0, 10: 0, 15: 0}
    )
    categories: Set[str] = field(default_factory=set)
    examples: List[str] = field(default_factory=list)
    access_score: int = 0

    @property
    def count_within_15(self) -> int:
        """Total destinations reachable within 15 minutes."""
        return self.count_by_minute.get(15, 0)

    @property
    def count_within_10(self) -> int:
        """Total destinations reachable within 10 minutes."""
        count_5 = self.count_by_minute.get(5, 0)
        count_10 = self.count_by_minute.get(10, 0)
        return count_5 + count_10

    @property
    def category_count(self) -> int:
        """Number of distinct place categories."""
        return len(self.categories)

    def __repr__(self) -> str:
        return (
            f"AccessStatus(lens_id={self.lens_id!r}, minute={self.minute}, "
            f"count_15={self.count_within_15}, score={self.access_score})"
        )


@dataclass
class FunctionScore:
    """
    Score and narrative for one of the 6 social functions.
    
    Represents the assessed readiness of a function at a location,
    including the score, tone (GOOD/CLOSE/BAD), and human-readable explanation.
    
    Attributes:
        function_id (str): Function identifier
        label (str): Display name (e.g., 'Living')
        color (str): Hex color code for visualization
        score (int): Composite score (0-100)
        tone (VerdictTone): Classification (GOOD/CLOSE/BAD)
        detail (str): Human-readable explanation
        minute (Optional[int]): How soon first destination appears
        evidence (List[str]): Supporting facts for the score
    """
    function_id: str
    label: str
    color: str
    score: int
    tone: 'VerdictTone'
    detail: str
    minute: Optional[int] = None
    evidence: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"FunctionScore(function_id={self.function_id!r}, "
            f"label={self.label!r}, score={self.score}, tone={self.tone.value})"
        )


@dataclass
class ContextMetric:
    """
    Score for one local support dimension.
    
    Measures neighborhood context: walkability, transit reach, urban density,
    green comfort, housing affordability burden.
    
    Attributes:
        metric_id (str): Metric identifier (e.g., 'walkability')
        label (str): Display name
        score (int): Normalized score (0-100)
        raw_value (float): Original measurement value
        display (str): Formatted string for UI
        color (str): Hex color for visualization
    """
    metric_id: str
    label: str
    score: int
    raw_value: float
    display: str
    color: str

    def __repr__(self) -> str:
        return (
            f"ContextMetric(metric_id={self.metric_id!r}, "
            f"label={self.label!r}, score={self.score})"
        )


@dataclass
class Assessment:
    """
    Complete evaluation result for a selected point.
    
    Combines isochrone analysis, function scores, and local context
    to produce a transparent verdict about 15-minute city readiness.
    This is the final result object passed to the UI for display.
    
    Attributes:
        center (Tuple[float, float]): (lng, lat) coordinates
        isochrones (Dict[int, Polygon]): {5: Polygon, 10: Polygon, 15: Polygon}
        access_by_function (Dict[str, AccessStatus]): Results for each function
        function_scores (List[FunctionScore]): Scored results (all 6)
        context_metrics (List[ContextMetric]): Local support metrics
        verdict_tone (VerdictTone): GOOD, CLOSE, or BAD
        overall_score (int): 0-100 weighted average
        narrative (str): AI-style summary text
        ready_count (int): How many of 6 functions are >= 60
        transit_score (int): Transit enablement (0-100)
        living_score (int): Residential quality (0-100)
        rings_ready (Dict[int, int]): {5: count, 10: count, 15: count}
        place_name (str): Neighborhood or barangay name
        barangay (Optional[str]): Barangay name (if found)
        district (Optional[str]): District name (if found)
        iso_source (str): "api", "cache", or "fallback"
    """
    center: Tuple[float, float]
    isochrones: Dict[int, object] = field(default_factory=dict)
    access_by_function: Dict[str, AccessStatus] = field(default_factory=dict)
    function_scores: List[FunctionScore] = field(default_factory=list)
    context_metrics: List[ContextMetric] = field(default_factory=list)
    
    verdict_tone: 'VerdictTone' = VerdictTone.BAD
    overall_score: int = 0
    narrative: str = ""
    ready_count: int = 0
    transit_score: int = 0
    living_score: int = 0
    
    rings_ready: Dict[int, int] = field(
        default_factory=lambda: {5: 0, 10: 0, 15: 0}
    )
    
    place_name: str = "Selected point"
    barangay: Optional[str] = None
    district: Optional[str] = None
    iso_source: str = "api"

    def __repr__(self) -> str:
        return (
            f"Assessment(center={self.center}, "
            f"verdict={self.verdict_tone.value}, score={self.overall_score})"
        )
