"""
Natural Language Processing service for medical text analysis.

Provides comprehensive NLP capabilities including entity extraction,
text summarization, semantic search, and medical text classification
for the AI-Powered Patient Risk Prediction platform.
"""
import re
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from loguru import logger
from sentence_transformers import SentenceTransformer  # type: ignore
from transformers import (AutoModel, AutoTokenizer, BertModel,  # type: ignore
                          BertTokenizer, pipeline)

from app.models.schemas import ExtractedEntity
from config.settings import settings


class NLPService:
    """Natural Language Processing service for medical text analysis"""

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.embeddings_model: Optional[SentenceTransformer] = None
        self.summarizer: Optional[Any] = None
        self.ner_pipeline: Optional[Any] = None

        # Initialize models
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize NLP models"""
        try:
            # Clinical BERT for medical text understanding
            model_name = settings.huggingface_model
            logger.info(f"Loading clinical NLP model: {model_name}")

            self.tokenizers["clinical"] = AutoTokenizer.from_pretrained(model_name)
            self.models["clinical"] = AutoModel.from_pretrained(model_name)
            self.models["clinical"].to(self.device)

            # Sentence transformer for embeddings
            self.embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")

            # Summarization pipeline
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=0 if torch.cuda.is_available() else -1,
            )

            # Named Entity Recognition for medical entities
            self.ner_pipeline = pipeline(
                "ner",
                model="d4data/biomedical-ner-all",
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1,
            )

            logger.info("NLP models initialized successfully")

        except (ImportError, OSError, RuntimeError) as e:
            logger.error(f"Failed to initialize NLP models: {e}")
            self._initialize_fallback_models()

    def _initialize_fallback_models(self) -> None:
        """Initialize fallback models if main models fail"""
        try:
            logger.warning("Initializing fallback NLP models")

            # Use simpler models as fallback
            self.tokenizers["clinical"] = BertTokenizer.from_pretrained(
                "bert-base-uncased"
            )
            self.models["clinical"] = BertModel.from_pretrained("bert-base-uncased")
            self.models["clinical"].to(self.device)

            self.embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")

            # Simple summarization
            self.summarizer = pipeline(
                "summarization", model="sshleifer/distilbart-cnn-12-6"
            )

            logger.info("Fallback NLP models initialized")

        except (ImportError, OSError, RuntimeError) as e:
            logger.error(f"Failed to initialize fallback models: {e}")
            self.models = {}
            self.tokenizers = {}

    async def extract_medical_entities(self, text: str) -> Dict[str, Any]:
        """Extract medical entities from text"""
        try:
            # Clean text
            cleaned_text = self._clean_medical_text(text)

            # Use NER pipeline if available
            if hasattr(self, "ner_pipeline") and self.ner_pipeline is not None:
                entities = self.ner_pipeline(cleaned_text)

                # Process and categorize entities
                processed_entities = []
                for entity in entities:
                    processed_entities.append(
                        ExtractedEntity(
                            entity_type=self._map_entity_type(entity["entity_group"]),
                            text=entity["word"],
                            confidence=float(entity["score"]),
                            start_pos=int(entity["start"]),
                            end_pos=int(entity["end"]),
                        )
                    )
            else:
                # Fallback: rule-based entity extraction
                processed_entities = self._rule_based_entity_extraction(cleaned_text)

            # Categorize entities
            categorized = self._categorize_entities(processed_entities)

            return {
                "entities": [entity.dict() for entity in processed_entities],
                "categorized": categorized,
                "entity_count": len(processed_entities),
                "text_length": len(text),
            }

        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to extract medical entities: {e}")
            return {
                "entities": [],
                "categorized": {},
                "entity_count": 0,
                "text_length": len(text),
                "error": str(e),
            }

    def _clean_medical_text(self, text: str) -> str:
        """Clean and preprocess medical text"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep medical abbreviations
        text = re.sub(r"[^\w\s\.\,\;\:\-\(\)\/]", "", text)

        # Normalize common medical abbreviations
        abbreviations = {
            "pt": "patient",
            "hx": "history",
            "dx": "diagnosis",
            "tx": "treatment",
            "rx": "prescription",
            "sx": "symptoms",
        }

        for abbr, full in abbreviations.items():
            text = re.sub(rf"\b{abbr}\b", full, text, flags=re.IGNORECASE)

        return text.strip()

    def _map_entity_type(self, entity_group: str) -> str:
        """Map NER entity groups to medical categories"""
        mapping = {
            "DISEASE": "diagnosis",
            "CHEMICAL": "medication",
            "GENE": "genetic_factor",
            "SPECIES": "organism",
            "CELL_LINE": "cell_type",
            "CELL_TYPE": "cell_type",
            "DNA": "genetic_factor",
            "RNA": "genetic_factor",
            "PROTEIN": "protein",
        }
        return mapping.get(entity_group.upper(), "other")

    def _rule_based_entity_extraction(self, text: str) -> List[ExtractedEntity]:
        """Fallback rule-based entity extraction"""
        entities = []

        # Common medication patterns
        medication_patterns = [
            r"\b\w+cillin\b",  # antibiotics
            r"\b\w+statin\b",  # statins
            r"\b\w+pril\b",  # ACE inhibitors
            r"\b\w+sartan\b",  # ARBs
            r"\b\w+lol\b",  # beta blockers
        ]

        for pattern in medication_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(
                    ExtractedEntity(
                        entity_type="medication",
                        text=match.group(),
                        confidence=0.7,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )

        # Common diagnosis patterns
        diagnosis_patterns = [
            r"\b(diabetes|hypertension|cancer|pneumonia|infection)\b",
            r"\b(heart failure|myocardial infarction|stroke)\b",
            r"\b(depression|anxiety|bipolar)\b",
        ]

        for pattern in diagnosis_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(
                    ExtractedEntity(
                        entity_type="diagnosis",
                        text=match.group(),
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )

        return entities

    def _categorize_entities(
        self, entities: List[ExtractedEntity]
    ) -> Dict[str, List[str]]:
        """Categorize extracted entities"""
        categorized: Dict[str, List[str]] = {
            "diagnoses": [],
            "medications": [],
            "procedures": [],
            "allergies": [],
            "symptoms": [],
            "other": [],
        }

        for entity in entities:
            if entity.entity_type == "diagnosis":
                categorized["diagnoses"].append(entity.text)
            elif entity.entity_type == "medication":
                categorized["medications"].append(entity.text)
            elif entity.entity_type == "procedure":
                categorized["procedures"].append(entity.text)
            elif entity.entity_type == "allergy":
                categorized["allergies"].append(entity.text)
            elif entity.entity_type == "symptom":
                categorized["symptoms"].append(entity.text)
            else:
                categorized["other"].append(entity.text)

        # Remove duplicates
        for key in categorized:
            categorized[key] = list(set(categorized[key]))

        return categorized

    async def summarize_medical_text(
        self, text: str, max_length: int = 150
    ) -> Dict[str, Any]:
        """Summarize medical text"""
        try:
            if len(text) < 100:
                return {
                    "summary": text,
                    "original_length": len(text),
                    "summary_length": len(text),
                    "compression_ratio": 1.0,
                }

            # Use summarization pipeline
            if hasattr(self, "summarizer") and self.summarizer is not None:
                # Chunk text if too long
                max_input_length = 1024
                if len(text) > max_input_length:
                    chunks = [
                        text[i : i + max_input_length]
                        for i in range(0, len(text), max_input_length)
                    ]
                    summaries = []

                    for chunk in chunks:
                        if len(chunk.strip()) > 50:  # Only summarize meaningful chunks
                            summary = self.summarizer(
                                chunk,
                                max_length=max_length // len(chunks),
                                min_length=20,
                                do_sample=False,
                            )
                            summaries.append(summary[0]["summary_text"])

                    final_summary = " ".join(summaries)
                else:
                    summary = self.summarizer(
                        text, max_length=max_length, min_length=30, do_sample=False
                    )
                    final_summary = summary[0]["summary_text"]
            else:
                # Fallback: extractive summarization
                final_summary = self._extractive_summarization(text, max_length)

            return {
                "summary": final_summary,
                "original_length": len(text),
                "summary_length": len(final_summary),
                "compression_ratio": len(final_summary) / len(text),
            }

        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to summarize text: {e}")
            return {
                "summary": text[:max_length] + "..."
                if len(text) > max_length
                else text,
                "original_length": len(text),
                "summary_length": min(len(text), max_length),
                "compression_ratio": min(1.0, max_length / len(text)),
                "error": str(e),
            }

    def _extractive_summarization(self, text: str, max_length: int) -> str:
        """Simple extractive summarization as fallback"""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return text[:max_length]

        # Score sentences by length and medical keywords
        medical_keywords = [
            "patient",
            "diagnosis",
            "treatment",
            "medication",
            "symptoms",
            "condition",
            "therapy",
            "procedure",
            "test",
            "result",
        ]

        scored_sentences = []
        for sentence in sentences:
            score = len(sentence)  # Prefer longer sentences
            for keyword in medical_keywords:
                if keyword.lower() in sentence.lower():
                    score += 50
            scored_sentences.append((score, sentence))

        # Sort by score and select top sentences
        scored_sentences.sort(reverse=True)

        summary = ""
        for score, sentence in scored_sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + ". "
            else:
                break

        return summary.strip()

    async def semantic_search(
        self, query: str, db, patient_id: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Perform semantic search on medical records"""
        try:
            if not self.embeddings_model:
                return {"matches": [], "error": "Embeddings model not available"}

            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query])

            # Get medical records from database
            if patient_id:
                records_query = """
                    SELECT id, patient_id, content, record_type, created_at
                    FROM medical_records
                    WHERE patient_id = ?
                    ORDER BY created_at DESC
                """
                params = [patient_id]
            else:
                records_query = """
                    SELECT id, patient_id, content, record_type, created_at
                    FROM medical_records
                    ORDER BY created_at DESC
                    LIMIT 1000
                """
                params = []

            records = await db.execute_query(records_query, params)

            if not records:
                return {"matches": [], "message": "No medical records found"}

            # Calculate similarities
            matches = []
            for record in records:
                record_id, pat_id, content, record_type, created_at = record

                if len(content.strip()) < 10:
                    continue

                # Generate embedding for record content
                record_embedding = self.embeddings_model.encode([content])

                # Calculate cosine similarity
                similarity = np.dot(query_embedding[0], record_embedding[0]) / (
                    np.linalg.norm(query_embedding[0])
                    * np.linalg.norm(record_embedding[0])
                )

                matches.append(
                    {
                        "record_id": record_id,
                        "patient_id": pat_id,
                        "content": content[:500] + "..."
                        if len(content) > 500
                        else content,
                        "record_type": record_type,
                        "similarity_score": float(similarity),
                        "created_at": created_at,
                    }
                )

            # Sort by similarity and return top matches
            matches.sort(key=lambda x: x["similarity_score"], reverse=True)

            return {
                "matches": matches[:limit],
                "total_records_searched": len(records),
                "query": query,
            }

        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return {"matches": [], "error": str(e), "query": query}

    async def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            if not self.embeddings_model:
                raise ValueError("Embeddings model not available")

            embeddings = self.embeddings_model.encode(texts)
            return embeddings

        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return np.array([])

    async def classify_medical_text(self, text: str) -> Dict[str, Any]:
        """Classify medical text into categories"""
        try:
            # Simple rule-based classification
            categories = {
                "clinical_note": 0,
                "lab_report": 0,
                "discharge_summary": 0,
                "prescription": 0,
                "imaging_report": 0,
            }

            text_lower = text.lower()

            # Clinical note indicators
            if any(
                word in text_lower
                for word in ["patient", "examination", "assessment", "plan"]
            ):
                categories["clinical_note"] += 1

            # Lab report indicators
            if any(
                word in text_lower
                for word in ["lab", "test", "result", "normal", "abnormal", "reference"]
            ):
                categories["lab_report"] += 1

            # Discharge summary indicators
            if any(
                word in text_lower
                for word in ["discharge", "admission", "hospital", "summary"]
            ):
                categories["discharge_summary"] += 1

            # Prescription indicators
            if any(
                word in text_lower
                for word in ["medication", "prescription", "dose", "mg", "tablet"]
            ):
                categories["prescription"] += 1

            # Imaging report indicators
            if any(
                word in text_lower
                for word in ["x-ray", "ct", "mri", "ultrasound", "imaging"]
            ):
                categories["imaging_report"] += 1

            # Determine primary category
            primary_category = max(categories, key=lambda k: categories[k])
            confidence = (
                categories[primary_category] / sum(categories.values())
                if sum(categories.values()) > 0
                else 0
            )

            return {
                "primary_category": primary_category,
                "confidence": confidence,
                "all_scores": categories,
            }

        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to classify medical text: {e}")
            return {"primary_category": "unknown", "confidence": 0.0, "error": str(e)}
