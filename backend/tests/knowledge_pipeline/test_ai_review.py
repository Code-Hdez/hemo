from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = PROJECT_ROOT / "knowledge_base" / "scripts"
AI_REVIEW_DIR = SCRIPTS_DIR / "ai_review"
for candidate in (SCRIPTS_DIR, AI_REVIEW_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def test_canonical_source_uses_batch_source_file_over_candidate_source_id() -> None:
    from ai_review_common import build_batch_index, canonical_source_for_metadata

    report = {
        "records": [
            {
                "source_id": "cowell_pdf",
                "source_file": "Cowell.pdf",
                "batches": [
                    {
                        "staging_markdown_path": "knowledge_base/staging_md/cowell_pdf__pages_0001_0050.docling.md",
                    }
                ],
            },
            {
                "source_id": "bsava_pdf",
                "source_file": "BSAVA.pdf",
                "batches": [
                    {
                        "staging_markdown_path": "knowledge_base/staging_md/bsava_pdf__pages_0001_0050.docling.md",
                    }
                ],
            },
        ]
    }
    metadata = {
        "source_id": "cowell_pdf",
        "source_file": "bsava_pdf__pages_0001_0050.docling.md",
    }

    batch_index = build_batch_index(report)

    assert canonical_source_for_metadata(metadata, batch_index) == "bsava_pdf"


def test_classification_rejects_contributors_and_routes_broken_tables_to_human() -> None:
    from ai_review_common import classify_candidate

    contributor = classify_candidate(
        metadata={
            "title": "Jane Example, DVM, PhD, DACVP",
            "quality_flags": ["species_uncertain", "very_short_section"],
            "contains_tables": False,
        },
        body="# Jane Example, DVM, PhD, DACVP\n\nAssistant Professor University Contributor",
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )
    broken_table = classify_candidate(
        metadata={
            "title": "Reference intervals",
            "quality_flags": ["possible_broken_table", "requires_manual_table_review"],
            "contains_tables": True,
            "contains_ranges_or_units": True,
        },
        body="# Reference intervals\n\n| RBC | HCT |\n| 5.5 |",
        validation_record={
            "classification": "warning",
            "errors": [],
            "warnings": [
                "quality_flag:possible_broken_table",
                "quality_flag:requires_manual_table_review",
            ],
        },
    )

    assert contributor.decision == "rejected"
    assert "contributors_like_content" in contributor.reason_codes
    assert broken_table.decision == "needs_human_review"
    assert "requires_manual_table_review" in broken_table.reason_codes


def test_classification_rejects_acknowledgments_and_author_chapter_lists() -> None:
    from ai_review_common import classify_candidate

    acknowledgment = classify_candidate(
        metadata={
            "title": "Acknowledgment",
            "quality_flags": [],
            "contains_tables": False,
            "contains_ranges_or_units": True,
            "species": "canine_feline",
        },
        body=(
            "# Acknowledgment\n\n"
            "The authors wish to acknowledge the contributions of previous chapter authors.\n\n"
            "1. Craig FE, Foon KA. Flow cytometric immunophenotyping for hematologic neoplasms. Blood. 2008.\n"
            "2. Avery AC. Molecular diagnostics of hematologic malignancies in small animals. Vet Clin North Am Small Anim Pract. 2012.\n"
            "3. Burkhard MJ, Bienzle D. Making sense of lymphoma diagnostics in small animal patients. Vet Clin North Am Small Anim Pract. 2013."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )
    author_chapter_list = classify_candidate(
        metadata={
            "title": "Rick L. Cowell, DVM, MS, DACVP",
            "quality_flags": ["species_uncertain", "very_short_section"],
            "contains_tables": False,
        },
        body=(
            "# Rick L. Cowell, DVM, MS, DACVP\n\n"
            "Clinical Pathologist Stillwater, Oklahoma Sample Collection and Preparation "
            "Cell Types and Criteria of Malignancy Selected Infectious Agents "
            "Transtracheal and Bronchoalveolar Washes The Kidneys The Spleen "
            "The Reproductive Tract and Cytology of Cutaneous and Subcutaneous Lesions"
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert acknowledgment.decision == "rejected"
    assert "editorial_or_legal_content" in acknowledgment.reason_codes
    assert author_chapter_list.decision == "rejected"
    assert "contributors_like_content" in author_chapter_list.reason_codes


def test_classification_routes_damaged_chapter_titles_to_human_review() -> None:
    from ai_review_common import classify_candidate

    damaged_title = classify_candidate(
        metadata={
            "title": "C H A P T E R 1 1",
            "quality_flags": [],
            "contains_tables": False,
            "contains_ranges_or_units": True,
            "species": "canine_feline",
        },
        body=(
            "# C H A P T E R 1 1\n\n"
            "Primary hyperparathyroidism increases calcium and phosphorus absorption from the intestine, "
            "releases minerals from bone, and affects renal phosphate excretion. "
            "Renal secondary hyperparathyroidism occurs with chronic renal failure and altered vitamin D activation. "
            "The serum calcium concentration may decrease, phosphate may be retained, and parathyroid hormone "
            "secretion may increase. The text discusses canine and feline laboratory interpretation of renal, "
            "endocrine, blood, cell, and diagnostic findings."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert damaged_title.decision == "needs_human_review"
    assert "damaged_or_missing_title" in damaged_title.reason_codes


def test_classification_routes_ocr_corrupted_clinical_text_to_human_review() -> None:
    from ai_review_common import classify_candidate

    corrupted = classify_candidate(
        metadata={
            "title": "DIAGNOSTIC PROPERTIES AND PRED1CTNE VALUE OF lA.BORATORY ASSAYS",
            "quality_flags": ["species_uncertain"],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "unknown",
        },
        body=(
            "# DIAGNOSTIC PROPERTIES AND PRED1CTNE VALUE OF lA.BORATORY ASSAYS\n\n"
            "A frequent purpost of analyzing a patient sample is to detect or confirm th. p, ... nce of disease. "
            "If a laboratory test r~ult is ouuid. the r~f~rence interval, how likdy is it th.t the pati~nt has a disorder? "
            "The following information is an introduction to diagnostic value of laboratory assays and pred1ctne value. "
            "TP true p05itive, TN true nq;ative, FP faJse p05itive, and FN faJse negative are used for classification."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert corrupted.decision == "needs_human_review"
    assert "ocr_corruption" in corrupted.reason_codes


def test_classification_routes_short_ocr_corrupted_text_to_human_review() -> None:
    from ai_review_common import classify_candidate

    corrupted = classify_candidate(
        metadata={
            "title": "Tissue l.ukocyt ..",
            "quality_flags": ["species_uncertain"],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "unknown",
        },
        body=(
            "# Tissue l.ukocyt ..\n\n"
            "Granulocytes ptrform their role in host d.£.Jl5t and di. "
            "Lymphocytes may undergo bl:astogt'nesis, mum to blood vi. lymphatic ~ or die. "
            "Monocyte. tr:msform into hisliocytes or macrophage; that :if. cop.bJ. of mito,;s."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert corrupted.decision == "needs_human_review"
    assert "ocr_corruption" in corrupted.reason_codes


def test_classification_rejects_reference_title_sections() -> None:
    from ai_review_common import classify_candidate

    reference_section = classify_candidate(
        metadata={
            "title": "Weiss DJ . Antibody - mediated suppression of erythropoiesis in dogs with red cell aplasia . Am J Vet Res 1986 ; 47 : 26",
            "quality_flags": [],
            "contains_tables": False,
            "contains_ranges_or_units": True,
            "species": "canine",
        },
        body=(
            "# Weiss DJ . Antibody - mediated suppression of erythropoiesis in dogs with red cell aplasia . Am J Vet Res 1986 ; 47 : 26\n\n"
            "58. Weinkle TK, Center SA, Randolph JF, et al. Evaluation of prognostic factors in dogs. J Am Vet Med Assoc 2005; 226: 1869-1880.\n"
            "59. Weiss DJ. Bone marrow pathology in dogs and cats with nonregenerative immune-mediated haemolytic anaemia. J Comp Pathol 2008; 138: 46-53.\n"
            "60. Wilkerson MJ, Davis E, Shuman W, et al. Isotype-specific antibodies in horses and dogs with immune-mediated hemolytic anemia. Vet Immunol Immunopathol 2000; 72: 113-124."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert reference_section.decision == "rejected"
    assert "bibliographic_reference_title" in reference_section.reason_codes


def test_classification_routes_reference_tail_contamination_to_human_review() -> None:
    from ai_review_common import classify_candidate

    contaminated = classify_candidate(
        metadata={
            "title": "SUMMARY",
            "quality_flags": [],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "feline",
        },
        body=(
            "# SUMMARY\n\n"
            "Monocytes, macrophages and dendritic cells are important hematopoietic cells that play critical roles in defense and homeostasis. "
            "Monocytes can indicate the health of the myelomonocytic lineage and tissue macrophages affect disease interpretation.\n\n"
            "1. Ardavin C. Origin, precursors and differentiation of mouse dendritic cells. Nat Rev Immunol 2003; 3: 582-590.\n"
            "2. Bienzle D, Reggeti F, Clark ME, et al. Immunophenotype and functional properties of feline dendritic cells. Vet Immunol Immunopathol 2003; 96: 19-30.\n"
            "3. Hume DA, Ross IL, Himes SR, et al. The mononuclear phagocyte system revisited. J Leukoc Biol 2002; 72: 621-627.\n"
            "4. Randolph GJ, Inaba K, Robbiani DF, et al. Differentiation of phagocytic monocytes. Science 1999; 282: 480-483."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert contaminated.decision == "needs_human_review"
    assert "bibliography_contamination" in contaminated.reason_codes


def test_classification_routes_sentence_fragment_titles_to_human_review() -> None:
    from ai_review_common import classify_candidate

    fragment_title = classify_candidate(
        metadata={
            "title": "analysis, frequently result in reaching of maximal allowable amounts, and can lead to iatrogenic decreases in RBC mass.",
            "quality_flags": ["species_uncertain"],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "unknown",
        },
        body=(
            "# analysis, frequently result in reaching of maximal allowable amounts, and can lead to iatrogenic decreases in RBC mass.\n\n"
            "Interim sampling can be done in rats, although the overall amount of blood and frequency of bleeding will be limited. "
            "Typically samples for hematological analysis are collected in microtainer tubes to achieve an adequate blood to anticoagulant ratio. "
            "The text discusses blood collection, erythrocyte mass, hematology analyzers, anticoagulant handling, and sample interpretation."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert fragment_title.decision == "needs_human_review"
    assert "damaged_or_missing_title" in fragment_title.reason_codes


def test_classification_rejects_short_author_name_chapter_lists_without_credentials() -> None:
    from ai_review_common import classify_candidate

    author_list = classify_candidate(
        metadata={
            "title": "V.E. TED VALLI and ROBERT M. JACOBS",
            "quality_flags": ["domain_uncertain", "very_short_section"],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "feline",
        },
        body=(
            "# V.E. TED VALLI and ROBERT M. JACOBS\n\n"
            "Hemopoietic System Cells and Organs Functional Anatomy of the Hemopoietic System "
            "Thymus BLV, bovine leukemia virus; FeLV, feline leukemia virus; MALT, mucosa-associated lymphoid tissue; "
            "MHC, major histocompatibility complex; TCR, T cell receptor genes; RBC, red blood cell."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert author_list.decision == "rejected"
    assert "contributors_like_content" in author_list.reason_codes


def test_classification_routes_author_titled_clinical_sections_to_human_review() -> None:
    from ai_review_common import classify_candidate

    author_titled = classify_candidate(
        metadata={
            "title": "Laia Solano-Gallego and Gad Baneth",
            "quality_flags": [],
            "contains_tables": False,
            "contains_ranges_or_units": False,
            "species": "canine_feline",
        },
        body=(
            "# Laia Solano-Gallego and Gad Baneth\n\n"
            "Protozoal and arthropod-borne infections cause important diseases in dogs and cats. "
            "Some diseases are endemic because they are transmitted by vectors restricted by geographical boundaries. "
            "The chapter describes diagnosis of protozoal and arthropod-borne diseases of dogs and cats, "
            "with distribution, transmission modes, clinical signs, clinicopathological abnormalities, "
            "diagnostic testing and recommendations for monitoring."
        ),
        validation_record={"classification": "valid_candidate", "errors": [], "warnings": []},
    )

    assert author_titled.decision == "needs_human_review"
    assert "author_title_requires_relabeling" in author_titled.reason_codes


def test_ai_frontmatter_never_marks_expert_reviewed() -> None:
    from ai_review_common import ReviewDecision, apply_review_frontmatter

    metadata = {
        "source_id": "cowell_original",
        "title": "Neutrophils",
        "status": "needs_expert_review",
        "review_required": True,
        "curation_level": "machine_precleaned",
    }
    decision = ReviewDecision(
        decision="approved_provisional",
        confidence="high",
        reason_codes=["clinically_useful_text"],
        short_reason="Useful clinical text with adequate context.",
        content_type="clinical_text",
        risk_level="low",
        recommended_for_rag=True,
    )

    reviewed = apply_review_frontmatter(
        metadata=metadata,
        decision=decision,
        canonical_source_id="cowell_pdf",
        reviewed_at="2026-06-30T12:00:00+00:00",
    )

    assert reviewed["status"] == "ai_approved_provisional"
    assert reviewed["reviewer"] == "codex_ai_reviewer"
    assert reviewed["curation_level"] == "ai_veterinary_screened_provisional"
    assert reviewed["rag_eligible"] is True
    assert reviewed["expert_reviewed"] is False
    assert reviewed["original_source_id"] == "cowell_original"
    assert reviewed["canonical_source_id"] == "cowell_pdf"


def test_provisional_chunks_only_include_approved_candidate_sources() -> None:
    from ai_review_common import filter_chunks_for_approved_candidates

    chunks = [
        {
            "chunk_id": "approved",
            "source_id": "cowell_original",
            "source_file": "cowell_pdf__pages_0001_0050.docling.md",
            "section_file": "knowledge_base/curated_candidates/cytology/approved.md",
            "text": "Neutrophils are segmented granulocytes.",
        },
        {
            "chunk_id": "rejected",
            "source_id": "cowell_original",
            "source_file": "cowell_pdf__pages_0001_0050.docling.md",
            "section_file": "knowledge_base/curated_candidates/cytology/rejected.md",
            "text": "Copyright page.",
        },
        {
            "chunk_id": "orphan",
            "source_id": "cowell_original",
            "source_file": "cowell_pdf__pages_0001_0050.docling.md",
            "section_file": "knowledge_base/curated_candidates/cytology/missing.md",
            "text": "No source.",
        },
    ]

    filtered = filter_chunks_for_approved_candidates(
        chunks=chunks,
        approved_original_paths={"knowledge_base/curated_candidates/cytology/approved.md"},
        canonical_source_id="cowell_pdf",
        book_title="Cowell",
    )

    assert len(filtered) == 1
    assert filtered[0]["original_chunk_id"] == "approved"
    assert filtered[0]["ai_review_status"] == "approved_provisional"
    assert filtered[0]["rag_eligible"] is True
    assert filtered[0]["expert_reviewed"] is False


def test_copy_reviewed_markdown_is_idempotent_for_same_source(tmp_path: Path) -> None:
    from ai_review_common import copy_reviewed_markdown

    source = tmp_path / "source_section.md"
    destination = tmp_path / "reviewed"
    destination.mkdir()
    source.write_text("# Source\n", encoding="utf-8")

    first = copy_reviewed_markdown(
        source_path=source,
        destination_dir=destination,
        metadata={"title": "Source section", "status": "ai_approved_provisional"},
        body="# Source section\n\nFirst version.",
    )
    second = copy_reviewed_markdown(
        source_path=source,
        destination_dir=destination,
        metadata={"title": "Source section", "status": "ai_approved_provisional"},
        body="# Source section\n\nSecond version.",
    )

    reviewed_files = list(destination.glob("*.md"))
    assert first == second
    assert len(reviewed_files) == 1
    assert "Second version." in first.read_text(encoding="utf-8")
    assert "ai_review_original_path:" in first.read_text(encoding="utf-8")


def test_match_candidate_by_filename_requires_unique_match() -> None:
    from ai_review_common import match_candidate_by_filename

    pending = Path("knowledge_base/expert_review/pending/example.md")
    unique = [Path("knowledge_base/curated_candidates/cytology/example.md")]
    duplicated = [
        Path("knowledge_base/curated_candidates/cytology/example.md"),
        Path("knowledge_base/curated_candidates/hematology/example.md"),
    ]

    assert match_candidate_by_filename(pending, unique) == unique[0]
    assert match_candidate_by_filename(pending, duplicated) is None
