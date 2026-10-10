from backend.policies.models import (
    PolicyChunk,
    PolicyDocument,
)
from backend.policies.service import search_policies


def test_search_preserves_exact_chunk_identity(
    db_session,
):
    marker = "fyloxsourceidentitycheck"

    approved_document = PolicyDocument(
        title="Approved identity-check policy",
        version="1.0",
        status="APPROVED",
        content=f"{marker} Refund review requires approval.",
    )

    draft_document = PolicyDocument(
        title="Draft identity-check policy",
        version="1.0",
        status="DRAFT",
        content=f"{marker} Refund review requires approval.",
    )

    db_session.add_all(
        [
            approved_document,
            draft_document,
        ]
    )
    db_session.flush()

    shared_text = (
        f"{marker} Refund review requires approval."
    )

    approved_chunk = PolicyChunk(
        document_id=approved_document.id,
        section_heading="Refund review",
        content_snippet=shared_text,
        chunk_index=0,
    )

    draft_chunk = PolicyChunk(
        document_id=draft_document.id,
        section_heading="Refund review",
        content_snippet=shared_text,
        chunk_index=0,
    )

    db_session.add_all(
        [
            approved_chunk,
            draft_chunk,
        ]
    )
    db_session.flush()

    results = search_policies(
        db_session,
        marker,
    )

    assert len(results) == 1

    result = results[0]

    assert result.document_id == approved_document.id
    assert result.chunk_id == approved_chunk.id
    assert result.snippet_text == shared_text

    assert result.chunk_id != draft_chunk.id