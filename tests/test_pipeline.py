import unittest
from eightfold.pipeline import Pipeline
from eightfold.extract import Evidence

class DummyExtractor:
    def __init__(self, evidence_list):
        self.evidence_list = evidence_list
    def extract(self, *args, **kwargs):
        return self.evidence_list

class TestPipeline(unittest.TestCase):
    def test_conflict_resolution(self):
        # Edge case: severe conflict on full_name across unstructured and structured sources
        ev1 = Evidence("full_name", "Byungjin Park", "Byungjin Park", "resume.pdf", "heuristic", "heuristic:smart_first_line")
        ev2 = Evidence("full_name", "Tejaswi Bhavani", "Tejaswi Bhavani", "recruiter.csv", "structured", "csv:full_name")
        ev3 = Evidence("emails", "posquit0.bj@gmail.com", "posquit0.bj@gmail.com", "resume.pdf", "regex", "regex:email")
        ev4 = Evidence("emails", "bhavanih1111@gmail.com", "bhavanih1111@gmail.com", "recruiter.csv", "structured", "csv:email")

        pipeline = Pipeline()
        pipeline.extractors = [DummyExtractor([ev1, ev2, ev3, ev4])]
        
        canonical, projected, meta = pipeline.run(["dummy.pdf"])
        
        # 1. Because of severe conflict, name should resolve to None
        self.assertIsNone(projected["full_name"])
        
        # 2. Both emails should be safely unioned
        self.assertIn("posquit0.bj@gmail.com", projected["emails"])
        self.assertIn("bhavanih1111@gmail.com", projected["emails"])
        
        # 3. Overall confidence should plummet due to contradiction
        self.assertLess(projected["overall_confidence"], 0.2)

    def test_containment_refinement(self):
        # Edge case: One name is a stricter subset of the other
        ev1 = Evidence("full_name", "Tejaswi", "Tejaswi", "resume.pdf", "heuristic", "heuristic:smart_first_line")
        ev2 = Evidence("full_name", "Tejaswi Bhavani Hari", "Tejaswi Bhavani Hari", "linkedin_apify", "semistructured", "apify:name")

        pipeline = Pipeline()
        pipeline.extractors = [DummyExtractor([ev1, ev2])]
        
        canonical, projected, meta = pipeline.run(["dummy.pdf"])
        
        # The engine should recognize "Tejaswi" as a subset and refine to the full name
        self.assertEqual(projected["full_name"], "Tejaswi Bhavani Hari")

if __name__ == "__main__":
    unittest.main()
