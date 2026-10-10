from sqlalchemy.orm import Session, joinedload

from backend.policies.models import (
    PolicyChunk,
    PolicyDocument,
)
from backend.policies.schemas import (
    PolicyDocumentCreate,
    PolicySearchResultItem,
)


def ingest_markdown_policy(
    db: Session,
    payload: PolicyDocumentCreate,
) -> PolicyDocument:
    """
    Store a policy document and its ordered text chunks.
    """
    document = PolicyDocument(
        title=payload.title,
        version=payload.version,
        content=payload.content,
        effective_from=payload.effective_from,
        status="APPROVED",
    )

    db.add(document)
    db.flush()

    blocks = [
        block.strip()
        for block in payload.content.split("\n\n")
        if block.strip()
    ]

    current_heading = None
    chunk_index = 0

    for block in blocks:
        if block.startswith("#"):
            current_heading = block.lstrip("#").strip()

        if len(block) > 10:
            chunk = PolicyChunk(
                document_id=document.id,
                section_heading=current_heading,
                content_snippet=block,
                chunk_index=chunk_index,
            )

            db.add(chunk)
            chunk_index += 1

    db.commit()
    db.refresh(document)

    return document


def search_policies(
    db: Session,
    query: str,
) -> list[PolicySearchResultItem]:
    """
    Return approved policy chunks using deterministic
    keyword-overlap scoring.
    """
    normalized_query = query.strip().lower()

    if not normalized_query:
        return []

    chunks = (
        db.query(PolicyChunk)
        .join(PolicyDocument)
        .options(joinedload(PolicyChunk.document))
        .filter(
            PolicyDocument.status == "APPROVED"
        )
        .all()
    )

    query_tokens = set(normalized_query.split())
    scored_results = []

    for chunk in chunks:
        text_lower = chunk.content_snippet.lower()

        heading_lower = (
            chunk.section_heading or ""
        ).lower()

        title_lower = chunk.document.title.lower()

        score = 0.0

        for token in query_tokens:
            if token in text_lower:
                score += 1.0

            if token in heading_lower:
                score += 1.5

            if token in title_lower:
                score += 2.0

        if score > 0:
            scored_results.append((score, chunk))

    scored_results.sort(
        key=lambda item: (
            -item[0],
            item[1].document_id,
            item[1].chunk_index,
            item[1].id,
        )
    )

    return [
        PolicySearchResultItem(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            document_title=chunk.document.title,
            version=chunk.document.version,
            effective_date=(
                chunk.document.effective_from
            ),
            section_heading=chunk.section_heading,
            snippet_text=chunk.content_snippet,
            relevance_score=score,
        )
        for score, chunk in scored_results[:10]
    ]