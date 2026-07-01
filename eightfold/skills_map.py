"""
A small, explicit synonym table for skill canonicalization.

This is intentionally a flat dict rather than fuzzy matching: it's
deterministic and explainable (a requirement of the brief) at the cost of
not catching every possible spelling. Anything not in the table falls
back to a generic cleanup (trim, collapse whitespace, title-case) rather
than being dropped — we never invent or discard a candidate's stated
skill, we just don't get the canonicalization confidence bonus for it.
"""

import re

# lowercased variant -> canonical display name
SKILL_SYNONYMS = {
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "golang": "Go",
    "go": "Go",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "django": "Django",
    "flask": "Flask",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "restful api": "REST APIs",
    "eclispe": "Eclipse",
    "eclipse": "Eclipse",
    "vs code": "VS Code",
    "visual studio": "Visual Studio",
    "github": "GitHub",
    "mongodb": "MongoDB",
    "firebase": "Firebase",
    "kubernetes": "Kubernetes",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    "c/c++": "C/C++",
}


def canonicalize_skill(raw: str):
    """Returns (canonical_name, was_known) — was_known=False means we
    fell back to generic cleanup, which downstream code uses to apply a
    slightly lower confidence bonus (we can't vouch for novel terms the
    same way we can for known synonyms)."""
    if raw is None:
        return None, False
    cleaned = " ".join(str(raw).strip().split())
    cleaned = re.sub(r"^[\s\u2022•·\-*]+", "", cleaned).rstrip(".,;:")
    if not cleaned:
        return None, False
    key = cleaned.lower()
    if key in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[key], True
    # generic fallback: title-case short tokens, but preserve things that
    # look like acronyms or already have internal capitalization (e.g. "SQL", "GraphQL")
    if cleaned.isupper() or any(c.isupper() for c in cleaned[1:]):
        return cleaned, False
    return cleaned.title(), False
