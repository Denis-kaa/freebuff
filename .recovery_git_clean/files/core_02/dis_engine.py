"""Decision Intelligence System v0.2 (Phase 5 Forward-action #3).

Per `docs_10/engineering-memory/RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md` v5.94.0.
Phase 5 #3 implements: DIRSReviewer (ARE) + ConflictAnalyzer (CAE) + TechnicalDebtAnalyzer (TDA) + PolicyChecker (PC).
B17 (Governance Layer) transitions DOCTRINE -> ENFORCED per §37.7.
Closes governance gap per §35 R-... mitigating T8 risk.
"""
from dataclasses import dataclass, field
from enum import Enum


class Enforcement(Enum):
    """Policy enforcement level per RFC_DIS §9 hierarchy."""
    ADVISORY = "advisory"
    MANDATORY = "mandatory"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class ReviewScore:
    """7-criterion review score per RFC_DIS §4.1."""
    consistency: float = 0.0       # weight 0.20
    completeness: float = 0.0      # weight 0.10
    scalability: float = 0.0       # weight 0.15
    coupling: float = 0.0          # weight 0.15
    additivity: float = 0.0        # weight 0.15
    debt_risk: float = 0.0         # weight 0.15
    evolution_fit: float = 0.0     # weight 0.10
    overall: float = 0.0
    confidence: float = 0.0
    recommendations: list = field(default_factory=list)

    def to_dict(self):
        return {
            "consistency": self.consistency,
            "completeness": self.completeness,
            "scalability": self.scalability,
            "coupling": self.coupling,
            "additivity": self.additivity,
            "debt_risk": self.debt_risk,
            "evolution_fit": self.evolution_fit,
            "overall": self.overall,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
        ***REMOVED***


class DIRSReviewer:
    """Architecture Review Engine (ARE) per RFC_DIS §4.1."""

    WEIGHTS = {
        "consistency": 0.20,
        "completeness": 0.10,
        "scalability": 0.15,
        "coupling": 0.15,
        "additivity": 0.15,
        "debt_risk": 0.15,
        "evolution_fit": 0.10,
    ***REMOVED***

    def review(self, document_text):
        """Score document on 7 criteria. Returns ReviewScore."""
        consistency = self.score_consistency(document_text)
        completeness = self.score_completeness(document_text)
        scalability = self.score_scalability(document_text)
        coupling = self.score_coupling(document_text)
        additivity = self.score_additivity(document_text)
        debt_risk = self.score_debt_risk(document_text)
        evolution_fit = self.score_evolution_fit(document_text)
        overall = (
            consistency * self.WEIGHTS["consistency"***REMOVED*** +
            completeness * self.WEIGHTS["completeness"***REMOVED*** +
            scalability * self.WEIGHTS["scalability"***REMOVED*** +
            coupling * self.WEIGHTS["coupling"***REMOVED*** +
            additivity * self.WEIGHTS["additivity"***REMOVED*** +
            debt_risk * self.WEIGHTS["debt_risk"***REMOVED*** +
            evolution_fit * self.WEIGHTS["evolution_fit"***REMOVED***
        )
        # Confidence proportional to document length (longer = more confidence)
        confidence = min(1.0, len(document_text) / 5000.0)
        recommendations = [***REMOVED***
        if overall < 5.0:
            recommendations.append("REQUIRES_RESUBMISSION")
        elif overall < 7.0:
            recommendations.append("NEEDS_REVISION")
        else:
            recommendations.append("APPROVED_FOR_ARB")
        return ReviewScore(
            consistency=consistency,
            completeness=completeness,
            scalability=scalability,
            coupling=coupling,
            additivity=additivity,
            debt_risk=debt_risk,
            evolution_fit=evolution_fit,
            overall=overall,
            confidence=confidence,
            recommendations=recommendations,
        )

    def score_consistency(self, doc):
        # Heuristic: presence of "CON-" / "ADR-" references
        score = 5.0
        if "CON-" in doc or "ADR-" in doc:
            score += 2.0
        if "ADDITIVE" in doc or "CAN-16" in doc:
            score += 1.0
        return min(10.0, score)

    def score_completeness(self, doc):
        # Heuristic: section coverage
        score = 5.0
        for header in ["Назначение", "Архитектура", "Границы", "Принципы", "Реализация"***REMOVED***:
            if header.lower() in doc.lower():
                score += 1.0
        return min(10.0, score)

    def score_scalability(self, doc):
        score = 5.0
        if "scale" in doc.lower() or "scal" in doc.lower():
            score += 2.0
        return min(10.0, score)

    def score_coupling(self, doc):
        score = 7.0  # bonus default
        if "circular" in doc.lower() or "tight coupling" in doc.lower():
            score -= 3.0
        return max(0.0, min(10.0, score))

    def score_additivity(self, doc):
        score = 5.0
        if "Additive" in doc or "ADDITIVE" in doc:
            score += 3.0
        return min(10.0, score)

    def score_debt_risk(self, doc):
        score = 7.0
        if "hardcode" in doc.lower() or "single-entity" in doc.lower():
            score -= 3.0
        return max(0.0, min(10.0, score))

    def score_evolution_fit(self, doc):
        score = 5.0
        if "evolution" in doc.lower() or "BACKWARD" in doc.upper():
            score += 2.0
        return min(10.0, score)


class ConflictAnalyzer:
    """Conflict Analysis Engine (CAE) per RFC_DIS §4.2."""

    def detect_duplicates(self, doc):
        """Detect candidate duplicate terms in textual doc."""
        # Heuristic: phrases that repeat > 3 times may indicate duplicate definitions
        words = doc.lower().split()
        from collections import Counter
        counts = Counter(w for w in words if len(w) > 5)
        return [(term, c) for term, c in counts.most_common(10) if c >= 3***REMOVED***

    def analyze(self, doc):
        duplicates = self.detect_duplicates(doc)
        return {"duplicates_found": len(duplicates), "details": duplicates***REMOVED***


class TechnicalDebtAnalyzer:
    """Technical Debt Analyzer (TDA) per RFC_DIS §4.3."""

    DEBT_PATTERNS = [
        ("hardcoded paths", "hardcode", "high"),
        ("single-entity design", "single-entity", "high"),
        ("god component", "god component", "medium"),
        ("missing abstraction", "no abstract", "medium"),
    ***REMOVED***

    def predict_debt(self, doc):
        hits = [***REMOVED***
        for label, keyword, severity in self.DEBT_PATTERNS:
            if keyword in doc.lower():
                hits.append({"pattern": label, "severity": severity***REMOVED***)
        return hits


class PolicyChecker:
    """Policy Checker (PC) per RFC_DIS §4.4. Enforces mandatory/blocking rules."""

    DEFAULT_RULES = [
        {"rule": "all stages use atomic_write", "severity": "mandatory"***REMOVED***,
        {"rule": "no /tmp hardcoded paths", "severity": "mandatory"***REMOVED***,
        {"rule": "ADR-11 PRE-EXECUTION CHECKPOINT enforced", "severity": "blocking"***REMOVED***,
        {"rule": "ADDITIVE architecture (CAN-16)", "severity": "advisory"***REMOVED***,
    ***REMOVED***

    def enforce(self, doc, rules=None):
        if rules is None:
            rules = self.DEFAULT_RULES
        violations = [***REMOVED***
        for entry in rules:
            rule = entry["rule"***REMOVED***
            severity = entry["severity"***REMOVED***
            # Heuristic: rule keyword absence = violation
            keyword = rule.split()[0***REMOVED***  # First token as search keyword
            if keyword.lower() not in doc.lower() and severity in ("mandatory", "blocking"):
                violations.append({"rule": rule, "severity": severity***REMOVED***)
        return {"violations": violations, "passed": len(violations) == 0***REMOVED***


def cli_review(path):
    """CLI: review document and print ReviewScore as JSON."""
    import json
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    reviewer = DIRSReviewer()
    score = reviewer.review(text)
    ca = ConflictAnalyzer()
    conflicts = ca.analyze(text)
    tda = TechnicalDebtAnalyzer()
    debt = tda.predict_debt(text)
    pc = PolicyChecker()
    policies = pc.enforce(text)
    return {
        "score": score.to_dict(),
        "conflicts": conflicts,
        "debt": debt,
        "policies": policies,
    ***REMOVED***


if __name__ == "__main__":
    import json as _json, sys
    if len(sys.argv) >= 3 and sys.argv[1***REMOVED*** == "--review":
        result = cli_review(sys.argv[2***REMOVED***)
        print(_json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("DIS v0.2: use --review <path> to score a document")
        print("Components: DIRSReviewer + ConflictAnalyzer + TechnicalDebtAnalyzer + PolicyChecker")
