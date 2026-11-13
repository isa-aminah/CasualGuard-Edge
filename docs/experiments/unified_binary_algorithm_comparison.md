# Unified Binary Algorithm Comparison and Model Selection

## 1. Experiment Objective

This experiment compares five machine-learning algorithms using two feature configurations for pedestrian–vehicle track classification in CAUSALGUARD-EDGE.

The objective is to identify the most suitable classification algorithm while ensuring a fair comparison across identical data, labels and validation folds.

## 2. Dataset and Validation Setup

- Total manually reviewed tracks: 54
- Unique videos: 15
- Classification classes: PEDESTRIAN and VEHICLE
- PEDESTRIAN samples: 30
- VEHICLE samples: 24
- Validation strategy: Leave-One-Video-Out cross-validation
- Number of validation folds: 15
- Baseline feature configuration: 16 features
- Enhanced feature configuration: 40 features

The original OCCUPANT label was merged into VEHICLE for this unified binary experiment.

Dataset validation confirmed:
- 54 tracks in each feature dataset.
- Identical video and track identifiers.
- Identical mapped binary labels.
- Identical video-wise validation groups.

All five algorithms were evaluated using both feature configurations.

## 3. Algorithm Performance Comparison

| Algorithm | Feature Set | Accuracy | Balanced Accuracy | Macro F1 |
|---|---|---:|---:|---:|
| Logistic Regression | Baseline 16 | 85.19% | 85.42% | 85.10% |
| SVM RBF | Baseline 16 | 83.33% | 82.92% | 83.05% |
| Random Forest | Baseline 16 | 87.04% | 87.50% | 87.00% |
| XGBoost | Baseline 16 | 90.74% | 90.42% | 90.58% |
| LightGBM | Baseline 16 | 87.04% | 87.50% | 87.00% |
| Logistic Regression | Enhanced 40 | 83.33% | 82.92% | 83.05% |
| SVM RBF | Enhanced 40 | 75.93% | 74.58% | 74.88% |
| Random Forest | Enhanced 40 | 87.04% | 87.08% | 86.92% |
| XGBoost | Enhanced 40 | 90.74% | 90.42% | 90.58% |
| LightGBM | Enhanced 40 | 87.04% | 87.50% | 87.00% |

XGBoost achieved the highest accuracy and macro F1 in both feature configurations.

## 4. Class-Wise Performance of XGBoost

The baseline and enhanced XGBoost configurations achieved identical class-wise metrics.

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| PEDESTRIAN | 90.32% | 93.33% | 91.80% | 30 |
| VEHICLE | 91.30% | 87.50% | 89.36% | 24 |

Out of 30 pedestrian tracks, 28 were correctly classified.

Out of 24 vehicle tracks, 21 were correctly classified.

Overall, 49 out of 54 tracks were correctly classified.

## 5. Prediction Latency Comparison

Mean prediction latency per track, as recorded by the experiment:

| Algorithm | Baseline 16 Features | Enhanced 40 Features |
|---|---:|---:|
| Logistic Regression | 0.703 ms | 0.766 ms |
| SVM RBF | 0.588 ms | 0.658 ms |
| Random Forest | 26.131 ms | 22.391 ms |
| XGBoost | 1.349 ms | 2.121 ms |
| LightGBM | 0.940 ms | 1.107 ms |

The baseline XGBoost configuration achieved the same predictive performance as enhanced XGBoost with lower measured prediction latency.

The measured latency is per-track prediction time, not total video-processing or end-to-end system latency.

## 6. Investigation of Differing XGBoost Predictions

The two XGBoost configurations produced different predictions on only two of the 54 tracks.

| Video | Track ID | Actual | Baseline Prediction | Enhanced Prediction |
|---|---:|---|---|---|
| (Brindavana) Sample 17.mp4 | 184 | VEHICLE | PEDESTRIAN | VEHICLE |
| (Travel) Sample 4.mp4 | 484 | VEHICLE | VEHICLE | PEDESTRIAN |

The enhanced feature configuration corrected the first prediction but incorrectly classified the second track.

Consequently, both configurations retained the same total of 49 correct predictions out of 54.

This demonstrates that the enhanced feature set changed individual classification decisions without improving aggregate performance in this experiment.

## 7. Model Selection Decision

**Selected algorithm: XGBoost**

**Selected feature configuration: Baseline 16 features**

Reasons for selection:

1. Highest observed accuracy among the five compared algorithms: 90.74%.
2. Highest observed macro F1: 90.58%.
3. Highest observed balanced accuracy: 90.42%.
4. Identical class-wise performance to the enhanced 40-feature XGBoost configuration.
5. Lower measured prediction latency: 1.349 ms per track compared with 2.121 ms.
6. Lower feature dimensionality, reducing the number of input features from 40 to 16.

The baseline XGBoost configuration is therefore selected as the preferred classification configuration for the current prototype.

The enhanced feature configuration is retained as an experimental comparison rather than discarded.

## 8. Limitations

The experiment uses 54 manually reviewed tracks from 15 videos. The reviewed tracks were manually selected and do not constitute a random, representative sample of all traffic conditions.

The reported metrics should therefore be interpreted as exploratory results from video-wise cross-validation, not as proof of generalisation to all road environments.

The prediction latency figures represent the experiment's recorded mean prediction time per track. They do not represent the end-to-end latency of the complete detection, tracking, classification and alert pipeline.

Near-miss detection, TTC/PET estimation and causal counterfactual analysis are separate project components. The classification accuracy reported here must not be presented as the accuracy of those components.

## 9. Reproducibility and Evidence Files

Experiment script:

`tools/run_unified_binary_comparison.py`

Input datasets:

- `training/algorithm_comparison/reviewed_track_feature_dataset.csv`
- `training/algorithm_comparison/experiment2_features/experiment2_feature_dataset.csv`

Generated results:

`training/algorithm_comparison/unified_binary_comparison/`

Important output files:

- `unified_binary_summary.csv`
- `unified_binary_per_class.csv`
- `unified_binary_oof_predictions.csv`
- `unified_binary_per_video_folds.csv`
- Confusion matrix CSV files for the evaluated configurations.

The experiment audit confirmed that both feature configurations contained identical tracks and mapped labels and were evaluated with the same video-wise folds.

## 10. Conclusion

Among the five evaluated algorithms, XGBoost achieved the strongest classification performance.

The 16-feature and 40-feature XGBoost configurations achieved identical overall and class-wise metrics. The 16-feature configuration had lower measured prediction latency and required fewer features.

Therefore, XGBoost with the original 16 features is selected as the preferred classifier for the current CAUSALGUARD-EDGE prototype.

Further evaluation on a larger, more diverse and independently collected dataset is required before making broader generalisation claims.