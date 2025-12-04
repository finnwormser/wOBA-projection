# wOBA-projection

## Introduction

This project aims to predict rOBA values for MLB hitters in their rookie season, based on their minor-league statistics. rOBA is a composite statistic which tries to distill a hitter's value into a single metric. Based on our literature review, we followed two methods: a Bayesian regression model implemented in R through the **brms** package, and an MLP implemented manually in Python. The dataset we used was collected from **baseball-reference.com**  using the scraping code in `scraping.py`. 

## Data Processing
To handle different quantities of data for each player, we computed a weighted average of a players' minor league seasons where each previous season was weighted half as much as the following, until the player reached the MLB level. We then converted all counting statistics to a rate basis, and recomputed them based on time played.

## Bayesian Regression
After testing out different hyperparameters, our final Bayesian model used the default prior and a Gaussian likelihood for rOBA. We trained 4 chains of 2500 iterations each, with 450 discarded as burn-in.

## MLP
Our final MLP used a single hidden layer of 7 nodes, activated via the ReLU function. We trained this model for 10,000 epochs at a learning rate of η = 0.01.

## Results and Conclusion
The Bayesian model produced far more conservative predictions than the MLP, typically predicting very close to the mean. Thanks to this, it significantly outperformed the MLP, which was especially notable in some outlier cases. However, neither model was effective, both scoring worse than the naive baseline for this problem. This suggests that the models failed to capture some relationship, either due to lack of data or the simplifications we made when computing weighted averages.

Bayesian regression: **RMSE**: .038, **$R^2$**: .148
MLP: **RMSE**: .1065, **$R^2$**: .-5.51