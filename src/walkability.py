"""
VERDICT BUILDER: VerdictBuilder
================================

Builds verdict and narrative from access analysis + context.

This class encapsulates:
- Score combination rules
- Verdict threshold logic
- Narrative generation
- Assessment aggregation

Author: Marita R. Botin
"""

from typing import Dict, List, Optional, Tuple
from data_models import AccessStatus, FunctionScore, Assessment, VerdictTone
from config import (
    LENSES, VERDICT_THRESHOLDS, FUNCTION_READY_THRESHOLD, 
    FUNCTION_WEIGHTS, NARRATIVE_TEMPLATE_GOOD, NARRATIVE_TEMPLATE_CLOSE,
    NARRATIVE_TEMPLATE_BAD
)


class VerdictBuilder:
    """
    Builds verdict and narrative from access analysis.
    
    This class encapsulates:
    - Score combination rules
    - Verdict threshold logic
    - Narrative generation
    - Assessment aggregation
    """

    def __init__(self) -> None:
        """Initialize with verdict rules from config."""
        self._thresholds = VERDICT_THRESHOLDS
        self._function_ready_threshold = FUNCTION_READY_THRESHOLD

    def build_assessment(
        self,
        center: Tuple[float, float],
        access_by_function: Dict[str, AccessStatus],
        travel_mode: str = "walking",
        iso_source: str = "api",
        place_name: str = "Selected point",
        barangay: Optional[str] = None,
        district: Optional[str] = None,
    ) -> Assessment:
        """
        Build a complete assessment from access analysis.
        
        Args:
            center: (lng, lat)
            access_by_function: Result from SixFunctionAnalyzer.analyze_catchment()
            travel_mode: "walking" or "cycling"
            iso_source: "api", "fallback", or "cache"
            place_name: Neighborhood name
            barangay: Barangay name (if found)
            district: District name (if found)
        
        Returns:
            Complete Assessment object
        """
        # Convert AccessStatus to FunctionScore
        function_scores = self._access_to_function_scores(access_by_function)

        # Compute aggregate scores
        overall_score, ready_count = self._compute_overall_score(function_scores)
        transit_score = self._estimate_transit_score(
            access_by_function.get("living")
        )
        living_score = self._estimate_living_score(function_scores)

        # Determine verdict tone
        verdict_tone = self._determine_verdict(
            ready_count, transit_score, overall_score
        )

        # Generate narrative
        narrative = self._generate_narrative(
            verdict_tone, function_scores, travel_mode, overall_score
        )

        # Compute rings readiness
        rings_ready = self._compute_rings_ready(access_by_function)

        return Assessment(
            center=center,
            access_by_function=access_by_function,
            function_scores=function_scores,
            verdict_tone=verdict_tone,
            overall_score=overall_score,
            narrative=narrative,
            ready_count=ready_count,
            transit_score=transit_score,
            living_score=living_score,
            rings_ready=rings_ready,
            place_name=place_name,
            barangay=barangay,
            district=district,
            iso_source=iso_source,
        )

    def _access_to_function_scores(
        self, access_by_function: Dict[str, AccessStatus]
    ) -> List[FunctionScore]:
        """
        Convert AccessStatus objects to FunctionScore objects.
        
        Args:
            access_by_function: Dictionary of AccessStatus objects
        
        Returns:
            List of FunctionScore objects (one per lens)
        """
        scores = []

        for function_id in LENSES.keys():
            access = access_by_function.get(function_id)
            if access is None:
                continue

            lens_config = LENSES[function_id]
            tone = self._score_to_tone(access.access_score)

            # Build detail string
            if access.minute is not None:
                detail = (
                    f"{lens_config['label']} begins within {access.minute} min. "
                    f"Found {access.count_within_15} destinations "
                    f"({access.category_count} types)."
                )
            else:
                detail = (
                    f"No {lens_config['label']} destinations "
                    f"found within 15 min."
                )

            # Build evidence
            evidence = [
                f"First: {access.minute}min" if access.minute else "Outside 15min",
                f"5/10/15: {access.count_by_minute[5]}/"
                f"{access.count_within_10}/{access.count_within_15}",
                f"{access.category_count} type"
                f"{'s' if access.category_count != 1 else ''}",
            ]

            fs = FunctionScore(
                function_id=function_id,
                label=lens_config["label"],
                color=lens_config["color"],
                score=access.access_score,
                tone=tone,
                detail=detail,
                minute=access.minute,
                evidence=evidence,
            )
            scores.append(fs)

        return scores

    @staticmethod
    def _score_to_tone(score: int) -> VerdictTone:
        """
        Convert 0-100 score to tone classification.
        
        Args:
            score: Score from 0 to 100
        
        Returns:
            VerdictTone (GOOD, CLOSE, or BAD)
        """
        if score >= 74:
            return VerdictTone.GOOD
        elif score >= 52:
            return VerdictTone.CLOSE
        else:
            return VerdictTone.BAD

    def _compute_overall_score(
        self, function_scores: List[FunctionScore]
    ) -> Tuple[int, int]:
        """
        Compute weighted average of function scores.
        
        Args:
            function_scores: List of all 6 FunctionScore objects
        
        Returns:
            Tuple of (overall_score, ready_count)
        """
        if not function_scores:
            return 0, 0

        weighted_sum = 0.0
        ready_count = 0

        for fs in function_scores:
            weight = FUNCTION_WEIGHTS.get(fs.function_id, 1.0 / len(LENSES))
            weighted_sum += fs.score * weight

            if fs.score >= self._function_ready_threshold:
                ready_count += 1

        overall_score = round(weighted_sum)
        return overall_score, ready_count

    @staticmethod
    def _estimate_transit_score(living_access: Optional[AccessStatus]) -> int:
        """
        Estimate transit enablement from living/transit access.
        
        Args:
            living_access: AccessStatus for the living/transit function
        
        Returns:
            Transit score (0-100)
        """
        if living_access is None:
            return 0
        return living_access.access_score

    @staticmethod
    def _estimate_living_score(function_scores: List[FunctionScore]) -> int:
        """
        Estimate living quality score from all functions.
        
        Args:
            function_scores: List of all FunctionScore objects
        
        Returns:
            Living quality score (0-100)
        """
        non_work = [fs.score for fs in function_scores if fs.function_id != "working"]
        if non_work:
            return round(sum(non_work) / len(non_work))
        return 0

    def _determine_verdict(
        self, ready_count: int, transit_score: int, overall_score: int
    ) -> VerdictTone:
        """
        Determine verdict tone based on thresholds.
        
        Args:
            ready_count: Number of functions scoring >= 60
            transit_score: Transit enablement score
            overall_score: Weighted average score
        
        Returns:
            VerdictTone (GOOD, CLOSE, or BAD)
        """
        good = self._thresholds.get("good", {})
        close = self._thresholds.get("close", {})

        if (
            ready_count >= good.get("min_functions_ready", 6)
            and transit_score >= good.get("min_transit_score", 68)
            and overall_score >= good.get("min_overall_score", 68)
        ):
            return VerdictTone.GOOD

        if (
            ready_count >= close.get("min_functions_ready", 5)
            and transit_score >= close.get("min_transit_score", 46)
            and overall_score >= close.get("min_overall_score", 55)
        ):
            return VerdictTone.CLOSE

        return VerdictTone.BAD

    def _generate_narrative(
        self,
        verdict_tone: VerdictTone,
        function_scores: List[FunctionScore],
        travel_mode: str,
        overall_score: int,
    ) -> str:
        """
        Generate human-readable narrative for the verdict.
        
        Args:
            verdict_tone: GOOD, CLOSE, or BAD
            function_scores: List of all function scores
            travel_mode: "walking" or "cycling"
            overall_score: Overall readiness score
        
        Returns:
            Human-readable summary string
        """
        mode_label = "Walking" if travel_mode == "walking" else "Cycling"

        if verdict_tone == VerdictTone.GOOD:
            return NARRATIVE_TEMPLATE_GOOD.format(
                mode=mode_label, score=overall_score
            )

        # Find missing functions
        missing = [fs.label.lower() for fs in function_scores if fs.score < 60]
        missing_str = " and ".join(missing[:2]) if missing else "several functions"

        if verdict_tone == VerdictTone.CLOSE:
            return NARRATIVE_TEMPLATE_CLOSE.format(
                mode=mode_label, missing=missing_str
            )

        # BAD
        weakest = min(function_scores, key=lambda fs: fs.score, default=None)
        weakest_label = weakest.label.lower() if weakest else "services"
        return NARRATIVE_TEMPLATE_BAD.format(
            mode=mode_label,
            weakest=weakest_label,
            missing=missing_str,
        )

    @staticmethod
    def _compute_rings_ready(
        access_by_function: Dict[str, AccessStatus]
    ) -> Dict[int, int]:
        """
        Compute how many functions are ready per ring.
        
        Args:
            access_by_function: AccessStatus for all functions
        
        Returns:
            {5: count, 10: count, 15: count}
        """
        rings = {5: 0, 10: 0, 15: 0}

        for access in access_by_function.values():
            for minutes in [5, 10, 15]:
                if access.minute is not None and access.minute <= minutes:
                    rings[minutes] += 1

        return rings
