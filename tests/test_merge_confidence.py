import unittest

from eightfold.models import Evidence
from eightfold.merge import merge_single_valued, merge_emails_or_phones, merge_skills


def ev(field, value, source, source_type="structured", method="test"):
    return Evidence(field, value, value, source, source_type, method)


class TestSingleValuedMerge(unittest.TestCase):
    def test_unanimous_agreement_high_confidence(self):
        evs = [ev("current_company", "Google", "a"), ev("current_company", "Google", "b")]
        result = merge_single_valued("current_company", evs, ["a", "b"])
        self.assertEqual(result["value"], "Google")
        self.assertFalse(result["conflict"])
        self.assertGreater(result["confidence"], 0.7)

    def test_no_evidence_is_null_not_invented(self):
        result = merge_single_valued("current_company", [], ["a"])
        self.assertIsNone(result["value"])
        self.assertEqual(result["confidence"], 0.0)

    def test_name_containment_prefers_more_complete_value(self):
        evs = [
            ev("full_name", "Tejaswi Bhavani", "csv"),
            ev("full_name", "Tejaswi Bhavani Hari", "resume"),
            ev("full_name", "Tejaswi Bhavani Hari", "linkedin"),
        ]
        result = merge_single_valued("full_name", evs, ["csv", "resume", "linkedin"])
        self.assertEqual(result["value"], "Tejaswi Bhavani Hari")
        self.assertTrue(result["conflict"])  # flagged even though we resolved it

    def test_true_contradiction_with_no_majority_resolves_to_null(self):
        # three sources, three different (non-containment) values -> can't adjudicate
        evs = [
            ev("current_company", "Google", "a"),
            ev("current_company", "Microsoft", "b"),
            ev("current_company", "Amazon", "c"),
        ]
        result = merge_single_valued("current_company", evs, ["a", "b", "c"])
        self.assertIsNone(result["value"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertTrue(result["conflict"])

    def test_majority_wins_over_minority(self):
        evs = [
            ev("current_title", "Software Engineer", "a"),
            ev("current_title", "Software Engineer", "b"),
            ev("current_title", "Software Engineer II", "c"),
        ]
        result = merge_single_valued("current_title", evs, ["a", "b", "c"])
        self.assertEqual(result["value"], "Software Engineer")
        self.assertTrue(result["conflict"])
        self.assertIn("software engineer ii", result["conflicting_values"])


class TestMultiValuedMerge(unittest.TestCase):
    def test_union_with_corroboration_ranking(self):
        evs = [
            ev("emails", "a@x.com", "csv"),
            ev("emails", "a@x.com", "resume"),
            ev("emails", "b@x.com", "linkedin"),
        ]
        items = merge_emails_or_phones("emails", evs, ["csv", "resume", "linkedin"])
        self.assertEqual(items[0]["value"], "a@x.com")  # 2 sources -> ranks first
        self.assertEqual(len(items[0]["sources"]), 2)
        self.assertEqual(items[1]["value"], "b@x.com")


class TestSkillsMerge(unittest.TestCase):
    def test_spelling_variants_unify_into_one_canonical_entry(self):
        evs = [
            ev("skills", "React", "resume", source_type="unstructured"),
            ev("skills", "ReactJS", "linkedin", source_type="semistructured"),
        ]
        items = merge_skills(evs, ["resume", "linkedin"])
        names = [i["name"] for i in items]
        self.assertEqual(names.count("React"), 1)
        self.assertEqual(set(items[0]["sources"]), {"resume", "linkedin"})


if __name__ == "__main__":
    unittest.main()
