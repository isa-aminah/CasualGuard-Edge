# CAUSALGUARD-EDGE: Annotation Consistency Audit

## Purpose

Validate pedestrian-versus-occupant annotations before constructing the
pedestrian-vehicle near-miss machine-learning dataset.

## Dataset inspected

- Original tracking videos: 78
- Videos with interaction observations: 75
- Videos with candidate interaction episodes: 73
- Candidate interaction episodes: 4,373

## Manual annotation findings

### Visual review and reference

- Reviewed person-vehicle pairs: 20
- Occupant: 9
- Pedestrian: 7
- Uncertain: 4
- Duplicate review keys: 0
- Disagreements between visual review and reference: 0

### Corrected classification

- Reviewed occupants: 10
- Reviewed pedestrians: 6
- Reviewed uncertain: 4

One disagreement requires investigation:

- Video: (Brindavana) Sample 19.mp4
- Person track ID: 93
- Reference/visual label: PEDESTRIAN
- Corrected classification: OCCUPANT

This disagreement is unresolved. Neither label should be
automatically treated as ground truth until the source video is reviewed.

## Video coverage

- Tracking videos without interaction observations: 3
- Interaction videos without candidate episodes: 2

## Research implications

1. Person-versus-occupant classification requires further validation.
2. Candidate interaction episodes are not confirmed near-miss events.
3. Ground-truth near-miss labels must be created independently.
4. Video-level separation must be maintained during model evaluation.
5. Existing experimental CSV files must remain unchanged.

## Next research stage

- Resolve annotation disagreements.
- Validate pedestrian tracks.
- Establish verified interaction labels.
- Extract machine-learning features.
- Compare XGBoost, Random Forest and SVM.
- Evaluate using held-out videos.
