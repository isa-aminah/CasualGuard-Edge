# CAUSALGUARD-EDGE
# Test-Set Track Classification Manual Validation

## 1. Audit overview

- Reviewed tracks: 60
- Manual visual decisions: 60
- AI classification groups: 3

## 2. Manual decision distribution

manual_decision  count
      AMBIGUOUS      4
    NOT_VISIBLE      2
       OCCUPANT     12
     PEDESTRIAN     30
        VEHICLE     12

## 3. AI versus manual comparison

review_decision       AMBIGUOUS  NOT_VISIBLE  OCCUPANT  PEDESTRIAN  VEHICLE  All
weighted_track_class
pedestrian                    1            0         1          18        0   20
uncertain                     2            0         6          12        0   20
vehicle                       1            2         5           0       12   20
All                           4            2        12          30       12   60

## 4. Definitive pedestrian/vehicle subset

- Eligible manual pedestrian/vehicle tracks: 42
- AI decisive predictions: 30
- Correct decisive predictions: 30
- Prediction coverage: 71.43%
- Agreement among decisive predictions: 100.00%
- Correct predictions divided by all eligible tracks: 71.43%

Uncertain AI predictions are treated as abstentions, not silently counted as correct.

## 5. Occupant analysis

weighted_track_class  count
          pedestrian      1
           uncertain      6
             vehicle      5

## 6. Uncertain prediction analysis

manual_decision  count
     PEDESTRIAN     12
       OCCUPANT      6
      AMBIGUOUS      2

## 7. Methodological limitations

- This is a manually reviewed sample of 60 tracks from the test split.
- The sample was deliberately stratified by AI classification group.
- It is not a random representative sample of all test tracks.
- Results must not be presented as overall test-set accuracy.
- Manual decisions are based on visual contact sheets, not independent
  ground-truth annotations across every frame.
- Short tracks and uncertain visual evidence limit interpretation.
- Occupants are reported separately from pedestrians and vehicles.
- The analysis does not establish detection accuracy, tracking accuracy,
  near-miss detection accuracy, or real-world safety performance.

## 8. Interpretation

These findings are preliminary evidence about track-level role
classification. They can guide improvements and further validation,
but should not be generalized to the complete test dataset.
