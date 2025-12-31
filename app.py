import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Production Dashboard", layout="wide")

DATA_FILE = "production_data.xlsx"
DATA_SHEET = "production_data"
TARGET_SHEET = "targets"

KPIS = ["Production_tons", "Defects_count", "Scrap_tons", "Delay_minutes"]

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file, sheet_name=DATA_SHEET)
    targets = pd.read_excel(file, sheet_name=TARGET_SHEET)
    df["Date"] = pd.to_datetime(df["Date"])
    return df, targets

def target_map(targets_df):
    return dict(zip(targets_df["KPI"], zip(targets_df["Target"], targets_df["Direction"])))

# fallback functions
def achievement(actual, target, direction):
    if direction == "higher_better":
        return (actual / target) * 100
    return (target / actual) * 100 if actual != 0 else 100

def rag(actual, target, direction):
    if direction == "higher_better":
        if actual >= target: return "🟢 Green"
        if actual >= 0.95 * target: return "🟠 Amber"
        return "🔴 Red"
    else:
        if actual <= target: return "🟢 Green"
        if actual <= 1.10 * target: return "🟠 Amber"
        return "🔴 Red"

def add_periods(df):
    df = df.copy()
    df["Week"] = df["Date"].dt.to_period("W").astype(str)
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Year"] = df["Date"].dt.year
    return df

def ensure_kpi_columns(df, tmap):
    """ Variance/Achievement/RAG"""
    out = df.copy()
    for kpi in KPIS:
        target, direction = tmap[kpi]

        if f"{kpi}_Variance" not in out.columns:
            out[f"{kpi}_Variance"] = out[kpi] - target

        if f"{kpi}_Achievement_%" not in out.columns:
            out[f"{kpi}_Achievement_%"] = out[kpi].apply(
                lambda a: round(achievement(a, target, direction), 1)
            )

        if f"{kpi}_RAG" not in out.columns:
            out[f"{kpi}_RAG"] = out[kpi].apply(
                lambda a: rag(a, target, direction)
            )
    return out

def aggregate(df, period_col):
    return df.groupby(period_col).agg(
        Production_tons=("Production_tons","sum"),
        Defects_count=("Defects_count","sum"),
        Scrap_tons=("Scrap_tons","sum"),
        Delay_minutes=("Delay_minutes","sum"),
        Days=("Date","nunique")
    ).reset_index()

# -------- UI --------
st.sidebar.title("Controls")
uploaded = st.sidebar.file_uploader("Upload Excel (optional)", type=["xlsx"])

if uploaded:
    df, targets = load_excel(uploaded)
else:
    df, targets = load_excel(DATA_FILE)

tmap = target_map(targets)
df = add_periods(df)
df = ensure_kpi_columns(df, tmap)

view = st.sidebar.selectbox("View", ["Daily", "Weekly", "Monthly", "Yearly"])

min_d = df["Date"].min().date()
max_d = df["Date"].max().date()
start, end = st.sidebar.date_input("Date range", (min_d, max_d))

dff = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)].copy()

st.title("Production Performance Dashboard")

# For Daily View
if view == "Daily":
    st.subheader("Daily View (Reads KPI from Excel)")

    st.dataframe(
        dff.sort_values("Date"),
        use_container_width=True,
        hide_index=True
    )

    fig = px.line(dff, x="Date", y="Production_tons", title="Daily Production")
    st.plotly_chart(fig, use_container_width=True)

# Weekly / Monthly / Yearly Viws
else:
    period_col = {"Weekly":"Week","Monthly":"Month","Yearly":"Year"}[view]
    agg = aggregate(dff, period_col)

    st.subheader(f"{view} View")

    fig1 = px.bar(agg, x=period_col, y="Production_tons", title=f"{view} Production")
    st.plotly_chart(fig1, use_container_width=True)

    st.dataframe(agg, use_container_width=True, hide_index=True)