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

    def test_pdf_header_normalization_handles_split_headers(self):
        from eightfold.sources.pdf_source import _normalize_header
        self.assertEqual(_normalize_header("Ski lls:"), "skills")
        self.assertEqual(_normalize_header("Ski  lls"), "skills")
        self.assertEqual(_normalize_header("Exp erience"), "experience")
        self.assertEqual(_normalize_header("Edu cation:"), "education")
        self.assertEqual(_normalize_header("Hon ors & Awards"), "awards")
        self.assertEqual(_normalize_header("TECHNNICAL SKILLS"), "skills")

    def test_pdf_name_picker_skips_location_lines(self):
        from eightfold.sources.pdf_source import _pick_name_line
        lines = [
            "EDUCATION",
            "+91 8919546693",
            "Hyderabad, Telangana, India",
            "TEJASWI BHAVANI HARI",
            "bhavanih1111@gmail.com",
        ]
        self.assertEqual(_pick_name_line(lines), "TEJASWI BHAVANI HARI")

    def test_pdf_name_picker_skips_section_headers(self):
        from eightfold.sources.pdf_source import _pick_name_line
        lines = [
            "TECHNNICAL SKILLS",
            "TEJASWI BHAVANI HARI",
            "Hyderabad, Telangana, India",
        ]
        self.assertEqual(_pick_name_line(lines), "TEJASWI BHAVANI HARI")

    def test_skill_canonicalization_cleans_typos_and_punctuation(self):
        from eightfold.skills_map import canonicalize_skill
        self.assertEqual(canonicalize_skill("Eclispe."), ("Eclipse", True))
        self.assertEqual(canonicalize_skill("VS code"), ("VS Code", True))


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


class TestURLNormalization(unittest.TestCase):
    def test_linkedin_url_without_in_segment_is_normalized(self):
        from eightfold.url_discovery import discover_urls
        urls = discover_urls([
            "https://linkedIn.com/tejaswibhavnaih",
            "https://github.com/TejaswiBhavani",
        ])
        self.assertEqual(urls["linkedin"], "https://linkedin.com/in/tejaswibhavnaih")
        self.assertEqual(urls["github"], "https://github.com/TejaswiBhavani")


if __name__ == "__main__":
    unittest.main()
