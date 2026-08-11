from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import ExtractedFactModel
from app.services.llm import llm


class SourcePointer(BaseModel):
    document_id: int
    page_number: int | None = None
    section: str | None = None
    chunk_id: int


class ExtractedFact(BaseModel):
    fact: str
    value: str
    source: SourcePointer


class FactExtractionResult(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)


def extract_facts(
    document_id: int,
    chunk_id: int,
    content: str,
    page_number: int | None,
    section: str | None,
) -> FactExtractionResult:
    prompt = f"""
You are a document fact extraction system.

Extract ONLY facts explicitly stated in the source text.
Do not infer, assume, or use outside knowledge.

Source metadata:
document_id: {document_id}
chunk_id: {chunk_id}
page_number: {page_number}
section: {section}

Source text:
---
{content}
---

Extract useful business facts such as:
parties, amounts, dates, payment terms,
obligations, contract terms, and invoice details.

Every fact must be supported by the source text.
"""

    structured_llm = llm.with_structured_output(FactExtractionResult)

    return structured_llm.invoke(prompt)

    for fact in result.facts:
        fact.source.document_id = document_id
        fact.source.chunk_id = chunk_id
        fact.source.page_number = page_number
        fact.source.section = section
        
    return result

def save_extracted_facts(
    db: Session,
    result: FactExtractionResult,
) -> list[ExtractedFactModel]:
    saved = []

    for fact in result.facts:
        model = ExtractedFactModel(
            document_id=fact.source.document_id,
            chunk_id=fact.source.chunk_id,
            fact=fact.fact,
            value=fact.value,
            page_number=fact.source.page_number,
            section=fact.source.section,
        )

        db.add(model)
        saved.append(model)

    db.commit()

    for model in saved:
        db.refresh(model)

    return saved