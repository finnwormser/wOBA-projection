import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="Rookie rOBA App", layout="wide")

@st.cache_data
def load():
    df = pd.read_csv("test_results.csv")
    df["residual"] = df["Rookie_rOBA_pred"] - df["Rookie_rOBA"]
    return df

df = load()
tab1, tab2 = st.tabs(["Overview", "Results"])

with tab1:
    st.title("MLB Rookie rOBA Prediction")

    st.markdown(
        """
### Introduction
This project aims to predict rOBA values for MLB hitters in their rookie season, based on their minor-league statistics. rOBA is a composite statistic which tries to distill a hitter's value into a single metric. Based on our literature review, we followed two methods: a Bayesian regression model implemented in R through the brms package, and an MLP implemented manually in Python. The dataset we used was collected from baseball-reference.com using the scraping code in scraping.py.

### Data Processing
To handle different quantities of data for each player, we computed a weighted average of a players' minor league seasons where each previous season was weighted half as much as the following, until the player reached the MLB level. We then converted all counting statistics to a rate basis, and recomputed them based on time played.

### Bayesian Regression (bayesian_demo.R)
After testing out different hyperparameters, our final Bayesian model used the default prior and a Gaussian likelihood for rOBA. We trained 4 chains of 2500 iterations each, with 450 discarded as burn-in.

### MLP (MLP.ipynb)
Our final MLP used a single hidden layer of 7 nodes, activated via the ReLU function. We trained this model for 10,000 epochs at a learning rate of η = 0.01.

### Results and Conclusion
The Bayesian model produced far more conservative predictions than the MLP, typically predicting very close to the mean. Thanks to this, it significantly outperformed the MLP, which was especially notable in some outlier cases. However, neither model was effective, both scoring worse than the naive baseline for this problem. This suggests that the models failed to capture some relationship, either due to lack of data or the simplifications we made when computing weighted averages.

Bayesian regression: RMSE: .038, R²: .148  
MLP: RMSE: .1065, R²: -5.51
        """
    )

with tab2:
    st.header("Bayesian Test Predictions")

    rmse = np.sqrt(((df["Rookie_rOBA"] - df["Rookie_rOBA_pred"]) ** 2).mean())
    corr = df["Rookie_rOBA"].corr(df["Rookie_rOBA_pred"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Players", len(df))
    c2.metric("RMSE", f"{rmse:.4f}")
    c3.metric("Correlation", f"{corr:.3f}")

    rmin, rmax = float(df["Rookie_rOBA"].min()), float(df["Rookie_rOBA"].max())

    r_range = st.slider(
        "Actual rOBA range",
        min_value=round(rmin, 3),
        max_value=round(rmax, 3),
        value=(round(rmin, 3), round(rmax, 3)),
        step=0.001,
    )

    max_resid = st.slider(
        "Max |residual|",
        min_value=0.0,
        max_value=float(abs(df["residual"]).max()),
        value=float(abs(df["residual"]).max()),
        step=0.005,
    )

    name = st.text_input("Search name or ID")

    f = df[
        (df["Rookie_rOBA"] >= r_range[0])
        & (df["Rookie_rOBA"] <= r_range[1])
        & (abs(df["residual"]) <= max_resid)
    ]

    if name.strip():
        s = name.lower().strip()
        f = f[
            f["PlayerID"].str.lower().str.contains(s)
            | f["fullName"].str.lower().str.contains(s)
        ]

    base = alt.Chart(f).encode(
        x=alt.X("Rookie_rOBA", title="Actual"),
        y=alt.Y("Rookie_rOBA_pred", title="Predicted"),
        tooltip=[
            "PlayerID",
            "fullName",
            alt.Tooltip("Rookie_rOBA", format=".3f"),
            alt.Tooltip("Rookie_rOBA_pred", format=".3f"),
            alt.Tooltip("low_rOBA_pred", format=".3f"),
            alt.Tooltip("high_rOBA_pred", format=".3f"),
            alt.Tooltip("residual", format=".3f"),
        ],
    )

    pts = base.mark_point().interactive()
    bars = alt.Chart(f).mark_rule(opacity=0.2).encode(
        x="Rookie_rOBA",
        y="low_rOBA_pred",
        y2="high_rOBA_pred",
    )

    line = alt.Chart(
        pd.DataFrame({"x": [rmin, rmax], "y": [rmin, rmax]})
    ).mark_line(strokeDash=[4, 4], color="red").encode(x="x", y="y")

    chart = (bars + pts + line).properties(width=700, height=500)
    st.altair_chart(chart, use_container_width=True)

    st.dataframe(
        f[
            [
                "PlayerID",
                "fullName",
                "Rookie_rOBA",
                "Rookie_rOBA_pred",
                "low_rOBA_pred",
                "high_rOBA_pred",
                "residual",
            ]
        ].sort_values("Rookie_rOBA", ascending=False),
        use_container_width=True,
    )

