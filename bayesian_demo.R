library(dplyr)
library(tidyr)
library(caret)
library(brms)
library(ggplot2)
library(ggrepel)
library(baseballr)

# load data
minors <- read.csv("../Project/ds4420_minors_stats.csv")

# remove amateur levels
minors <- minors %>%
  filter(!Lev %in% c("Fal", "NCAA", "Summ", "Ind", "Smr", "Fgn", "WRk"))

# get one stat-line for each season (regardless of number of teams played for)
num_stats <- colnames(minors)[c(8:30)]
minors_aggregated <- minors %>%
  group_by(PlayerID, Year) %>%
  summarize(
    Age = max(Age), 
    Rookie_Season = max(Rookie_Season), 
    Rookie_rOBA = max(Rookie_rOBA), 
    across(all_of(num_stats), ~ {sum(.x)})
  )

# get a weighted average for each player using each season worth of data
minors_weighted <- minors_aggregated %>%
  mutate(
    Year_Weight = 0.5^(Rookie_Season - Year - 1),   # more recent seasons are weighted heavier
    Rookie_Age = Age - Year + Rookie_Season   # calculate age when a rookie
  ) %>%
  group_by(PlayerID) %>%
  summarize(
    Rookie_Season = max(Rookie_Season), 
    Rookie_Age = max(Rookie_Age), 
    Rookie_rOBA = max(Rookie_rOBA), 
    across(all_of(num_stats), ~{weighted.mean(.x, Year_Weight)})  # calculate weighed mean
  ) %>%
  mutate( # calculate rate stats
    BA = H/AB, OBP = (H+BB+HBP)/(AB+BB+HBP+SF), SLG = TB/AB, X2B_rate = X2B/PA, X3B_rate = X3B/PA, 
    HR_rate = HR/PA, BB_rate = BB/PA, SO_rate = SO/PA, HBP_rate = HBP/PA, SF_rate = SF/PA, 
    IBB_rate = IBB/PA
  ) %>%
  select( # select rate stats and necessary bio information
    PlayerID, Rookie_Season, Rookie_rOBA, Rookie_Age, BA, OBP, SLG, X2B_rate, X3B_rate, HR_rate, BB_rate, SO_rate, HBP_rate, 
    SF_rate, IBB_rate
  ) %>%
  filter(rowSums(is.na(.))==0) %>%   # remove rows with missing data
  ungroup()

# split data into validation (2025 rookies) and modeling (pre-2025 rookies) sets
validation_df <- minors_weighted %>% filter(Rookie_Season == 2025)
modeling_df <- minors_weighted %>% filter(Rookie_Season < 2025)

# get train/test splits of modeling data
train_idx <- sample(seq(nrow(modeling_df)), nrow(modeling_df) * 0.8)
train_df <- modeling_df[train_idx,]
test_df <- modeling_df[-train_idx,]

# scale training data
train_df_scaled <- train_df
train_df_scaled[,-c(1:3)] <- scale(train_df[,-c(1:3)])

# scale testing data
test_df_scaled <- test_df
for (col in colnames(test_df)[4:15]) {
  test_df_scaled[[col]] <- (test_df[[col]] - mean(train_df[[col]])) / sd(train_df[[col]])
}

# use default prior (amount of data makes any prior choice pretty useless)
prior <- default_prior(Rookie_rOBA ~ .,
                       data = train_df_scaled[,-c(1:2)],
                       family = gaussian())

# fit model
stats_brm <- brm(Rookie_rOBA ~ .,
                 family = gaussian(), 
                 data = train_df_scaled[,-c(1:2)],
                 chains = 4, 
                 cores = getOption("mc.cores", 1), 
                 iter = 2500, 
                 warmup = 450, 
                 thin = 1, 
                 prior = prior)

# show coefficients
summary(stats_brm)

### TEST DATA ###

# calcualte R-squared for test data 
bayes_R2(stats_brm, newdata=test_df_scaled)

# extract predictions for test data
test_preds <- posterior_predict(stats_brm, newdata=test_df_scaled)

# calculate and print the RMSE
rmse <- sqrt(mean((test_df_scaled$Rookie_rOBA - colMeans(test_preds))^2))
naive_rmse <- sqrt(mean((matrix(mean(train_df$Rookie_rOBA), nrow=333, ncol=1) - colMeans(test_preds))^2))
cat("Test RMSE:", round(rmse, 4))
cat("Naïve RMSE:", round(naive_rmse, 4))

# put together actual rOBA values, predicted rOBA values, and both high- and low-predictions
test_results <- data.frame(
  PlayerID = test_df_scaled$PlayerID, 
  Rookie_rOBA = test_df_scaled$Rookie_rOBA,
  Rookie_rOBA_pred = colMeans(test_preds), 
  high_rOBA_pred = apply(test_preds, 2, quantile, 0.975),
  low_rOBA_pred = apply(test_preds, 2, quantile, 0.025)
)

# plot actual-predicted difference and include error bars
test_results %>%
  ggplot(aes(x = Rookie_rOBA, y = Rookie_rOBA_pred)) +
  geom_point() +
  geom_errorbar(aes(ymin = low_rOBA_pred, ymax = high_rOBA_pred), width = 0, alpha=0.15) +
  geom_abline(intercept = 0, slope = 1, linetype = "dashed", color='red', linewidth=1) +
  theme_minimal() +
  ylim(0.15, 0.5) + 
  labs(
    x = "Rookie rOBA",
    y = "Predicted Rookie rOBA",
    title = "Actual vs. Predicted rOBA (with 95% Confidence Intervals)"
  )

### VALIDATION DATA ###

# scale validation data
validation_df_scaled <- validation_df
for (col in colnames(validation_df)[4:15]) {
  validation_df_scaled[[col]] <- (validation_df[[col]] - mean(train_df[[col]])) / sd(train_df[[col]])
}

# extract predictions for validation data
validation_preds <- posterior_predict(stats_brm, newdata=validation_df_scaled)

# put together actual rOBA values, predicted rOBA values, and both high- and low-predictions
validation_results <- data.frame(
  PlayerID = validation_df_scaled$PlayerID, 
  Rookie_rOBA = validation_df_scaled$Rookie_rOBA,
  Rookie_rOBA_pred = colMeans(validation_preds), 
  high_rOBA_pred = apply(validation_preds, 2, quantile, 0.975),
  low_rOBA_pred = apply(validation_preds, 2, quantile, 0.025)
)

# get lookup table for player IDs
chadwick_lu <- chadwick_player_lu()
chadwick_lu <- chadwick_lu %>% mutate(fullName = paste(name_first, name_last))

# plot actual-predicted difference and include player labels
validation_results %>%
  left_join(chadwick_lu, by=c("PlayerID" = "key_bbref")) %>%
  ggplot(aes(x = Rookie_rOBA, y = Rookie_rOBA_pred, label=fullName)) +
  geom_point() +
  geom_text_repel(size = 3, max.overlaps = Inf) +
  geom_errorbar(aes(ymin = low_rOBA_pred, ymax = high_rOBA_pred), width = 0, alpha=0.15) +
  geom_abline(intercept = 0, slope = 1, linetype = "dashed", color='red', linewidth=1) +
  theme_minimal() +
  xlim(0.225, 0.425) +
  ylim(0.275, 0.375) + 
  labs(
    x = "Rookie rOBA",
    y = "Predicted Rookie rOBA",
    title = "Actual vs. Predicted rOBA (2025 Rookies)"
  )


