from __future__ import annotations

from app.models.schemas import CopilotResponse, InterviewQuestion


class InterviewCopilotService:
    """Converts HR commands into adaptive question prompts."""

    def respond(self, command: str, questions: list[InterviewQuestion], current_question_index: int = 0) -> CopilotResponse:
        if not questions:
            note = "The current resume does not contain enough project detail for adaptive questioning."
            return CopilotResponse(
                suggested_question="No project-based interview questions are available yet.",
                expected_direction="Upload and analyze a resume with project evidence first.",
                difficulty="N/A",
                coaching_note=note,
                reason=note,
            )

        command_key = command.strip().casefold()
        index = max(0, min(current_question_index, len(questions) - 1))
        question = questions[index]

        if command_key == "next question":
            next_index = min(index + 1, len(questions) - 1)
            question = questions[next_index]
            note = f"Move to project '{question.project_name}' and ask for a concrete implementation story."
            return CopilotResponse(
                suggested_question=question.question,
                expected_direction=question.expected_answer,
                difficulty=question.difficulty,
                coaching_note=note,
                reason="Advancing to the next prepared question to broaden evidence.",
            )

        if command_key == "make easier":
            easier_question = f"At a high level, what was your role in '{question.project_name}', and where did you use that project's main tools?"
            coaching = "Use this when the candidate needs to re-anchor in the project before deeper follow-ups."
            return CopilotResponse(
                suggested_question=easier_question,
                expected_direction="Look for ownership, the module they handled, and one clear example of how they used the listed technology.",
                difficulty="Easy",
                coaching_note=coaching,
                reason="You asked for an easier prompt; this widens the question so the candidate can warm up.",
            )

        if command_key == "make harder":
            harder_question = (
                f"In '{question.project_name}', what would break first under higher load or stricter reliability goals, "
                "and how would you redesign it?"
            )
            coaching = "Use follow-ups about bottlenecks, monitoring, and fallback behaviour."
            return CopilotResponse(
                suggested_question=harder_question,
                expected_direction="Push for failure modes, trade-offs, and a concrete redesign sequence rather than general claims.",
                difficulty="Hard",
                coaching_note=coaching,
                reason="You asked for a harder prompt; this stresses scale and reliability thinking.",
            )

        if command_key == "candidate struggling":
            scaffolded_question = (
                f"Let's narrow it down: in '{question.project_name}', pick one feature you built and explain the input, the processing step, and the output."
            )
            coaching = "This gives the candidate a smaller surface area so you can still validate ownership."
            return CopilotResponse(
                suggested_question=scaffolded_question,
                expected_direction="The answer should become more step-by-step and evidence-based.",
                difficulty="Easy",
                coaching_note=coaching,
                reason="You flagged that the candidate is struggling; this breaks the problem into smaller steps.",
            )

        coaching = "Unknown command received, so the current question has been repeated."
        return CopilotResponse(
            suggested_question=question.question,
            expected_direction=question.expected_answer,
            difficulty=question.difficulty,
            coaching_note=coaching,
            reason=coaching,
        )

