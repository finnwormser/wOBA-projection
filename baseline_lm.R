library(dplyr)
library(tidyr)
library(caret)

minors <- read.csv("../Project/ds4420_minors_stats.csv")

minors <- minors %>%
  filter(!Lev %in% c("Fal", "NCAA", "Summ", "Ind", "Smr", "Fgn", "WRk"))

minors_final_year <- minors %>% 
  group_by(PlayerID) %>%
  filter(Year == max(Year)) %>%
  summarize(Rookie_rOBA = max(Rookie_rOBA), G = sum(G), PA = sum(PA), AB = sum(AB), R = sum(R), 
            H = sum(H), X2B = sum(X2B), X3B = sum(X3B), HR = sum(HR), RBI = sum(RBI), SB = sum(SB), 
            CS = sum(CS), BB = sum(BB), SO = sum(SO), TB = sum(TB), GDP = sum(GDP), HBP = sum(HBP), 
            SH = sum(SH), SF = sum(SF), IBB = sum(IBB)) %>%
  filter(PA > 0) %>%
  mutate(across(where(is.numeric), ~replace_na(., 0))) %>%
  mutate(BA = round(H / AB, 3), 
         OBP = round((H + BB + HBP) / (AB + BB + HBP + SF), 3), 
         SLG = round(TB / AB, 3), 
         OPS = round(OBP + SLG, 3))

minors_final_year_scaled <- cbind(minors_final_year[,1:2], 
                                  scale(minors_final_year[,3:length(minors_final_year)]))

set.seed(123)
train_control <- trainControl(method = "cv", number = 10)

baseline_cv <- train(
  Rookie_rOBA ~ ., 
  data = minors_final_year_scaled %>% select(-PlayerID),
  method = "lm",
  trControl = train_control
)

print(baseline_cv$results)

