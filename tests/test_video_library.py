import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_library import (
    VideoLibraryError,
    delete_video,
    get_video,
    get_alert_reviews,
    save_video,
    set_alert_status,
    videos_directory,
)


class VideoLibraryDeletionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {"CAUSALGUARD_DATA_DIR": self.temporary_directory.name},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_deleting_video_removes_library_record_and_all_video_files(self):
        video = save_video(b"original clip bytes", "crossing.mp4")
        processed_path = videos_directory() / f"{video['video_id']}_tracked.mp4"
        processed_path.write_bytes(b"annotated clip bytes")

        from video_library import record_analysis

        record_analysis(
            video["video_id"],
            {
                "processed_filename": processed_path.name,
                "model_name": "test-model",
                "frames_processed": 1,
                "pedestrian_tracks": 1,
                "vehicle_tracks": 1,
                "pedestrian_detections": 1,
                "vehicle_detections": 1,
            },
        )

        delete_video(video["video_id"])

        self.assertIsNone(get_video(video["video_id"]))
        self.assertFalse((videos_directory() / video["stored_filename"]).exists())
        self.assertFalse(processed_path.exists())
        self.assertEqual(list(Path(videos_directory()).iterdir()), [])

    def test_deleting_unknown_video_reports_a_library_error(self):
        with self.assertRaisesRegex(VideoLibraryError, "no longer in the saved library"):
            delete_video("a" * 64)

    def test_invalid_ids_are_rejected_without_touching_storage(self):
        with self.assertRaisesRegex(VideoLibraryError, "ID is invalid"):
            delete_video("..")

        self.assertFalse(Path(videos_directory()).exists())

    def test_deleting_video_also_removes_its_persisted_alert_review_status(self):
        video = save_video(b"clip with alert", "alert.mp4")
        set_alert_status(video["video_id"], "EV-001", "Acknowledged")

        delete_video(video["video_id"])

        self.assertNotIn((video["video_id"], "EV-001"), get_alert_reviews())

    def test_reanalysis_clears_review_status_for_recomputed_event_ids(self):
        video = save_video(b"clip that is reanalyzed", "reanalyzed.mp4")
        from video_library import record_analysis

        result = {
            "processed_filename": f"{video['video_id']}_tracked.mp4",
            "model_name": "test-model",
            "frames_processed": 1,
            "pedestrian_tracks": 1,
            "vehicle_tracks": 1,
            "pedestrian_detections": 1,
            "vehicle_detections": 1,
        }
        record_analysis(video["video_id"], result)
        set_alert_status(video["video_id"], "EV-001", "Acknowledged")
        record_analysis(video["video_id"], result)

        self.assertNotIn((video["video_id"], "EV-001"), get_alert_reviews())


if __name__ == "__main__":
    unittest.main()
