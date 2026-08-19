"""Static medical knowledge graph — adapted from Healthcare.ipynb Week 6
(MedicalKnowledgeGraph + find_diagnoses_for_symptoms/get_cross_reactive_allergens,
cells 87-88). Used by the Risk Detection agent to corroborate LLM findings
with a deterministic ontology.
"""
import networkx as nx

LAB_TESTS_TO_DIAGNOSES: dict[str, list[str]] = {
    "CBC": ["anemia", "infection", "leukemia"],
    "LFT": ["hepatitis", "cirrhosis", "fatty_liver"],
    "KFT": ["kidney_disease", "dehydration"],
    "Thyroid_Panel": ["hypothyroidism", "hyperthyroidism"],
}

SYMPTOMS_TO_DIAGNOSES: dict[str, list[str]] = {
    "fatigue": ["anemia", "hypothyroidism", "infection"],
    "fever": ["infection", "inflammation"],
    "shortness_of_breath": ["anemia", "pneumonia", "heart_failure"],
    "cough": ["pneumonia", "bronchitis", "asthma"],
}

ALLERGEN_CROSS_REACTIVITY: dict[str, list[str]] = {
    "peanut": ["tree_nuts", "legumes", "lupin"],
    "penicillin": ["amoxicillin", "cephalosporins"],
    "latex": ["banana", "avocado", "kiwi"],
    "shellfish": ["shrimp", "crab", "lobster"],
    "aspirin": ["nsaids", "ibuprofen"],
}

DIAGNOSIS_TREATMENTS: dict[str, list[str]] = {
    "anemia": ["iron_supplements", "b12_injection"],
    "infection": ["antibiotics", "antivirals"],
    "hypothyroidism": ["levothyroxine"],
}


class MedicalKnowledgeGraph:
    """NetworkX DiGraph encoding TEST/DIAGNOSIS/SYMPTOM/ALLERGEN/TREATMENT
    nodes and CONFIRMS/INDICATES/CROSS_REACTIVE/TREATS relations."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self._build_medical_ontology()

    def _build_medical_ontology(self) -> None:
        for test, diagnoses in LAB_TESTS_TO_DIAGNOSES.items():
            self.graph.add_node(test, type="TEST")
            for diagnosis in diagnoses:
                self.graph.add_node(diagnosis, type="DIAGNOSIS")
                self.graph.add_edge(test, diagnosis, relation="CONFIRMS")

        for symptom, diagnoses in SYMPTOMS_TO_DIAGNOSES.items():
            self.graph.add_node(symptom, type="SYMPTOM")
            for diagnosis in diagnoses:
                if not self.graph.has_node(diagnosis):
                    self.graph.add_node(diagnosis, type="DIAGNOSIS")
                self.graph.add_edge(symptom, diagnosis, relation="INDICATES")

        for allergen, cross_reactive in ALLERGEN_CROSS_REACTIVITY.items():
            self.graph.add_node(allergen, type="ALLERGEN")
            for related in cross_reactive:
                self.graph.add_node(related, type="ALLERGEN")
                self.graph.add_edge(allergen, related, relation="CROSS_REACTIVE")

        for diagnosis, treatments in DIAGNOSIS_TREATMENTS.items():
            for treatment in treatments:
                self.graph.add_node(treatment, type="TREATMENT")
                self.graph.add_edge(treatment, diagnosis, relation="TREATS")

    def find_diagnoses_for_symptoms(self, symptoms: list[str]) -> dict:
        diagnosis_scores: dict[str, int] = {}
        for symptom in symptoms:
            if self.graph.has_node(symptom):
                for _, target, data in self.graph.out_edges(symptom, data=True):
                    if data.get("relation") == "INDICATES":
                        diagnosis_scores[target] = diagnosis_scores.get(target, 0) + 1
        return {
            "symptoms": symptoms,
            "diagnoses": sorted(diagnosis_scores.items(), key=lambda x: -x[1]),
        }

    def get_cross_reactive_allergens(self, allergen: str) -> list[str]:
        cross_reactive = []
        if self.graph.has_node(allergen):
            for _, target, data in self.graph.out_edges(allergen, data=True):
                if data.get("relation") == "CROSS_REACTIVE":
                    cross_reactive.append(target)
        return cross_reactive

    def find_diagnoses_for_test(self, test: str) -> list[str]:
        """CONFIRMS edges from a lab test category (e.g. 'CBC') to candidate diagnoses."""
        diagnoses = []
        if self.graph.has_node(test):
            for _, target, data in self.graph.out_edges(test, data=True):
                if data.get("relation") == "CONFIRMS":
                    diagnoses.append(target)
        return diagnoses
