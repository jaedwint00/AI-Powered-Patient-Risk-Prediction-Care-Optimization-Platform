"""
Simplified NLP service for medical text analysis
This version avoids complex dependencies and provides basic functionality
"""

import re
from typing import List, Dict, Any
from loguru import logger


class NLPService:
    """Simplified Natural Language Processing service for medical text analysis"""

    def __init__(self):
        self.medical_entities = {
            "medications": [
                "metformin",
                "insulin",
                "lisinopril",
                "atorvastatin",
                "aspirin",
                "warfarin",
                "prednisone",
                "furosemide",
                "levothyroxine",
                "omeprazole",
            ],
            "conditions": [
                "diabetes",
                "hypertension",
                "hyperlipidemia",
                "heart disease",
                "copd",
                "asthma",
                "pneumonia",
                "stroke",
                "myocardial infarction",
                "atrial fibrillation",
                "heart failure",
                "kidney disease",
            ],
            "symptoms": [
                "chest pain",
                "shortness of breath",
                "fatigue",
                "dizziness",
                "nausea",
                "vomiting",
                "fever",
                "cough",
                "headache",
                "pain",
            ],
        }

    async def initialize(self):
        """Initialize the NLP service"""
        logger.info("Initializing simplified NLP service")
        return True

    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract medical entities from text using rule-based approach"""
        text_lower = text.lower()

        entities: Dict[str, List[str]] = {
            "medications": [],
            "conditions": [],
            "symptoms": [],
            "measurements": [],
        }

        # Extract medications
        for med in self.medical_entities["medications"]:
            if med in text_lower:
                entities["medications"].append(med.title())

        # Extract conditions
        for condition in self.medical_entities["conditions"]:
            if condition in text_lower:
                entities["conditions"].append(condition.title())

        # Extract symptoms
        for symptom in self.medical_entities["symptoms"]:
            if symptom in text_lower:
                entities["symptoms"].append(symptom.title())

        # Extract measurements (blood pressure, heart rate, etc.)
        bp_pattern = r"(\d{2,3})/(\d{2,3})\s*mmhg"
        hr_pattern = r"(\d{2,3})\s*bpm"
        temp_pattern = r"(\d{2,3}\.?\d*)\s*°?[cf]"

        bp_matches = re.findall(bp_pattern, text_lower)
        hr_matches = re.findall(hr_pattern, text_lower)
        temp_matches = re.findall(temp_pattern, text_lower)

        if bp_matches:
            entities["measurements"].extend(
                [f"{sys}/{dia} mmHg" for sys, dia in bp_matches]
            )
        if hr_matches:
            entities["measurements"].extend([f"{hr} bpm" for hr in hr_matches])
        if temp_matches:
            entities["measurements"].extend([f"{temp}°" for temp in temp_matches])

        return {
            "entities": entities,
            "entity_count": sum(len(v) for v in entities.values()),
            "categorized": entities,
        }

    async def summarize_text(self, text: str, max_length: int = 150) -> str:
        """Simple text summarization using sentence extraction"""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) <= 2:
            return text

        # Score sentences based on medical keywords
        scored_sentences = []
        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()

            # Higher score for sentences with medical terms
            for category in self.medical_entities.values():
                for term in category:
                    if term in sentence_lower:
                        score += 1

            scored_sentences.append((score, sentence))

        # Sort by score and take top sentences
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        top_sentences = [sent for _, sent in scored_sentences[:2]]

        summary = ". ".join(top_sentences)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    async def semantic_search(
        self, query: str, documents: List[str], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based search"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            doc_words = set(doc_lower.split())

            # Calculate simple overlap score
            match_count = len(query_words.intersection(doc_words))
            score = float(match_count) / float(len(query_words)) if query_words else 0

            if score > 0:
                results.append(
                    {
                        "document_id": i,
                        "text": doc,
                        "score": score,
                        "snippet": doc[:200] + "..." if len(doc) > 200 else doc,
                    }
                )

        # Sort by score and return top_k
        results.sort(
            reverse=True,
            key=lambda x: (
                float(x["score"]) if isinstance(x["score"], (int, float)) else 0.0
            ),
        )
        return results[:top_k]

    async def classify_text(self, text: str) -> Dict[str, Any]:
        """Simple rule-based text classification"""
        text_lower = text.lower()

        # Classification categories
        categories = {
            "emergency": ["emergency", "urgent", "critical", "severe", "acute"],
            "routine": ["routine", "follow-up", "scheduled", "regular"],
            "diagnostic": ["test", "scan", "x-ray", "mri", "ct", "lab", "blood work"],
            "treatment": ["treatment", "therapy", "medication", "surgery", "procedure"],
        }

        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = score / len(keywords)

        # Get the category with highest score
        predicted_category = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[predicted_category]

        return {
            "category": predicted_category,
            "confidence": confidence,
            "all_scores": scores,
        }

    async def process_medical_text(
        self, text: str, task: str = "extract_entities"
    ) -> Dict[str, Any]:
        """Process medical text based on the specified task"""

        if task == "extract_entities":
            return await self.extract_entities(text)
        if task == "summarize":
            summary = await self.summarize_text(text)
            return {"summary": summary}
        if task == "classify":
            return await self.classify_text(text)
        # Default: extract entities
        return await self.extract_entities(text)
