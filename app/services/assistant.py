from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.models.schemas import AssistantChatRequest, AssistantChatResponse
from app.utils.config import settings


class AssistantChatService:
    """Context-grounded assistant backed by Ollama chat completions."""

    def answer(self, request: AssistantChatRequest) -> AssistantChatResponse:
        if settings.assistant_provider.casefold() != "ollama":
            warning = (
                f"Assistant provider '{settings.assistant_provider}' is not supported for chat. "
                "Set ASSISTANT_PROVIDER=ollama to enable the conversational assistant."
            )
            return AssistantChatResponse(
                answer=warning,
                model=settings.ollama_model,
                warning=warning,
            )

        messages = self._build_messages(request)
        attempted_models: list[str] = []
        warnings: list[str] = []

        for model_name in self._candidate_models():
            attempted_models.append(model_name)
            parsed, warning = self._chat_once(model_name, messages)
            if parsed is not None:
                answer = str(parsed.get("message", {}).get("content", "")).strip()
                if not answer:
                    answer = (
                        "I received a response from Ollama, but it did not include any message content. "
                        "Please try again or switch to a different local model."
                    )
                return AssistantChatResponse(
                    answer=answer,
                    model=parsed.get("model") or model_name,
                    warning=" ".join(warnings) if warnings else None,
                )
            if warning:
                warnings.append(warning)

        combined_warning = " ".join(warnings).strip() or "No Ollama model was available for chat."
        configured_model = attempted_models[0] if attempted_models else settings.ollama_model
        return AssistantChatResponse(
            answer=self._assistant_unavailable_message(combined_warning),
            model=configured_model,
            warning=combined_warning,
        )

    def _build_messages(self, request: AssistantChatRequest) -> list[dict[str, str]]:
        context_payload = {
            "current_view": request.view,
            "active_tab": request.active_tab,
            "assistant_reference": self._assistant_reference(),
            "job_context": request.job_context.model_dump() if request.job_context else None,
            "analysis": request.analysis.model_dump() if request.analysis else None,
        }

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self._system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    "Use the following application context as the only source of truth. "
                    "Do not mention the raw JSON unless the user explicitly asks for structure.\n\n"
                    f"{json.dumps(context_payload, indent=2)}"
                ),
            },
        ]

        for item in request.history[-8:]:
            if item.role not in {"user", "assistant"}:
                continue
            content = item.content.strip()
            if not content:
                continue
            messages.append({"role": item.role, "content": content})

        messages.append({"role": "user", "content": request.question.strip()})
        return messages

    def _candidate_models(self) -> list[str]:
        candidates = [settings.ollama_model]
        fallback_model = self._first_local_model()
        if fallback_model and fallback_model not in candidates:
            candidates.append(fallback_model)
        return candidates

    def _chat_once(self, model_name: str, messages: list[dict[str, str]]) -> tuple[dict | None, str | None]:
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": {
                "temperature": 0.2,
            },
        }

        endpoint = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
        http_request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=settings.ollama_timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            warning = self._extract_error_message(details) or f"Ollama returned HTTP {exc.code}."
            return None, warning
        except urllib.error.URLError as exc:
            warning = (
                f"Could not reach Ollama at {settings.ollama_base_url}. "
                f"Details: {exc.reason}"
            )
            return None, warning

        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError:
            return None, "Ollama returned an invalid JSON response."

        return parsed, None

    def _first_local_model(self) -> str | None:
        endpoint = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        http_request = urllib.request.Request(endpoint, method="GET")
        try:
            with urllib.request.urlopen(http_request, timeout=min(settings.ollama_timeout_seconds, 10)) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            return None

        models = parsed.get("models") or []
        if not models:
            return None
        first_model = models[0]
        return first_model.get("name") or first_model.get("model")

    def _system_prompt(self) -> str:
        return (
            "You are the AI Assistant inside an HR technical interview copilot. "
            "Answer like a thoughtful, capable assistant for recruiters and hiring managers. "
            "You should synthesize information, explain tradeoffs, and recommend next steps based on the provided context. "
            "Grounding rules: "
            "1. Use only the provided application context and conversation history. "
            "2. Do not invent candidate details, scores, projects, or skills. "
            "3. If the answer is not supported by the context, say you do not have enough evidence yet. "
            "4. Do not simply restate labels from the interface when the user is asking for analysis; explain what the data means. "
            "5. If you infer a recommendation or next step, say that it is based on the provided analysis. "
            "6. Keep answers concise but useful, usually a short paragraph or a few flat bullets. "
            "7. When discussing scores or recommendations, cite exact values and concrete evidence from the context."
        )

    def _assistant_reference(self) -> dict:
        return {
            "product_purpose": (
                "This application helps HR users define hiring criteria, upload resumes, analyze candidates, "
                "review explainable scoring, prepare technical interviews, and run an assisted interview flow."
            ),
            "upload_support": ["PDF", "DOC", "DOCX", "TXT"],
            "scoring_rules": {
                "fresher": {
                    "skills_weight": 50,
                    "projects_weight": 50,
                    "experience_weight": 0,
                },
                "experienced": {
                    "skills_weight": 40,
                    "projects_weight": 30,
                    "experience_weight": 30,
                },
                "skill_score": "matched_skills / required_skills",
                "final_score": "weighted combination of skill_score, project_score, and experience_score",
            },
            "confidence_formula": (
                "confidence = extraction_confidence * 0.4 + skill_match * 0.3 + data_completeness * 0.3"
            ),
            "assistant_scope": [
                "explain the current screen",
                "explain the scoring and recommendation",
                "summarize strengths, weaknesses, and risks",
                "suggest interview focus areas",
                "explain coding test focus",
                "suggest next actions in the workflow",
            ],
        }

    def _assistant_unavailable_message(self, warning: str) -> str:
        return (
            f"I couldn't use Ollama for this response. {warning} "
            f"Make sure Ollama is running, then pull or configure a local model such as `{settings.ollama_model}`."
        )

    def _extract_error_message(self, payload: str) -> str | None:
        payload = payload.strip()
        if not payload:
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return payload
        return parsed.get("error") or parsed.get("message")
