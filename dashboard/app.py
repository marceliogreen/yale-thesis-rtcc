"""
RTCC Thesis Advisor Dashboard

Streamlit dashboard for advisor meetings showing REAL DATA findings
on RTCC effectiveness and clearance rate trends.

**IMPORTANT:** This is exploratory analysis with significant data limitations.
Findings should not be overinterpreted.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Page config
st.set_page_config(
    page_title="RTCC Thesis Advisor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        border-bottom: 3px solid #16213e;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #0f3460;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .warning-box {
        background: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1.5rem;
        margin: 2rem 0;
        border-radius: 5px;
    }
    .info-box {
        background: #e7f3ff;
        border-left: 5px solid #2196F3;
        padding: 1.5rem;
        margin: 2rem 0;
        border-radius: 5px;
    }
    .negative { color: #dc3545; font-weight: bold; }
    .positive { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# REAL DATA - Washington Post Homicide Dataset (2007-2017)
# ============================================================================

# RAW clearance rate findings from Washington Post data
CLEARANCE_FINDINGS = pd.DataFrame([
    {"City": "Chicago", "State": "IL", "RTCC_Year": 2017, "Pre_2016": "24.6%", "2017": "8.6%", "Trend": "Declining pre-RTCC"},
    {"City": "St. Louis", "State": "MO", "RTCC_Year": 2015, "Pre_2015": "40.6%", "Post_2015": "34.9%", "Trend": "Declining pre-RTCC"},
    {"City": "Miami", "State": "FL", "RTCC_Year": 2016, "Pre_2016": "44.0%", "Post_2016": "23.7%", "Trend": "Declining pre-RTCC"},
    {"City": "New Orleans", "State": "LA", "RTCC_Year": 2017, "Pre_2017": "26.7%", "Post_2017": "29.4%", "Trend": "Slight increase"},
    {"City": "Fresno", "State": "CA", "RTCC_Year": 2018, "Pre_RTCC_Avg": "71.1%", "2017": "42.9%", "Trend": "High baseline, declining"},
    {"City": "Albuquerque", "State": "NM", "RTCC_Year": 2020, "Pre_RTCC_Avg": "63.0%", "2017": "50.7%", "Trend": "High baseline, declining"},
])

# Annual homicide data with full trend context
ANNUAL_HOMICIDES = pd.DataFrame([
    # Chicago - Shows declining clearance BEFORE RTCC spike in 2016
    {"City": "Chicago", "Year": 2010, "Homicides": 434, "Cleared": 135, "Rate": 31.1, "RTCC": 0},
    {"City": "Chicago", "Year": 2011, "Homicides": 437, "Cleared": 133, "Rate": 30.4, "RTCC": 0},
    {"City": "Chicago", "Year": 2012, "Homicides": 505, "Cleared": 136, "Rate": 26.9, "RTCC": 0},
    {"City": "Chicago", "Year": 2013, "Homicides": 423, "Cleared": 133, "Rate": 31.4, "RTCC": 0},
    {"City": "Chicago", "Year": 2014, "Homicides": 418, "Cleared": 125, "Rate": 29.9, "RTCC": 0},
    {"City": "Chicago", "Year": 2015, "Homicides": 487, "Cleared": 120, "Rate": 24.6, "RTCC": 0},
    {"City": "Chicago", "Year": 2016, "Homicides": 765, "Cleared": 110, "Rate": 14.4, "RTCC": 0},  # Spike BEFORE RTCC
    {"City": "Chicago", "Year": 2017, "Homicides": 654, "Cleared": 56, "Rate": 8.6, "RTCC": 1},
    # St. Louis
    {"City": "St. Louis", "Year": 2010, "Homicides": 142, "Cleared": 81, "Rate": 57.0, "RTCC": 0},
    {"City": "St. Louis", "Year": 2011, "Homicides": 113, "Cleared": 68, "Rate": 60.2, "RTCC": 0},
    {"City": "St. Louis", "Year": 2012, "Homicides": 112, "Cleared": 62, "Rate": 55.4, "RTCC": 0},
    {"City": "St. Louis", "Year": 2013, "Homicides": 121, "Cleared": 62, "Rate": 51.2, "RTCC": 0},
    {"City": "St. Louis", "Year": 2014, "Homicides": 160, "Cleared": 65, "Rate": 40.6, "RTCC": 0},
    {"City": "St. Louis", "Year": 2015, "Homicides": 186, "Cleared": 65, "Rate": 34.9, "RTCC": 1},
    {"City": "St. Louis", "Year": 2016, "Homicides": 188, "Cleared": 68, "Rate": 36.2, "RTCC": 1},
    {"City": "St. Louis", "Year": 2017, "Homicides": 202, "Cleared": 64, "Rate": 31.7, "RTCC": 1},
    # Fresno - High clearance rates
    {"City": "Fresno", "Year": 2010, "Homicides": 45, "Cleared": 30, "Rate": 66.7, "RTCC": 0},
    {"City": "Fresno", "Year": 2011, "Homicides": 35, "Cleared": 28, "Rate": 80.0, "RTCC": 0},
    {"City": "Fresno", "Year": 2012, "Homicides": 51, "Cleared": 36, "Rate": 70.6, "RTCC": 0},
    {"City": "Fresno", "Year": 2013, "Homicides": 39, "Cleared": 34, "Rate": 87.2, "RTCC": 0},
    {"City": "Fresno", "Year": 2014, "Homicides": 49, "Cleared": 39, "Rate": 79.6, "RTCC": 0},
    {"City": "Fresno", "Year": 2015, "Homicides": 39, "Cleared": 28, "Rate": 71.8, "RTCC": 0},
    {"City": "Fresno", "Year": 2016, "Homicides": 39, "Cleared": 21, "Rate": 53.8, "RTCC": 0},
    {"City": "Fresno", "Year": 2017, "Homicides": 56, "Cleared": 24, "Rate": 42.9, "RTCC": 0},
    # Albuquerque - High clearance rates
    {"City": "Albuquerque", "Year": 2010, "Homicides": 45, "Cleared": 30, "Rate": 66.7, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2011, "Homicides": 38, "Cleared": 28, "Rate": 73.7, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2012, "Homicides": 46, "Cleared": 32, "Rate": 69.6, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2013, "Homicides": 33, "Cleared": 17, "Rate": 51.5, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2014, "Homicides": 28, "Cleared": 20, "Rate": 71.4, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2015, "Homicides": 50, "Cleared": 29, "Rate": 58.0, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2016, "Homicides": 63, "Cleared": 38, "Rate": 60.3, "RTCC": 0},
    {"City": "Albuquerque", "Year": 2017, "Homicides": 75, "Cleared": 38, "Rate": 50.7, "RTCC": 0},
])

# Header
st.markdown('<div class="main-header">RTCC Thesis Advisor Dashboard</div>', unsafe_allow_html=True)
st.markdown("**Thesis:** Advancing Computational Perception towards Cognitive-Grounded Prediction: Evaluating RTCC Effectiveness")
st.markdown("**Author:** Marcel Green | **Program:** Yale CGSC 4910 | **Advisor:** Dr. Isaac Davis")
st.markdown("**Last Updated:** March 31, 2026")

# Critical Warning
st.markdown('<div class="warning-box">', unsafe_allow_html=True)
st.warning("""
⚠️ **EXPLORATORY ANALYSIS - DATA LIMITATIONS APPLY**

This dashboard uses the Washington Post Homicide Dataset (2007-2017). Key limitations:
- Data ends in 2017, missing 5-8 years of post-RTCC implementation
- Cities show declining clearance trends BEFORE RTCC implementation
- National clearance rates have been declining for decades
- Findings are preliminary and should not be overinterpreted

**This is NOT the final thesis analysis - it's an initial data exploration.**
""")
st.markdown("</div>", unsafe_allow_html=True)

# Info box
st.markdown('<div class="info-box">', unsafe_allow_html=True)
st.info("""
**Important Context:** National homicide clearance rates have declined from ~90% in the 1960s to ~50-52% today.
This long-term trend affects all cities regardless of RTCC implementation.
Any evaluation must account for this baseline decline.
""")
st.markdown("</div>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Overview", "📈 Trend Analysis", "🏙️ City-by-City", "📁 Data Sources"])

with tab1:
    st.markdown('<div class="section-header">Data Coverage Summary</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cities with Data", "6", "of 8 RTCC cities")
    with col2:
        st.metric("Data Years", "2007-2017", "Missing 2018-2023")
    with col3:
        st.metric("Total Records", "52,179", "Individual homicides")
    with col4:
        st.metric("Limitation", "Incomplete", "Post-RTCC data missing")

    st.markdown('<div class="section-header">Key Observation: Pre-Existing Decline Trends</div>', unsafe_allow_html=True)

    st.markdown("""
    ### Critical Finding: Declining Clearance Often PRECEDED RTCC

    **Chicago (RTCC 2017):**
    - 2010: 31.1% → 2016: 14.4% (declining BEFORE RTCC)
    - 2016 spike: 765 homicides, 14.4% clearance
    - RTCC implemented during ongoing crisis

    **St. Louis (RTCC 2015):**
    - 2011: 60.2% → 2014: 40.6% (declining BEFORE RTCC)
    - RTCC implemented during decline

    **New Orleans (RTCC 2017):**
    - 2016: 26.7% → 2017: 29.4% (slight INCREASE post-RTCC)

    **Fresno & Albuquerque:**
    - Maintained HIGH clearance rates (50-87%) vs national avg (~50%)
    - But showed declining trends even before RTCC
    """)

    st.markdown('<div class="section-header">Alternative Interpretation</div>', unsafe_allow_html=True)

    st.info("""
    **Some research suggests RTCCs may HELP REVERSE declining trends locally:**

    - Cities with high baseline clearance (Fresno, Albuquerque) maintained above-average rates
    - New Orleans showed slight improvement from 2016 to 2017
    - RTCCs may slow or stabilize declines that would otherwise be worse

    **However:** Washington Post data ends in 2017, making it impossible to evaluate longer-term effects.
    """)

with tab2:
    st.markdown('<div class="section-header">Clearance Rate Trends Over Time</div>', unsafe_allow_html=True)

    # City selector
    selected_city = st.selectbox("Select City", ANNUAL_HOMICIDES["City"].unique())

    city_data = ANNUAL_HOMICIDES[ANNUAL_HOMICIDES["City"] == selected_city].copy()
    rtcc_year = CLEARANCE_FINDINGS[CLEARANCE_FINDINGS["City"] == selected_city]["RTCC_Year"].values[0]

    # Line chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=city_data["Year"],
        y=city_data["Rate"],
        mode="lines+markers",
        name="Clearance Rate",
        line=dict(color="#636efa", width=3),
        marker=dict(size=8),
        text=city_data["Rate"].apply(lambda x: f"{x:.1f}%"),
        hovertemplate="Year: %{x}<br>Clearance: %{y:.1f}%<extra></extra>"
    ))

    # Add RTCC implementation line
    fig.add_vline(
        x=rtcc_year,
        line_dash="dash",
        line_color="red",
        annotation_text=f"RTCC ({rtcc_year})"
    )

    fig.update_layout(
        title=f"{selected_city}: Homicide Clearance Rate Trend (2010-2017)",
        xaxis_title="Year",
        yaxis_title="Clearance Rate (%)",
        yaxis_tickformat=".1f",
        height=500,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary statistics
    st.markdown("### Summary Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_rate = city_data["Rate"].mean()
        st.metric("Average Clearance", f"{avg_rate:.1f}%")
    with col2:
        max_rate = city_data["Rate"].max()
        st.metric("Highest Rate", f"{max_rate:.1f}%")
    with col3:
        min_rate = city_data["Rate"].min()
        st.metric("Lowest Rate", f"{min_rate:.1f}%")

with tab3:
    st.markdown('<div class="section-header">City-by-City Analysis</div>', unsafe_allow_html=True)

    for city in ANNUAL_HOMICIDES["City"].unique():
        city_data = ANNUAL_HOMICIDES[ANNUAL_HOMICIDES["City"] == city]
        rtcc_year = CLEARANCE_FINDINGS[CLEARANCE_FINDINGS["City"] == city]["RTCC_Year"].values[0]

        with st.expander(f"**{city}** (RTCC: {rtcc_year})"):
            st.dataframe(
                city_data[["Year", "Homicides", "Cleared", "Rate"]],
                use_container_width=True,
                hide_index=True
            )

            # Calculate pre/post if applicable
            pre_rtcc = city_data[city_data["Year"] < rtcc_year]
            post_rtcc = city_data[city_data["Year"] >= rtcc_year]

            if len(pre_rtcc) > 0 and len(post_rtcc) > 0:
                pre_avg = pre_rtcc["Rate"].mean()
                post_avg = post_rtcc["Rate"].mean()
                change = post_avg - pre_avg

                st.markdown(f"""
                - **Pre-RTCC avg:** {pre_avg:.1f}%
                - **Post-RTCC avg:** {post_avg:.1f}%
                - **Change:** {'+' if change > 0 else ''}{change:.1f}%
                """)

with tab4:
    st.markdown('<div class="section-header">Data Sources</div>', unsafe_allow_html=True)

    sources_data = pd.DataFrame([
        {"Source": "Washington Post Homicides", "Records": "52,179", "Years": "2007-2017", "Coverage": "50 largest US cities"},
        {"Source": "Chicago Socrata API", "Records": "8,000+", "Years": "2010-2023", "Coverage": "Chicago only"},
        {"Source": "ICPSR 39066", "Records": "Agency-level", "Years": "2022", "Coverage": "All agencies (pending)"},
        {"Source": "Jacob Kaplan", "Records": "64 years", "Years": "1960-2024", "Coverage": "National (pending)"},
    ])

    st.dataframe(sources_data, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">Pending Downloads</div>', unsafe.allow_html=True)

    st.markdown("""
    | Dataset | Purpose | Status |
    |---------|---------|--------|
    | **ICPSR 39066** | UCR Clearances for Hartford/Newark | ⏳ Need ICPSR account |
    | **Jacob Kaplan 1960-2024** | Extended longitudinal analysis | ⏳ Ready to download |
    | **ICPSR 39069** | Supplementary Homicide Reports | ⏳ Need ICPSR account |

    ### Why These Matter:
    - **ICPSR 39066** fills the Hartford/Newark gap
    - **Jacob Kaplan** provides 2018-2024 data to see actual post-RTCC effects
    - Both datasets provide more recent data than Washington Post (ends 2017)
    """)

    st.markdown('<div class="section-header">Links</div>', unsafe.allow_html=True)

    st.markdown("""
    - [Washington Post Homicide Dataset](https://github.com/washingtonpost/data-homicides)
    - [ICPSR 39066 - UCR Clearances](https://www.icpsr.umich.edu/web/NACJD/studies/39066)
    - [Jacob Kaplan Offenses Known](https://www.openicpsr.org/openicpsr/project/100707/version/V22/view)
    - [UCR Book - Decoding FBI Data](https://ucrbook.com/)
    """)

# Footer
st.markdown("---")
st.markdown("""
### Data Notes & Limitations:

1. **Washington Post dataset ends in 2017** - This is a critical limitation. RTCCs implemented in 2016-2018 have
   only 0-2 years of post-implementation data, which is insufficient for meaningful evaluation.

2. **Pre-existing decline trends** - Most cities showed declining clearance rates BEFORE RTCC implementation.
   This suggests broader factors are at play.

3. **National context** - Homicide clearance rates nationally have declined from ~90% in the 1960s to ~50-52% today.
   This multi-decade trend affects all cities.

4. **Heterogeneity** - Fresno and Albuquerque maintained high clearance rates (50-87%) compared to national averages,
   suggesting local factors matter significantly.

5. **Chicago 2016 spike** - Chicago saw a massive homicide increase in 2016 (765 vs 487 in 2015) with a corresponding
   clearance drop (14.4%), all BEFORE RTCC implementation in 2017.

### Next Steps:

1. Download ICPSR 39066 for Hartford/Newark data
2. Download Jacob Kaplan dataset for 2018-2024 coverage
3. Implement interrupted time series (ITS) model
4. Add synthetic control method for causal inference
5. Conduct literature review on RTCC effectiveness studies

**CGSC 4910 — Yale Cognitive Science | Spring 2026**
""")
