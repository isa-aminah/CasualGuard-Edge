
from app.video_processing import (
    _classify_track,
    _finalize_track_classifications,
)


def make_observations(class_ids, confidence=0.8):
    return [
        {"class_id": class_id, "confidence": confidence}
        for class_id in class_ids
    ]


def test_person_track_is_classified_as_pedestrian():
    observations = make_observations([0, 0, 0, 0, 0])
    assert _classify_track(observations) == "pedestrian"


def test_vehicle_track_is_classified_as_vehicle():
    observations = make_observations([2, 2, 3, 5, 7])
    assert _classify_track(observations) == "vehicle"


def test_person_motorcycle_mixed_track_is_uncertain():
    observations = make_observations([0, 0, 3, 0, 0])
    assert _classify_track(observations) == "uncertain"


def test_person_car_mixed_track_is_uncertain():
    observations = make_observations([0, 0, 2, 0, 0])
    assert _classify_track(observations) == "uncertain"


def test_insufficient_observations_are_uncertain():
    observations = make_observations([0, 0, 0, 0])
    assert _classify_track(observations) == "uncertain"


def test_finalizer_assigns_track_categories():
    tracked_objects = {
        1: {"observations": make_observations([0, 0, 0, 0, 0])},
        2: {"observations": make_observations([2, 3, 5, 7, 2])},
        3: {"observations": make_observations([0, 0, 3, 0, 0])},
    }

    pedestrians, vehicles = _finalize_track_classifications(
        tracked_objects
    )

    assert tracked_objects[1]["kind"] == "pedestrian"
    assert tracked_objects[2]["kind"] == "vehicle"
    assert tracked_objects[3]["kind"] == "uncertain"

    assert pedestrians == {1}
    assert vehicles == {2}
