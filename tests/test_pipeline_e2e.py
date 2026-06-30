import os
import unittest

from eightfold.pipeline import run

HERE = os.path.dirname(__file__)
SAMPLES = os.path.join(HERE, "..", "sample_inputs")
CONFIGS = os.path.join(HERE, "..", "configs")


def p(*parts):
    return os.path.join(HERE, "..", *parts)


class TestEndToEndDefaultSchema(unittest.TestCase):
    def setUp(self):
        self.result = run([
            p("sample_inputs", "recruiter.csv"),
            p("sample_inputs", "resume.pdf"),
            p("sample_inputs", "linkedin.json"),
        ])

    def test_run_succeeds_and_validates(self):
        self.assertTrue(self.result.ok, self.result.validation_errors)

    def test_name_resolved_to_most_complete_version(self):
        self.assertEqual(self.result.output["full_name"], "Tejaswi Bhavani Hari")

    def test_phone_normalized_and_deduplicated_across_formats(self):
        self.assertEqual(self.result.output["phones"], ["+919876543210"])

    def test_skills_are_canonicalized_and_deduplicated(self):
        names = [s["name"] for s in self.result.output["skills"]]
        self.assertIn("React", names)
        self.assertNotIn("ReactJS", names)
        self.assertEqual(len(names), len(set(names)))

    def test_company_full_agreement(self):
        self.assertEqual(self.result.output["current_company"], "Google")

    def test_deterministic_same_inputs_same_output(self):
        result2 = run([
            p("sample_inputs", "recruiter.csv"),
            p("sample_inputs", "resume.pdf"),
            p("sample_inputs", "linkedin.json"),
        ])
        self.assertEqual(self.result.output, result2.output)


class TestEndToEndCustomConfig(unittest.TestCase):
    def test_public_profile_config_shape(self):
        import json
        with open(p("configs", "public_profile.json")) as f:
            config = json.load(f)
        result = run([
            p("sample_inputs", "recruiter.csv"),
            p("sample_inputs", "resume.pdf"),
            p("sample_inputs", "linkedin.json"),
        ], config=config)
        self.assertTrue(result.ok, result.validation_errors)
        self.assertIn("primary_email", result.output)
        self.assertIn("primary_email_confidence", result.output)  # include_confidence=true
        self.assertNotIn("linkedin_url", result.output)  # on_missing=omit drops genuinely absent field

    def test_public_profile_config_exposes_methods_when_requested(self):
        import json
        with open(p("configs", "public_profile.json")) as f:
            config = json.load(f)
        config["include_provenance"] = True
        config["include_confidence"] = False
        result = run([
            p("sample_inputs", "recruiter.csv"),
            p("sample_inputs", "resume.pdf"),
            p("sample_inputs", "linkedin.json"),
        ], config=config)
        self.assertTrue(result.ok, result.validation_errors)
        self.assertIn("primary_email_methods", result.output)
        self.assertIn("phone_sources", result.output)

    def test_minimal_config_only_returns_requested_fields(self):
        import json
        with open(p("configs", "minimal.json")) as f:
            config = json.load(f)
        result = run([p("sample_inputs", "recruiter.csv"), p("sample_inputs", "resume.pdf")], config=config)
        self.assertEqual(set(result.output.keys()), {"full_name", "primary_email"})


class TestURLDiscoveryAndPriority(unittest.TestCase):
    def test_discover_urls_from_text(self):
        from eightfold.url_discovery import discover_urls
        text = [
            "Here is my resume. Contact me on linkedin: linkedin.com/in/johndoe",
            "Or github.com/johndoe. Also check my site www.johndoe.dev/portfolio"
        ]
        urls = discover_urls(text)
        self.assertEqual(urls["linkedin"], "https://linkedin.com/in/johndoe")
        self.assertEqual(urls["github"], "https://github.com/johndoe")
        self.assertEqual(urls["portfolio"], "https://www.johndoe.dev/portfolio")

    def test_source_priority_ranking(self):
        from eightfold.merge import _source_rank
        # Resume is highest priority
        self.assertEqual(_source_rank("resume.pdf", []), 0)
        # LinkedIn is next
        self.assertEqual(_source_rank("linkedin_apify", []), 1)
        # GitHub is next
        self.assertEqual(_source_rank("github_apify", []), 2)
        # ATS JSON is next
        self.assertEqual(_source_rank("candidate.json", []), 3)
        # CSV is next
        self.assertEqual(_source_rank("recruiter.csv", []), 4)
        # TXT is last
        self.assertEqual(_source_rank("notes.txt", []), 5)


if __name__ == "__main__":
    unittest.main()
