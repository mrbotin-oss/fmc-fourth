"""
CONFIGURATION - Makati 15-Minute Observatory
==============================================

This module defines:
- LENSES: The 6 daily-life functions with their properties
- ACCESS_SCORE_RULES: Target thresholds per lens per time band
- VERDICT_THRESHOLDS: Verdict classification rules
- SCORE_WEIGHTS: How components combine into scores
- FUNCTION_WEIGHTS: How functions combine into overall score
- COLOR_TONE: Color mapping for verdict tones
- NARRATIVE_TEMPLATES: Text templates for verdicts
- PRESET_NEIGHBORHOODS: Pre-defined Makati locations

Author: Marita R. Botin
"""

from typing import Dict, Tuple


# ============================================================================
# SIX DAILY-LIFE FUNCTIONS (Lenses)
# ============================================================================

LENSES: Dict[str, Dict] = {
    "living": {
        "label": "Living",
        "color": "#8b5cf6",
        "soft_color": "#ede9fe",
        "methodology": "Urban density, transit, housing access",
        "description": (
            "Residential fit: access to high-quality housing in safe, "
            "dense neighborhoods with good transit connectivity."
        ),
        "osm_categories": ["transit_station", "residential_area", "park"],
        "place_types": ["rail_station", "bus_station"],
    },
    "working": {
        "label": "Working",
        "color": "#ef4444",
        "soft_color": "#fee2e2",
        "methodology": "Work & civic opportunities",
        "description": (
            "Opportunities to work close to home in local businesses, "
            "co-working spaces, offices, or government agencies."
        ),
        "osm_categories": ["office", "commercial", "government"],
        "place_types": ["office", "government_office", "bank", "coworking"],
    },
    "supplying": {
        "label": "Supplying",
        "color": "#14b8a6",
        "soft_color": "#ccfbf1",
        "methodology": "Daily shopping & errands",
        "description": (
            "Proximity to shops, supermarkets, markets, and local services "
            "for daily needs: food, bakery, post office, etc."
        ),
        "osm_categories": ["shop", "market", "supermarket"],
        "place_types": [
            "supermarket", "grocery_store", "bakery", "market",
            "public_market", "convenience_store", "pharmacy"
        ],
    },
    "caring": {
        "label": "Caring",
        "color": "#f59e0b",
        "soft_color": "#fed7aa",
        "methodology": "Health & care access",
        "description": (
            "Easy access to healthcare, pharmacies, clinics, hospitals, "
            "fitness facilities, and wellbeing services."
        ),
        "osm_categories": ["healthcare", "medical"],
        "place_types": [
            "hospital", "clinic", "pharmacy", "dentist",
            "health_center", "gymnasium", "fitness_center"
        ],
    },
    "learning": {
        "label": "Learning",
        "color": "#3b82f6",
        "soft_color": "#dbeafe",
        "methodology": "Educational facilities",
        "description": (
            "Proximity to schools, daycare, libraries, and educational "
            "centers for lifelong learning."
        ),
        "osm_categories": ["education", "school"],
        "place_types": [
            "elementary_school", "high_school", "daycare",
            "library", "university", "vocational_school"
        ],
    },
    "enjoying": {
        "label": "Enjoying",
        "color": "#22c55e",
        "soft_color": "#dcfce7",
        "methodology": "Culture, leisure & public space",
        "description": (
            "Access to culture, leisure, entertainment, and public spaces: "
            "parks, cafes, restaurants, sports facilities, museums."
        ),
        "osm_categories": ["leisure", "recreation", "culture", "food"],
        "place_types": [
            "park", "playground", "sports_center", "swimming_pool",
            "basketball_court", "restaurant", "cafe", "movie_theater",
            "bar", "mall", "museum", "church"
        ],
    },
}


# ============================================================================
# SCORING RULES (per lens, per time band)
# ============================================================================

ACCESS_SCORE_RULES: Dict[str, Dict[str, int]] = {
    "living": {
        "target_5_min": 2,
        "target_10_min": 3,
        "target_15_min": 6,
        "diversity_target": 3,
    },
    "working": {
        "target_5_min": 1,
        "target_10_min": 2,
        "target_15_min": 5,
        "diversity_target": 3,
    },
    "supplying": {
        "target_5_min": 3,
        "target_10_min": 6,
        "target_15_min": 10,
        "diversity_target": 4,
    },
    "caring": {
        "target_5_min": 1,
        "target_10_min": 2,
        "target_15_min": 4,
        "diversity_target": 2,
    },
    "learning": {
        "target_5_min": 1,
        "target_10_min": 2,
        "target_15_min": 3,
        "diversity_target": 2,
    },
    "enjoying": {
        "target_5_min": 2,
        "target_10_min": 4,
        "target_15_min": 8,
        "diversity_target": 4,
    },
}


# ============================================================================
# VERDICT RULES
# ============================================================================

VERDICT_THRESHOLDS: Dict[str, Dict[str, int]] = {
    "good": {
        "min_functions_ready": 6,
        "min_transit_score": 68,
        "min_overall_score": 68,
    },
    "close": {
        "min_functions_ready": 5,
        "min_transit_score": 46,
        "min_overall_score": 55,
    },
    "bad": {},
}

# Function must score >= this to count as "ready"
FUNCTION_READY_THRESHOLD: int = 60


# ============================================================================
# SCORING FORMULA COMPONENTS
# ============================================================================

SCORE_WEIGHTS: Dict[str, int] = {
    "proximity_bonus": 30,          # Extra if minute <= 5
    "band_5_min": 16,              # How much 5-min count contributes
    "band_10_min": 14,             # How much 10-min count contributes
    "band_15_min": 10,             # How much 15-min count contributes
    "diversity": 26,               # How much category variety contributes
}

# How FunctionScore is weighted into overall
FUNCTION_WEIGHTS: Dict[str, float] = {
    "living": 0.22,
    "working": 0.16,
    "supplying": 0.18,
    "caring": 0.14,
    "learning": 0.12,
    "enjoying": 0.18,
}


# ============================================================================
# UI COLORS & STYLING
# ============================================================================

COLOR_TONE: Dict[str, str] = {
    "good": "#0f766e",
    "close": "#b45309",
    "bad": "#b91c1c",
}


# ============================================================================
# NARRATIVE TEMPLATES
# ============================================================================

NARRATIVE_TEMPLATE_GOOD: str = (
    "{mode} access supports all six ETI social functions here, with transit "
    "acting as a strong enabler and an overall score of {score}/100."
)

NARRATIVE_TEMPLATE_CLOSE: str = (
    "The neighbourhood is almost complete by {mode}. The main gaps are around "
    "{missing}, while the rest of the six social functions are already "
    "performing with good balance."
)

NARRATIVE_TEMPLATE_BAD: str = (
    "Daily life is still fragmented here by {mode}. The weakest function is "
    "{weakest}, and the missing balance is most visible around {missing}."
)


# ============================================================================
# RING VERDICT RULES
# ============================================================================

def get_ring_verdict(minutes: int, functions_ready: int) -> Tuple[str, str]:
    """
    Determine verdict badge for each ring (5/10/15 min).
    
    Args:
        minutes: Time band (5, 10, or 15)
        functions_ready: Count of ready functions
    
    Returns:
        Tuple of (tone, label)
    """
    target = 3 if minutes == 5 else 4 if minutes == 10 else 6
    
    if functions_ready >= target:
        return ("good", "Accomplishes")
    elif functions_ready == target - 1:
        return ("close", "Almost")
    else:
        return ("bad", "Not yet")


# ============================================================================
# PRESETS
# ============================================================================

PRESET_NEIGHBORHOODS: Dict[str, Dict] = {
    "Makati City Center": {
        "coords": (121.0186, 14.5794),
        "description": "Heart of Makati's commercial district",
    },
    "BGC": {
        "coords": (121.0339, 14.5591),
        "description": "Bonifacio Global City (modern development)",
    },
    "San Lorenzo": {
        "coords": (121.0269, 14.5694),
        "description": "Upper-class residential village",
    },
    "Salcedo": {
        "coords": (121.0265, 14.5722),
        "description": "Historic village (tourism, heritage)",
    },
    "Dasmarinas": {
        "coords": (121.0102, 14.5615),
        "description": "Residential and commercial mix",
    },
}
