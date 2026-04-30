from __future__ import annotations

from app.models.schemas import BiasReducedProfile, CodingAssessment, CodingQuestion, CodingSubmission, JobContext


class CodingAssessmentService:
    """Generates lightweight coding questions and evaluates text submissions."""

    def generate_questions(self, profile: BiasReducedProfile, job_context: JobContext) -> list[CodingQuestion]:
        ordered_candidates = [
            *job_context.required_skills,
            *profile.skills,
            *(tech for project in profile.projects for tech in project.technologies),
        ]
        normalized = [skill.casefold() for skill in ordered_candidates]
        questions: list[CodingQuestion] = []

        if any(skill in normalized for skill in {"python", "fastapi", "pandas"}):
            questions.append(
                CodingQuestion(
                    question_id="python-dedup",
                    prompt="Write a Python function that removes duplicates from a list while preserving the original order.",
                    expected_answer="A strong solution uses iteration, a seen set, preserves sequence order, and returns a list.",
                    evaluation_rubric=["def", "set", "for", "if", "return"],
                    difficulty="Easy",
                    skill_target="Python",
                )
            )
        if any(skill in normalized for skill in {"sql", "postgresql", "mysql", "sqlite"}):
            questions.append(
                CodingQuestion(
                    question_id="sql-aggregate",
                    prompt="Write a SQL query to find the top 3 departments by average employee rating from a table named reviews.",
                    expected_answer="A strong solution selects department, calculates AVG(rating), groups by department, sorts descending, and limits to 3 rows.",
                    evaluation_rubric=["select", "avg", "group by", "order by", "limit"],
                    difficulty="Medium",
                    skill_target="SQL",
                )
            )
        if not questions:
            questions.append(
                CodingQuestion(
                    question_id="logic-frequency",
                    prompt="Write a function in your preferred language that returns the most frequent item in a list and its count.",
                    expected_answer="A strong solution uses a map or dictionary to count items, then returns the item with the highest frequency.",
                    evaluation_rubric=["function", "map", "count", "loop", "return"],
                    difficulty="Easy",
                    skill_target="Problem Solving",
                )
            )
        return questions[:2]

    def evaluate(
        self,
        questions: list[CodingQuestion],
        submissions: list[CodingSubmission],
    ) -> CodingAssessment:
        if not submissions:
            return CodingAssessment(
                questions=questions,
                coding_score=0.0,
                observation="Coding questions generated. No candidate submission has been evaluated yet.",
                submission_results=[],
            )

        question_map = {question.question_id: question for question in questions}
        results: list[dict] = []
        scores: list[float] = []

        for submission in submissions:
            question = question_map.get(submission.question_id)
            if not question:
                continue
            answer = submission.answer.casefold()
            rubric_hits = [item for item in question.evaluation_rubric if item.casefold() in answer]
            coverage = len(rubric_hits) / len(question.evaluation_rubric) if question.evaluation_rubric else 0.0
            structure_bonus = 10 if any(token in answer for token in ("def ", "function", "select ", "return")) else 0
            logic_bonus = 10 if any(token in answer for token in ("for ", "while ", "if ", "group by")) else 0
            score = round(min(100.0, (coverage * 80) + structure_bonus + logic_bonus), 2)
            scores.append(score)
            results.append(
                {
                    "question_id": submission.question_id,
                    "rubric_hits": rubric_hits,
                    "score": score,
                    "observation": (
                        "Strong keyword coverage and basic code structure detected."
                        if score >= 75
                        else "Partial logic detected, but the solution is missing expected components."
                    ),
                }
            )

        final_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        observation = (
            "Candidate demonstrates solid coding structure and expected logic."
            if final_score >= 75
            else "Coding response shows partial correctness; probe reasoning and edge cases in the interview."
        )
        return CodingAssessment(
            questions=questions,
            coding_score=final_score,
            observation=observation,
            submission_results=results,
        )

