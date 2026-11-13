# Dataset and Tracking Summary

## Dataset split

| Split | Videos | Detection records |
|---|---:|---:|
| Training | 78 | 238,088 |
| Validation | 16 | 44,120 |
| Testing | 18 | 38,569 |

## Detection configuration

- Detector: YOLO26n
- Tracker: ByteTrack
- Confidence threshold: 0.25
- Image size: 640
- Processing device: CUDA GPU (device 0)
- Classes: Person, Car, Motorcycle, Bus, Truck

## Interpretation

Detection records represent object detections across video frames. They are not unique objects, manually verified detections, or near-miss ground-truth labels.

Training, validation and testing were processed into separate folders. The test split is held out for final evaluation.