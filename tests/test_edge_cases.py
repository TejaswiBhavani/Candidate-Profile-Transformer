import json
import os
import unittest

from eightfold.pipeline import run

HERE = os.path.dirname(__file__)


def p(*parts):
    return os.path.join(HERE, "..", *parts)


class TestSourceRobustness(unittest.TestCase):
    def test_missing_file_does_not_crash_pipeline(self):
        result = run([p("sample_inputs", "does_not_exist.csv"), p("sample_inputs", "resume.pdf")])
        self.assertTrue(any("not found" in w for w in result.warnings))
        # resume.pdf alone is still enough to produce a (partial) profile
        self.assertEqual(result.output["full_name"], "Tejaswi Bhavani Hari")

    def test_corrupt_pdf_is_skipped_not_fatal(self):
        result = run([p("sample_inputs", "recruiter.csv"), p("sample_inputs", "corrupt_resume.pdf")])
        self.assertTrue(result.ok)
        self.assertTrue(any("corrupt_resume.pdf" in w for w in result.warnings))
        self.assertEqual(result.output["full_name"], "Tejaswi Bhavani")  # from the still-good CSV

    def test_all_sources_bad_degrades_gracefully_rather_than_crashing(self):
        result = run([p("sample_inputs", "does_not_exist.csv"), p("sample_inputs", "corrupt_resume.pdf")])
        # the *process* doesn't crash; we get an honest validation failure
        # instead, since the default schema requires full_name and nothing
        # could supply one.
        self.assertFalse(result.ok)
        self.assertIn("full_name", " ".join(result.validation_errors))

    def test_unsupported_file_type_is_a_soft_warning(self):
        result = run([p("sample_inputs", "recruiter.csv"), p("README.md")])
        self.assertTrue(any("unsupported file type" in w for w in result.warnings))
        self.assertTrue(result.ok)


class TestOnMissingPolicies(unittest.TestCase):
    def setUp(self):
        self.sources = [p("sample_inputs", "recruiter.csv"), p("sample_inputs", "resume.pdf")]

    def test_on_missing_null_includes_key_with_none(self):
        config = {"fields": [{"path": "current_title"}, {"path": "fax_number"}], "on_missing": "null"}
        result = run(self.sources, config=config)
        self.assertIn("fax_number", result.output)
        self.assertIsNone(result.output["fax_number"])

    def test_on_missing_omit_drops_key_entirely(self):
        config = {"fields": [{"path": "current_title"}, {"path": "fax_number"}], "on_missing": "omit"}
        result = run(self.sources, config=config)
        self.assertNotIn("fax_number", result.output)

    def test_on_missing_error_fails_the_run_for_required_field(self):
        config = {
            "fields": [{"path": "fax_number", "required": True}],
            "on_missing": "error",
        }
        result = run(self.sources, config=config)
        self.assertFalse(result.ok)
        self.assertTrue(any("fax_number" in e for e in result.validation_errors))

    def test_invalid_config_is_reported_cleanly(self):
        config = {"fields": [{}], "on_missing": "explode"}
        result = run(self.sources, config=config)
        self.assertFalse(result.ok)
        self.assertTrue(any("config" in e for e in result.validation_errors))


class TestSinglySourcedField(unittest.TestCase):
    def test_field_seen_in_only_one_source_gets_lower_but_nonzero_confidence(self):
        result = run([p("sample_inputs", "linkedin.json")])
        skills = {s["name"]: s["confidence"] for s in result.output["skills"]}
        self.assertIn("SQL", skills)
        self.assertLess(skills["SQL"], 0.7)
        self.assertGreater(skills["SQL"], 0.0)


if __name__ == "__main__":
    unittest.main()
