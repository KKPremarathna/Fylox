from sqlalchemy.orm import Session
from backend.policies.models import PolicyDocument, PolicyChunk
from backend.policies.schemas import PolicyDocumentCreate, PolicySearchResultItem

def ingest_markdown_policy(db: Session, payload: PolicyDocumentCreate) -> PolicyDocument:
    """
    Persists a markdown policy and splits it into searchable chunks preserving order.
    """
    doc = PolicyDocument(
        title=payload.title,
        version=payload.version,
        content=payload.content,
        effective_from=payload.effective_from,
        status="APPROVED"
    )
    db.add(doc)
    db.flush()

    # Simple heuristic Markdown chunking
    # Split by double newline to separate paragraphs/sections
    blocks = [b.strip() for b in payload.content.split("\n\n") if b.strip()]
    
    current_heading = None
    chunk_index = 0
    
    for block in blocks:
        if block.startswith("#"):
            # Update heading context, but keep it as a chunk if it has substantial meaning, 
            # or just register the heading.
            # Easiest: strip the markdown '#' characters for the clean heading constraint.
            current_heading = block.lstrip("#").strip()
            # If the block is ONLY a heading, we can skip creating a chunk for it alone, 
            # but usually it's safest to just chunk it too so its keywords are searchable.
        
        # Avoid tiny useless chunks like whitespace or just 2 letter words
        if len(block) > 10:
            chunk = PolicyChunk(
                document_id=doc.id,
                section_heading=current_heading,
                content_snippet=block,
                chunk_index=chunk_index
            )
            db.add(chunk)
            chunk_index += 1

    db.commit()
    db.refresh(doc)
    return doc


def search_policies(db: Session, query: str) -> list[PolicySearchResultItem]:
    """
    Retrieves snippets matching the query from APPROVED documents using a python-level text heuristic.
    This acts as a transparent, fully deterministic mock stand-in for future pgvector embeddings.
    """
    query = query.strip().lower()
    if not query:
        return []
    
    # 1. Fetch all chunks attached strictly to APPROVED policies.
    chunks = db.query(PolicyChunk).join(PolicyDocument).filter(
        PolicyDocument.status == "APPROVED"
    ).all()

    query_tokens = set(query.split())
    scored_results = []
    
    for chunk in chunks:
        text_lower = chunk.content_snippet.lower()
        heading_lower = (chunk.section_heading or "").lower()
        title_lower = chunk.document.title.lower()
        
        score = 0.0
        # Basic BM25/TF-IDF mock logic relying purely on term incidence overlapping
        for token in query_tokens:
            if token in text_lower:
                score += 1.0
            if token in heading_lower:
                score += 1.5
            if token in title_lower:
                score += 2.0
                
        if score > 0:
            scored_results.append((score, chunk))
            
    # Sort by descending relevance_score
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    # Map cleanly to explicit search payload requirements and clamp limits
    out = []
    for score, chunk in scored_results[:10]:
        out.append(
            PolicySearchResultItem(
                document_title=chunk.document.title,
                version=chunk.document.version,
                effective_date=chunk.document.effective_from,
                section_heading=chunk.section_heading,
                snippet_text=chunk.content_snippet,
                relevance_score=score,
            )
        )
        
    return out
