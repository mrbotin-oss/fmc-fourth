"""
ANALYZER: SixFunctionAnalyzer
=============================

Analyzes the six daily-life functions within an isochrone catchment.

This class encapsulates all logic for:
- Point-in-polygon spatial queries
- Scoring rule application
- Category diversity calculation
- AccessStatus generation

Author: Marita R. Botin
"""

import math
from typing import Dict, Optional, Set, List
import geopandas as gpd
from shapely.geometry import Polygon
import pandas as pd

from data_models import AccessStatus, VerdictTone
from config import LENSES, ACCESS_SCORE_RULES, SCORE_WEIGHTS


class SixFunctionAnalyzer:
    """
    Analyzes the six daily-life functions within an isochrone catchment.
    
    This class encapsulates all logic for:
    - Point-in-polygon spatial queries
    - Scoring rule application
    - Category diversity calculation
    - AccessStatus generation
    
    Attributes:
        _scoring_rules: Hardcoded targets per function
        _lenses: Configuration for all 6 lenses
    """

    def __init__(self) -> None:
        """Initialize analyzer with scoring rules from config."""
        self._scoring_rules = ACCESS_SCORE_RULES
        self._lenses = LENSES

    def analyze_catchment(
        self,
        isochrones: Dict[int, Polygon],
        places_gdf: gpd.GeoDataFrame,
    ) -> Dict[str, AccessStatus]:
        """
        Analyze all six functions within isochrones.
        
        Args:
            isochrones: Polygons for time bands {5: Polygon, 10: Polygon, 15: Polygon}
            places_gdf: GeoDataFrame with place points. Must have columns:
                - geometry (Point)
                - lens_id (str: living, working, supplying, etc.)
                - category_label (str)
                - name (str)
        
        Returns:
            Dictionary mapping function_id to AccessStatus
        
        Raises:
            KeyError: If required columns missing in GeoDataFrame
        """
        results = {}

        for function_id in self._lenses.keys():
            # Filter places for this lens
            lens_places = places_gdf[places_gdf["lens_id"] == function_id]

            if lens_places.empty:
                # No places for this function
                results[function_id] = AccessStatus(
                    lens_id=function_id,
                    minute=None,
                    access_score=0
                )
                continue

            # Analyze this lens across 5/10/15 min rings
            status = self._analyze_single_lens(
                function_id, lens_places, isochrones
            )
            results[function_id] = status

        return results

    def _analyze_single_lens(
        self,
        lens_id: str,
        lens_places: gpd.GeoDataFrame,
        isochrones: Dict[int, Polygon],
    ) -> AccessStatus:
        """
        Analyze a single lens/function.
        
        Args:
            lens_id: Function identifier
            lens_places: Filtered GeoDataFrame for this lens
            isochrones: Isochrone polygons
        
        Returns:
            AccessStatus with minute, count_by_minute, categories, and score
        """
        count_by_minute = {5: 0, 10: 0, 15: 0}
        categories: Set[str] = set()
        examples: List[str] = []
        first_minute: Optional[int] = None

        # Check which places fall within each ring
        for minutes in [5, 10, 15]:
            iso_poly = isochrones.get(minutes)
            if iso_poly is None:
                continue

            # Find places inside this ring
            within_ring = self._points_in_polygon(lens_places, iso_poly)

            if not within_ring.empty:
                count = len(within_ring)
                count_by_minute[minutes] = count

                # Track first appearance
                if first_minute is None:
                    first_minute = minutes

                # Collect categories
                if "category_label" in within_ring.columns:
                    cats = within_ring["category_label"]
                    if isinstance(cats, pd.Series):
                        categories.update(cats.dropna().unique())

                # Collect examples (up to 3)
                if len(examples) < 3 and "name" in within_ring.columns:
                    names = within_ring["name"]
                    if isinstance(names, pd.Series):
                        examples.extend(
                            names.dropna().unique()[:3 - len(examples)]
                        )

        # Compute access score
        access_score = self._compute_access_score(
            lens_id, first_minute, count_by_minute, len(categories)
        )

        return AccessStatus(
            lens_id=lens_id,
            minute=first_minute,
            count_by_minute=count_by_minute,
            categories=categories,
            examples=examples[:3],
            access_score=access_score,
        )

    @staticmethod
    def _points_in_polygon(
        points_gdf: gpd.GeoDataFrame, polygon: Polygon
    ) -> gpd.GeoDataFrame:
        """
        Find all points inside a polygon.
        
        Args:
            points_gdf: GeoDataFrame with point geometries
            polygon: Shapely Polygon
        
        Returns:
            Filtered GeoDataFrame with points inside polygon
        """
        return points_gdf[points_gdf.geometry.within(polygon)]

    def _compute_access_score(
        self,
        lens_id: str,
        minute: Optional[int],
        count_by_minute: Dict[int, int],
        category_count: int,
    ) -> int:
        """
        Compute 0-100 score for a lens.
        
        Formula:
            AccessScore = Proximity + BandScores + Diversity
        
        Where:
        - Proximity = 30 if minute <= 5, else 0
        - BandScores = Points for counts in each time band
        - Diversity = Points for category variety
        
        Args:
            lens_id: Function identifier
            minute: First reachable destination (5, 10, 15, None)
            count_by_minute: {5: count, 10: count, 15: count}
            category_count: Number of distinct place types
        
        Returns:
            Score clamped to [0, 100]
        """
        if minute is None:
            # No reachable destinations
            return 0

        rules = self._scoring_rules.get(lens_id, self._scoring_rules["supplying"])

        # 1. Proximity bonus
        proximity_bonus = SCORE_WEIGHTS["proximity_bonus"] if minute == 5 else 0

        # 2. Count bands
        count_5 = count_by_minute.get(5, 0)
        count_10 = count_by_minute.get(10, 0) + count_5
        count_15 = count_by_minute.get(15, 0) + count_10

        score_5 = self._ratio_to_score(
            count_5, rules["target_5_min"], SCORE_WEIGHTS["band_5_min"]
        )
        score_10 = self._ratio_to_score(
            count_10, rules["target_10_min"], SCORE_WEIGHTS["band_10_min"]
        )
        score_15 = self._ratio_to_score(
            count_15, rules["target_15_min"], SCORE_WEIGHTS["band_15_min"], 
            log_scale=True
        )

        # 3. Diversity
        diversity_score = self._category_diversity_score(
            category_count, rules["diversity_target"], SCORE_WEIGHTS["diversity"]
        )

        # Total
        total = proximity_bonus + score_5 + score_10 + score_15 + diversity_score
        return max(0, min(100, total))

    @staticmethod
    def _ratio_to_score(
        actual: int, target: int, max_score: int, log_scale: bool = False
    ) -> int:
        """
        Convert actual/target ratio into a score contribution.
        
        If log_scale=True, uses logarithmic scaling to reward scale economies.
        
        Args:
            actual: Observed count
            target: Target count
            max_score: Maximum points available
            log_scale: Whether to use logarithmic scaling
        
        Returns:
            Score contribution (0 to max_score)
        """
        if target <= 0 or actual <= 0:
            return 0

        if log_scale:
            ratio = math.log1p(actual) / math.log1p(target)
        else:
            ratio = actual / target

        ratio = max(0, min(1, ratio))
        return round(ratio * max_score)

    @staticmethod
    def _category_diversity_score(
        category_count: int, target: int, max_score: int
    ) -> int:
        """
        Score based on how many different place types exist.
        
        Formula:
        - If 0 categories: 0 points
        - If 1 category: 45% of max (half-credit for single type)
        - Otherwise: richness score capped at target
        
        Args:
            category_count: Number of distinct place types
            target: Target number of types
            max_score: Maximum points available
        
        Returns:
            Diversity score (0 to max_score)
        """
        if category_count == 0:
            return 0
        if category_count == 1:
            return round(max_score * 0.45)

        richness = min(1.0, category_count / target)
        return round(richness * max_score)
