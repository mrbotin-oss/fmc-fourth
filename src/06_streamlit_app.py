"""
STREAMLIT WEB APP - Makati 15-Minute Observatory
=================================================

Interactive Streamlit web application for 15-minute city assessment.

This module implements the UI layer using Streamlit, Folium, and the
core analysis modules.

Features:
    - Interactive map with click-to-assess
    - Sidebar controls (mode toggle, presets)
    - Real-time assessment results
    - Function score cards
    - Ring readiness visualization
    - Responsive 2-column layout

Author: Marita R. Botin
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict, Tuple

from data_models import Assessment, VerdictTone
from config import LENSES, PRESET_NEIGHBORHOODS, COLOR_TONE
from analyzer import SixFunctionAnalyzer
from verdict_builder import VerdictBuilder
from data_loader import load_sample_data, create_test_isochrones


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Makati 15-Minute Observatory",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# STREAMLIT SESSION STATE INITIALIZATION
# ============================================================================

if "current_assessment" not in st.session_state:
    st.session_state.current_assessment = None

if "selected_point" not in st.session_state:
    st.session_state.selected_point = PRESET_NEIGHBORHOODS["Makati City Center"]["coords"]

if "travel_mode" not in st.session_state:
    st.session_state.travel_mode = "walking"

if "active_lens" not in st.session_state:
    st.session_state.active_lens = "all"


# ============================================================================
# CACHED DATA LOADERS
# ============================================================================

@st.cache_resource
def get_analyzers() -> Dict:
    """Get analyzer instances (cached for performance)."""
    return {
        "function_analyzer": SixFunctionAnalyzer(),
        "verdict_builder": VerdictBuilder(),
    }


@st.cache_resource
def get_sample_data() -> Dict:
    """Load sample data (cached)."""
    return load_sample_data()


# ============================================================================
# ASSESSMENT FUNCTIONS
# ============================================================================

def run_assessment(
    center: Tuple[float, float], mode: str
) -> Optional[Assessment]:
    """
    Run full assessment pipeline.
    
    Args:
        center: (lng, lat)
        mode: "walking" or "cycling"
    
    Returns:
        Assessment object or None if error
    """
    try:
        # Load data
        data = get_sample_data()
        places_gdf = data["places"]
        
        # Get analyzers
        analyzers = get_analyzers()
        func_analyzer = analyzers["function_analyzer"]
        verdict_builder = analyzers["verdict_builder"]
        
        # Create isochrones
        isochrones = create_test_isochrones(center)
        
        # Analyze functions
        access_by_function = func_analyzer.analyze_catchment(
            isochrones, places_gdf
        )
        
        # Build verdict
        assessment = verdict_builder.build_assessment(
            center=center,
            access_by_function=access_by_function,
            travel_mode=mode,
            iso_source="fallback",
            place_name="Assessment Point",
        )
        
        return assessment
    
    except Exception as e:
        st.error(f"❌ Assessment failed: {e}")
        return None


def build_map(
    center: Tuple[float, float],
    assessment: Optional[Assessment]
) -> folium.Map:
    """
    Build Folium map with isochrones and POIs.
    
    Args:
        center: (lng, lat)
        assessment: Assessment object (if available)
    
    Returns:
        Folium Map object
    """
    m = folium.Map(
        location=[center[1], center[0]],  # folium uses (lat, lng)
        zoom_start=14,
        tiles="OpenStreetMap",
    )
    
    # Center marker
    folium.Marker(
        location=[center[1], center[0]],
        popup="📍 Selected Point",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)
    
    # Isochrone rings (if assessment exists)
    if assessment:
        colors = {5: "green", 10: "orange", 15: "red"}
        labels = {5: "5-minute walk", 10: "10-minute walk", 15: "15-minute walk"}
        
        for minutes, polygon in assessment.isochrones.items():
            if polygon:
                folium.GeoJson(
                    polygon.__geo_interface__,
                    style_function=lambda x, c=colors.get(minutes, "gray"): {
                        "fillColor": c,
                        "color": c,
                        "fillOpacity": 0.15,
                        "weight": 2,
                    },
                    tooltip=labels.get(minutes, f"{minutes} minute"),
                ).add_to(m)
    
    return m


# ============================================================================
# SIDEBAR: HERO CARD & CONTROLS
# ============================================================================

with st.sidebar:
    st.markdown(
        """
        # 🗺️ Makati 15-Minute Observatory
        
        **A practical interpretation of the 15-minute city framework 
        for Makati, Philippines.**
        
        - 📍 Click a point on the map or select a preset
        - 🚶 Choose walking or cycling mode
        - 📊 Explore 6 daily-life functions
        - 💡 See the verdict: ready, almost, or not yet
        """
    )
    
    st.divider()
    
    # Mode toggle
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("🚶 Walking", key="walk_btn", use_container_width=True):
            st.session_state.travel_mode = "walking"
    with col_m2:
        if st.button("🚴 Cycling", key="bike_btn", use_container_width=True):
            st.session_state.travel_mode = "cycling"
    
    st.caption(f"Mode: **{st.session_state.travel_mode.capitalize()}**")
    
    st.divider()
    
    # Preset locations
    st.markdown("### Jump to...")
    preset_names = list(PRESET_NEIGHBORHOODS.keys())
    selected_preset = st.selectbox(
        "Choose a neighborhood",
        preset_names,
        label_visibility="collapsed"
    )
    
    if selected_preset:
        st.session_state.selected_point = PRESET_NEIGHBORHOODS[selected_preset]["coords"]


# ============================================================================
# TRIGGER ASSESSMENT
# ============================================================================

assessment = run_assessment(st.session_state.selected_point, st.session_state.travel_mode)
if assessment:
    st.session_state.current_assessment = assessment

current_assessment = st.session_state.current_assessment


# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

st.markdown("# 🗺️ Makati 15-Minute Observatory")
st.markdown("*Assess urban walkability and 15-minute city readiness*")

# Two-column layout
col_left, col_right = st.columns([1, 1.3], gap="medium")

# ============================================================================
# LEFT COLUMN: VERDICT & RESULTS
# ============================================================================

with col_left:
    if current_assessment:
        # Verdict badge
        tone = current_assessment.verdict_tone.value
        tone_color = COLOR_TONE.get(tone, "#999")
        
        verdict_labels = {
            VerdictTone.GOOD: "✓ Accomplishes",
            VerdictTone.CLOSE: "≈ Almost there",
            VerdictTone.BAD: "✗ Not yet",
        }
        verdict_text = verdict_labels.get(current_assessment.verdict_tone, "Unknown")
        
        st.markdown(f"## {verdict_text}")
        
        # Scores
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Overall", f"{current_assessment.overall_score}/100")
        with col_s2:
            st.metric("Ready", f"{current_assessment.ready_count}/6")
        with col_s3:
            st.metric("Transit", f"{current_assessment.transit_score}/100")
        
        # Narrative
        st.info(f"**Summary:** {current_assessment.narrative}")
        
        st.divider()
        
        # Rings readiness
        st.subheader("🎯 Readiness by Ring")
        for minutes in [5, 10, 15]:
            ready = current_assessment.rings_ready.get(minutes, 0)
            st.progress(ready / 6, text=f"{minutes} min: {ready}/6 functions")
        
        st.divider()
        
        # Function cards
        st.subheader("📊 Six Social Functions")
        for i, fs in enumerate(current_assessment.function_scores, 1):
            tone_emoji = {
                VerdictTone.GOOD: "🟢",
                VerdictTone.CLOSE: "🟡",
                VerdictTone.BAD: "🔴",
            }.get(fs.tone, "⚪")
            
            with st.expander(
                f"{tone_emoji} **{fs.label}** - Score: {fs.score}/100",
                expanded=(i == 1)
            ):
                st.write(fs.detail)
                st.caption(" | ".join(fs.evidence))
    else:
        st.warning("⚠️ No assessment data available. Click the map to begin.")


# ============================================================================
# RIGHT COLUMN: MAP
# ============================================================================

with col_right:
    st.subheader("🗺️ Interactive Map")
    
    # Build map
    m = build_map(st.session_state.selected_point, current_assessment)
    
    # Display and capture interaction
    map_data = st_folium(m, width=700, height=600)
    
    # Handle map clicks
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        st.session_state.selected_point = (clicked["lng"], clicked["lat"])
        st.rerun()


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown(
    """
    ---
    **Makati 15-Minute Observatory**  
    Student Project by Marita R. Botin  
    GmE 221 & GmE 205 | Geomatics Engineering Program  
    Mapua University, Manila
    
    *Data sources: OpenStreetMap, Overture Maps, Makati Open Data, Mapbox Isochrone API*
    """
)
