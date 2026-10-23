import re

from sqlalchemy.orm import Session, joinedload

from backend.policies.models import (
    PolicyChunk,
    PolicyDocument,
)
from backend.policies.schemas import (
    PolicyDocumentCreate,
    PolicySearchResultItem,
)


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at",
    "be", "been", "but", "by", "can",
    "could", "do", "does", "for", "from",
    "had", "has", "have", "i", "if",
    "in", "is", "it", "its", "me", "my",
    "of", "on", "or", "our", "please",
    "the", "their", "them", "there",
    "this", "to", "was", "we", "were",
    "will", "with", "would", "you", "your",
}


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            value.casefold(),
        )
        if len(token) > 1 and token not in STOP_WORDS
    }


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
    Rank approved chunks using English whole-token overlap.

    Ranking does not establish policy applicability.
    """
    query_tokens = tokenize(query)

    if not query_tokens:
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

    scored_results = []

    for chunk in chunks:
        content_tokens = tokenize(
            chunk.content_snippet
        )
        heading_tokens = tokenize(
            chunk.section_heading or ""
        )
        title_tokens = tokenize(
            chunk.document.title
        )

        content_matches = query_tokens & content_tokens
        heading_matches = query_tokens & heading_tokens
        title_matches = query_tokens & title_tokens

        if not content_matches and not heading_matches:
            continue

        score = (
            len(content_matches)
            + 1.5 * len(heading_matches)
            + 0.5 * len(title_matches)
        )

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
            effective_date=chunk.document.effective_from,
            section_heading=chunk.section_heading,
            snippet_text=chunk.content_snippet,
            relevance_score=score,
        )
        for score, chunk in scored_results[:10]
    ]