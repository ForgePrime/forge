"""Seed data — default output contracts, micro-skills, operational contract guideline.

Run: python -m seed.seed_data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models import OutputContract, MicroSkill, Guideline


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # --- Output Contracts ---
    contracts = [
        OutputContract(
            task_type="*", ceremony_level="*", version=1, active=True,
            definition={
                "required": {"reasoning": {"min_length": 50}},
                "optional": {},
                "anti_patterns": {},
            },
        ),
        OutputContract(
            task_type="feature", ceremony_level="STANDARD", version=1, active=True,
            definition={
                "required": {
                    "reasoning": {
                        "min_length": 100,
                        "must_reference_file": True,
                        "must_contain_why": True,
                    },
                    "ac_evidence": {
                        "per_criterion": True,
                        "min_length": 50,
                        "must_reference_file_or_test": True,
                        "fail_blocks": True,
                    },
                },
                "optional": {
                    "decisions": {"min_issue_length": 20, "min_recommendation_length": 30},
                    "changes": {"min_summary_length": 30, "unique_summaries": True},
                    "findings": {"min_description_length": 50, "must_reference_file": True},
                },
                "anti_patterns": {
                    "duplicate_summaries_threshold": 0.8,
                    "placeholder_patterns": ["auto-complete", "auto-recorded", "(no changes needed)"],
                    "copy_paste_evidence": True,
                },
            },
        ),
        OutputContract(
            task_type="feature", ceremony_level="FULL", version=1, active=True,
            definition={
                "required": {
                    "reasoning": {
                        "min_length": 150,
                        "must_reference_file": True,
                        "must_contain_why": True,
                    },
                    "ac_evidence": {
                        "per_criterion": True,
                        "min_length": 50,
                        "must_reference_file_or_test": True,
                        "fail_blocks": True,
                    },
                },
                "optional": {
                    "decisions": {"min_issue_length": 20, "min_recommendation_length": 30},
                    "changes": {"min_summary_length": 30, "unique_summaries": True, "min_reasoning_length": 30},
                    "findings": {"min_description_length": 50, "must_reference_file": True, "min_evidence_length": 30},
                },
                "anti_patterns": {
                    "duplicate_summaries_threshold": 0.8,
                    "placeholder_patterns": ["auto-complete", "auto-recorded", "(no changes needed)"],
                    "copy_paste_evidence": True,
                },
            },
        ),
        OutputContract(
            task_type="bug", ceremony_level="LIGHT", version=1, active=True,
            definition={
                "required": {
                    "reasoning": {"min_length": 80, "must_reference_file": True},
                },
                "optional": {
                    "changes": {"min_summary_length": 20},
                },
                "anti_patterns": {
                    "placeholder_patterns": ["auto-complete", "auto-recorded"],
                },
            },
        ),
    ]

    # --- Micro-Skills ---
    skills = [
        # Reputation frames
        MicroSkill(
            name="reputation_developer", type="reputation",
            content=(
                "Jakby ktoś powiedział że jesteś programistą który nigdy nie idzie na skróty, "
                "nie zostawia długu technicznego, nie upraszcza kosztem poprawności, "
                "zawsze wybiera rozwiązanie właściwe nie najszybsze, nie zostawia nic 'na później', "
                "dostarcza rozwiązania kompletne i finalne — to co musiałbyś zrobić w tym zadaniu?"
            ),
            applicable_to=["implement"],
            tags=["general"], relevance_score=90,
        ),
        MicroSkill(
            name="reputation_architect", type="reputation",
            content=(
                "Jakby ktoś powiedział że jesteś najlepszym architektem który "
                "zaprojektował system bez ukrytych zależności, zapewnił pełną spójność danych, "
                "wyeliminował duplikację, przewidział edge-case'y i przyszłe rozszerzenia, "
                "stworzył rozwiązanie skalowalne i odporne — to co musiałbyś zrobić?"
            ),
            applicable_to=["plan", "spec"],
            tags=["architecture"], relevance_score=90,
        ),
        MicroSkill(
            name="reputation_analyst", type="reputation",
            content=(
                "Jakby ktoś powiedział że jesteś najlepszym analitykiem biznesowym który "
                "nigdy nie pomija edge cases, zawsze definiuje wymagania precyzyjnie, "
                "rozpoznaje ukryte założenia i sprzeczności w dokumentach, "
                "i tworzy specyfikacje z których można implementować bez pytań — "
                "to co musiałbyś zrobić?"
            ),
            applicable_to=["ingest", "analyze", "spec"],
            tags=["business"], relevance_score=90,
        ),
        MicroSkill(
            name="reputation_challenger", type="reputation",
            content=(
                "Jakby ktoś powiedział że jesteś najbardziej wnikliwym QA inżynierem "
                "który nigdy nie wierzy na słowo, zawsze sprawdza kod a nie deklaracje, "
                "który znajduje luki w każdym rozwiązaniu i nie boi się powiedzieć "
                "'to nie działa mimo że testy przechodzą' — to co musiałbyś zrobić?"
            ),
            applicable_to=["challenge", "verify"],
            tags=["quality"], relevance_score=90,
        ),

        # Technique skills
        MicroSkill(
            name="impact_aware", type="technique",
            content=(
                "Zanim zmienisz plik: sprawdź kto go importuje (grep import). "
                "Sprawdź kto go wywołuje (grep function name). "
                "Dla każdego zależnego: czy Twoja zmiana go psuje? "
                "Jeśli nie sprawdzisz — wymień co mogłeś pominąć."
            ),
            applicable_to=["implement"],
            tags=["general"], relevance_score=80,
        ),
        MicroSkill(
            name="contract_first", type="technique",
            content=(
                "Najpierw interfejs, potem implementacja. "
                "Zdefiniuj input/output zanim napiszesz logikę. "
                "Napisz test zanim napiszesz kod. "
                "Interfejs to kontrakt — implementacja to szczegół."
            ),
            applicable_to=["implement"],
            tags=["general"], relevance_score=70,
        ),
        MicroSkill(
            name="ac_from_spec", type="technique",
            content=(
                "AC MUSI pochodzić ze specyfikacji feature, nie z wyobraźni. "
                "Dla każdego AC: wskaż DOKŁADNIE który element spec (rule, edge case) "
                "ten AC testuje. AC bez źródła w spec = wymyślone = bezwartościowe."
            ),
            applicable_to=["plan"],
            tags=["planning"], relevance_score=80,
        ),
        MicroSkill(
            name="edge_case_explorer", type="technique",
            content=(
                "Dla KAŻDEJ reguły biznesowej pytaj: co jeśli dane puste? "
                "Co jeśli typ inny? Co jeśli kolejność odwrotna? "
                "Co jeśli wartość na granicy? Co jeśli concurrent access? "
                "Co jeśli timeout? Każda odpowiedź 'nie wiem' = scenariusz testowy."
            ),
            applicable_to=["spec", "plan", "challenge"],
            tags=["quality"], relevance_score=75,
        ),

        # Verification skills
        MicroSkill(
            name="code_vs_declaration", type="verification",
            content=(
                "NIE wierz w deklaracje (AC evidence, reasoning). Przeczytaj FAKTYCZNY KOD. "
                "'Test passes' ≠ test testuje właściwą rzecz. "
                "'Implements protocol' ≠ implementuje wszystkie metody. "
                "Otwórz plik, przeczytaj linijkę, zweryfikuj claim."
            ),
            applicable_to=["challenge", "verify"],
            tags=["quality"], relevance_score=85,
        ),
        MicroSkill(
            name="assumption_destroyer", type="verification",
            content=(
                "Każde twierdzenie w delivery = hipoteza do obalenia. "
                "Nie pytaj 'czy to działa?' — pytaj 'w jakich warunkach to NIE działa?'. "
                "Szukaj: ukrytych zależności, edge cases, race conditions, missing error handling."
            ),
            applicable_to=["challenge"],
            tags=["quality"], relevance_score=80,
        ),
    ]

    # Upsert micro-skills by name
    for skill in skills:
        existing = db.query(MicroSkill).filter(MicroSkill.name == skill.name).first()
        if existing:
            existing.content = skill.content
            existing.type = skill.type
            existing.applicable_to = skill.applicable_to
            existing.tags = skill.tags
            existing.relevance_score = skill.relevance_score
        else:
            db.add(skill)

    # Add contracts (no upsert — just add if table empty)
    existing_count = db.query(OutputContract).count()
    if existing_count == 0:
        for c in contracts:
            db.add(c)
        print(f"Seeded {len(contracts)} contracts")
    else:
        print(f"Contracts already exist ({existing_count}), skipping")

    db.commit()
    print(f"Seeded/updated {len(skills)} micro-skills")
    db.close()


if __name__ == "__main__":
    seed()
