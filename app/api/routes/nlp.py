import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger

from app.database.connection import get_database, DatabaseManager
from app.models.schemas import NLPProcessingRequest, NLPProcessingResponse
from app.services.nlp_service_simple import NLPService

router = APIRouter()


@router.post("/nlp/process", response_model=NLPProcessingResponse)
async def process_medical_text(
    request: NLPProcessingRequest, db: DatabaseManager = Depends(get_database)
):
    """
    Process medical text using NLP models
    """
    try:
        # Validate patient if provided
        if request.patient_id:
            patient_result = await db.execute_query(
                "SELECT id FROM patients WHERE patient_id = ?", [request.patient_id]
            )

            if not patient_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
                )

        request_id = str(uuid.uuid4())
        processed_at = datetime.utcnow()

        # Initialize NLP service
        nlp_service = NLPService()

        # Process based on task type
        if request.task == "extract_entities":
            results = await nlp_service.extract_entities(request.text)
        elif request.task == "summarize":
            results = {"summary": await nlp_service.summarize_text(request.text)}
        elif request.task == "search":
            search_results = await nlp_service.semantic_search(request.text, [])
            results = {"matches": search_results}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task. Must be 'extract_entities', 'summarize', or 'search'",
            )

        # Store processing record if patient_id provided
        if request.patient_id:
            # Get next ID for medical_records
            next_id_result = await db.execute_query(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM medical_records"
            )
            next_id = next_id_result[0][0] if next_id_result else 1

            await db.execute_query(
                """
                INSERT INTO medical_records (
                    id, patient_id, record_type, content, processed_content, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                [
                    next_id,
                    request.patient_id,
                    f"nlp_{request.task}",
                    request.text,
                    json.dumps(results),
                    processed_at,
                ],
            )

        logger.info(f"Processed NLP task '{request.task}' for request: {request_id}")

        return NLPProcessingResponse(
            request_id=request_id,
            task=request.task,
            patient_id=request.patient_id,
            processed_at=processed_at,
            results=results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process NLP request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/nlp/extract-entities")
async def extract_medical_entities(text: str, patient_id: Optional[str] = None):
    """
    Extract medical entities from text
    """
    try:
        nlp_service = NLPService()
        entities = await nlp_service.extract_entities(text)

        return {
            "text": text,
            "entities": entities,
            "entity_count": len(entities.get("entities", [])),
        }

    except Exception as e:
        logger.error(f"Failed to extract entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/nlp/summarize")
async def summarize_medical_text(
    text: str, max_length: int = 150, patient_id: Optional[str] = None
):
    """
    Summarize medical text
    """
    try:
        nlp_service = NLPService()
        summary = await nlp_service.summarize_text(text, max_length)

        return {
            "original_text": text,
            "summary": summary,
            "compression_ratio": len(summary) / len(text) if summary else 0,
        }

    except Exception as e:
        logger.error(f"Failed to summarize text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/nlp/semantic-search")
async def semantic_search(
    query: str,
    patient_id: Optional[str] = None,
    limit: int = 10,
    db: DatabaseManager = Depends(get_database),
):
    """
    Perform semantic search on medical records
    """
    try:
        nlp_service = NLPService()
        # Get documents for search
        if patient_id:
            records_query = """
                SELECT content FROM medical_records 
                WHERE patient_id = ? AND content IS NOT NULL
                ORDER BY created_at DESC LIMIT 100
            """
            records = await db.execute_query(records_query, [patient_id])
            documents = [record[0] for record in records if record[0]]
        else:
            records_query = """
                SELECT content FROM medical_records 
                WHERE content IS NOT NULL
                ORDER BY created_at DESC LIMIT 100
            """
            records = await db.execute_query(records_query)
            documents = [record[0] for record in records if record[0]]

        results = await nlp_service.semantic_search(query, documents, limit)

        return {
            "query": query,
            "results": results,
            "result_count": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to perform semantic search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/nlp/patient-records/{patient_id}")
async def get_patient_nlp_records(
    patient_id: str,
    record_type: Optional[str] = None,
    limit: int = 50,
    db: DatabaseManager = Depends(get_database),
):
    """
    Get NLP processed records for a patient
    """
    try:
        # Verify patient exists
        patient_result = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?", [patient_id]
        )

        if not patient_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        query = """
            SELECT id, record_type, content, processed_content, created_at
            FROM medical_records 
            WHERE patient_id = ?
        """
        params = [patient_id]

        if record_type:
            query += " AND record_type = ?"
            params.append(record_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(str(limit))

        result = await db.execute_query(query, params)

        records = []
        for row in result:
            record_id, rec_type, content, processed_content, created_at = row
            records.append(
                {
                    "id": record_id,
                    "record_type": rec_type,
                    "content": content,
                    "processed_content": json.loads(processed_content)
                    if processed_content
                    else None,
                    "created_at": created_at,
                }
            )

        return {
            "patient_id": patient_id,
            "records": records,
            "total_records": len(records),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get NLP records for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
