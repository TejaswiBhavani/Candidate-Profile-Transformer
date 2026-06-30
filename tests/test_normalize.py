import unittest

from eightfold.normalize import normalize_phone, normalize_date, normalize_email, normalize_text
from eightfold.skills_map import canonicalize_skill


class TestPhoneNormalization(unittest.TestCase):
    def test_bare_ten_digit_number_gets_default_country_code(self):
        self.assertEqual(normalize_phone("9876543210"), "+919876543210")

    def test_already_e164_passes_through(self):
        self.assertEqual(normalize_phone("+91 9876543210"), "+919876543210")

    def test_spaced_and_punctuated_number_normalizes(self):
        self.assertEqual(normalize_phone("+91 98765 43210"), "+919876543210")

    def test_leading_trunk_zero_is_stripped(self):
        self.assertEqual(normalize_phone("09876543210"), "+919876543210")

    def test_garbage_returns_none(self):
        self.assertIsNone(normalize_phone("call me maybe"))
        self.assertIsNone(normalize_phone(""))
        self.assertIsNone(normalize_phone(None))


class TestDateNormalization(unittest.TestCase):
    def test_month_year_to_iso(self):
        self.assertEqual(normalize_date("Jan 2023"), "2023-01")
        self.assertEqual(normalize_date("January 2023"), "2023-01")

    def test_present_is_a_sentinel_not_a_date(self):
        self.assertEqual(normalize_date("Present"), "present")
        self.assertEqual(normalize_date("current"), "present")

    def test_unparseable_returns_none(self):
        self.assertIsNone(normalize_date("sometime, idk"))


class TestEmailNormalization(unittest.TestCase):
    def test_lowercased_and_trimmed(self):
        self.assertEqual(normalize_email("  Tejaswi@Gmail.com "), "tejaswi@gmail.com")

    def test_missing_at_sign_is_invalid(self):
        self.assertIsNone(normalize_email("not-an-email"))


class TestSkillCanonicalization(unittest.TestCase):
    def test_known_synonyms_collapse(self):
        for variant in ("React", "ReactJS", "react.js", " REACTJS "):
            name, known = canonicalize_skill(variant)
            self.assertEqual(name, "React")
            self.assertTrue(known)

    def test_unknown_skill_falls_back_to_cleanup_not_drop(self):
        name, known = canonicalize_skill("  some niche framework  ")
        self.assertEqual(name, "Some Niche Framework")
        self.assertFalse(known)

    def test_acronym_like_terms_keep_casing(self):
        name, _ = canonicalize_skill("GraphQL")
        self.assertEqual(name, "GraphQL")


class TestTextNormalization(unittest.TestCase):
    def test_collapses_internal_whitespace(self):
        self.assertEqual(normalize_text("  Google   LLC "), "Google LLC")

    def test_empty_string_is_none(self):
        self.assertIsNone(normalize_text("   "))


if __name__ == "__main__":
    unittest.main()
