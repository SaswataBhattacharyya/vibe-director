import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from story_builder.services.job_queue_status import local_job_queue_status


class LocalJobQueueStatusTest(unittest.TestCase):
    def test_counts_durable_job_stores_without_exposing_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ledger = root / "ledger.sqlite3"
            image_jobs = root / "images.sqlite3"
            with sqlite3.connect(ledger) as db:
                db.execute("CREATE TABLE production_takes (status TEXT)")
                db.executemany("INSERT INTO production_takes VALUES (?)",
                    [("queued",), ("running",), ("failed",), ("accepted",)])
                db.execute("CREATE TABLE story_assembly_export_jobs (state TEXT)")
                db.executemany("INSERT INTO story_assembly_export_jobs VALUES (?)",
                    [("queued",), ("rendering",), ("failed",), ("completed",)])
            with sqlite3.connect(image_jobs) as db:
                db.execute("CREATE TABLE production_image_jobs (status TEXT)")
                db.executemany("INSERT INTO production_image_jobs VALUES (?)",
                    [("queued",), ("preparing",), ("recovery_required",), ("completed",)])
            media_root = root / "repertoire"
            for kind, states in {"analysis": ["queued", "running", "interrupted"]} .items():
                for index, state in enumerate(states):
                    path = media_root / "jobs" / kind / str(index) / "job.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({"status": state, "request": {"private": True}}))

            result = local_job_queue_status(ledger_path=ledger, image_jobs_path=image_jobs,
                repertoire_root=media_root)

        self.assertTrue(result["checked"])
        self.assertEqual((result["pending"], result["active"], result["attention"]), (4, 4, 4))
        self.assertEqual({item["id"] for item in result["sources"]},
            {"video_production", "image_production", "video_exports", "media_prep"})
        self.assertNotIn("private", repr(result))

    def test_missing_or_corrupt_queue_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ledger = root / "ledger.sqlite3"
            with sqlite3.connect(ledger) as db:
                db.execute("CREATE TABLE production_takes (status TEXT)")
                db.execute("CREATE TABLE story_assembly_export_jobs (state TEXT)")
            images = root / "images.sqlite3"
            with sqlite3.connect(images) as db:
                db.execute("CREATE TABLE production_image_jobs (status TEXT)")
            bad_job = root / "repertoire/jobs/analysis/bad/job.json"
            bad_job.parent.mkdir(parents=True)
            bad_job.write_text("not json")

            result = local_job_queue_status(ledger_path=ledger, image_jobs_path=images,
                repertoire_root=root / "repertoire")

        self.assertFalse(result["checked"])
        self.assertIsNone(result["pending"])
        self.assertTrue(all(item["checked"] for item in result["sources"] if item["id"] != "media_prep"))
        self.assertFalse(next(item for item in result["sources"] if item["id"] == "media_prep")["checked"])


if __name__ == "__main__":
    unittest.main()
