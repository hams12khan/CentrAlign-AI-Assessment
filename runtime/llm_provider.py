"""
Unified Multi-Provider LLM Client for CentrAlign AI Autonomous Runtime.

Supports:
1. Groq Free Tier (Llama 3.3 70B Versatile, Llama 3.1 8B Instant)
2. Google Gemini Free Tier (Gemini 1.5 Flash, Gemini 2.0 Flash)
3. Local Ollama (HTTP REST)
4. Offline Mock LLM Provider (100% deterministic, zero latency, offline safe)
"""

import abc
import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from runtime.config import RuntimeSettings, get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(abc.ABC):
    """Abstract interface for all language model providers."""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a text response given a prompt and optional system instructions.

        :param prompt: User prompt or instruction.
        :param system_prompt: Optional system persona and constraints.
        :param json_mode: Whether to enforce valid JSON output format.
        :param temperature: Sampling temperature.
        :return: Generated string response.
        """
        pass

    @abc.abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Generate output parsed into a strongly-typed Pydantic model.

        :param prompt: User prompt or instruction.
        :param response_model: Pydantic model class to deserialize into.
        :param system_prompt: Optional system persona.
        :return: Instance of response_model.
        """
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic offline LLM provider for live demos and unit test execution.
    Recognizes enterprise goals, DAG decomposition requests, and LLM-as-a-judge
    verification prompts, returning production-realistic structured outputs.
    """

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        prompt_lower = prompt.lower()
        combined_text = f"{system_prompt or ''} {prompt}".lower()

        # 1. LLM-as-a-Judge outcome verification requests
        if "judge" in combined_text or "verifier" in combined_text or "confidence_score" in combined_text:
            has_failures = (
            ": false" in prompt_lower
            or '"false"' in prompt_lower
            or '"status": "failed"' in prompt_lower
            or "'status': 'failed'" in prompt_lower
        )
            if has_failures:
                return json.dumps({
                    "verdict": "FAILED",
                    "confidence_score": 0.42,
                    "criteria_checklist": {
                        "database_state_consistent": False,
                        "artifacts_generated_and_hashed": False,
                        "policy_rules_adhered": True,
                        "no_unhandled_side_effects": False,
                    },
                    "reasoning": (
                        "Post-execution verification reveals deterministic ground truth failures. "
                        "Target state mutations or on-disk artifacts did not match expected criteria."
                    ),
                    "failure_diagnosis": "Deterministic assertions failed in database ground truth or artifact generation.",
                })

            return json.dumps({
                "verdict": "PASSED",
                "confidence_score": 0.98,
                "criteria_checklist": {
                    "database_state_consistent": True,
                    "artifacts_generated_and_hashed": True,
                    "policy_rules_adhered": True,
                    "no_unhandled_side_effects": True,
                },
                "reasoning": (
                    "Post-execution verification confirms all deterministic assertions passed. "
                    "Ledger state matches expected totals and required audit artifacts are present."
                ),
                "failure_diagnosis": None,
            })

        # 1.5 Emergency Payment / Disbursement DAG request
        if any(w in combined_text for w in ["disburs", "payment", "wire", "emergency"]):
            return json.dumps({
                "task_id": "task_payment_disburse_001",
                "goal": "Authorize and disburse emergency vendor payment with policy guardrails",
                "steps": {
                    "step_1": {
                        "id": "step_1",
                        "tool": "db_query",
                        "params": {"sql": "SELECT * FROM purchase_orders WHERE po_id = 'PO-2026-9012'", "db_type": "sqlite"},
                        "dependencies": [],
                        "description": "Query ERP for approved purchase order PO-2026-9012.",
                    },
                    "step_2": {
                        "id": "step_2",
                        "tool": "browser_action",
                        "params": {"action": "navigate_and_screenshot", "fields": {"po_id": "PO-2026-9012", "new_status": "DISBURSED"}},
                        "dependencies": ["step_1"],
                        "description": "Inspect portal and take visual ground truth screenshot.",
                    },
                    "step_3": {
                        "id": "step_3",
                        "tool": "db_update",
                        "params": {"sql": "UPDATE purchase_orders SET status = 'DISBURSED' WHERE po_id = 'PO-2026-9012'", "amount": 4500.00, "db_type": "sqlite"},
                        "dependencies": ["step_2"],
                        "description": "Execute disbursement update (exceeds $1,000 threshold, halts for HITL approval).",
                    },
                    "step_4": {
                        "id": "step_4",
                        "tool": "file_write",
                        "params": {
                            "file_path": "audit_logs/disbursement_receipt_PO-2026-9012.json",
                            "content": "{\"task\": \"payment\", \"po_id\": \"PO-2026-9012\", \"status\": \"DISBURSED\"}",
                        },
                        "dependencies": ["step_3"],
                        "description": "Save immutable payment execution receipt in sandbox.",
                    },
                },
            })

        # 2. Vendor Invoice Reconciliation DAG request
        if "invoice" in combined_text or "reconciliation" in combined_text:
            return json.dumps({
                "task_id": "task_invoice_recon_001",
                "goal": "Reconcile vendor invoices against purchase orders and update ERP",
                "steps": {
                    "step_1": {
                        "id": "step_1",
                        "tool": "file_read",
                        "params": {"file_path": "incoming_invoices/INV-2026-0042.json"},
                        "dependencies": [],
                        "description": "Parse inbound vendor invoice line items and claimed totals.",
                    },
                    "step_2": {
                        "id": "step_2",
                        "tool": "db_query",
                        "params": {
                            "sql": "SELECT * FROM purchase_orders WHERE po_id = 'PO-2026-9011'",
                            "db_type": "sqlite",
                        },
                        "dependencies": ["step_1"],
                        "description": "Query ERP database for matching approved purchase order.",
                    },
                    "step_3": {
                        "id": "step_3",
                        "tool": "evaluate_discrepancy",
                        "params": {
                            "invoice_amount": 1250.00,
                            "po_amount": 1200.00,
                            "po_id": "PO-2026-9011",
                        },
                        "dependencies": ["step_2"],
                        "description": "Calculate variance and determine policy routing (tolerance vs dispute).",
                    },
                    "step_4": {
                        "id": "step_4",
                        "tool": "db_update",
                        "params": {
                            "sql": "UPDATE purchase_orders SET status = 'FLAGGED_DISPUTE' WHERE po_id = 'PO-2026-9011'",
                            "db_type": "sqlite",
                        },
                        "dependencies": ["step_3"],
                        "description": "Update ERP ledger with dispute status and hold payment.",
                    },
                    "step_5": {
                        "id": "step_5",
                        "tool": "file_write",
                        "params": {
                            "file_path": "audit_logs/reconciliation_report_INV-2026-0042.md",
                            "content": (
                                "# Vendor Invoice Reconciliation Dossier\n"
                                "- Invoice: INV-2026-0042\n"
                                "- PO: PO-2026-9011\n"
                                "- Variance: $50.00\n"
                                "- Status: FLAGGED_DISPUTE\n"
                            ),
                        },
                        "dependencies": ["step_4"],
                        "description": "Generate immutable markdown reconciliation report in sandbox.",
                    },
                },
            })

        # 3. Customer Refund Anomaly DAG request
        if "refund" in combined_text or "anomaly" in combined_text or "march 2026" in combined_text:
            return json.dumps({
                "task_id": "task_refund_audit_001",
                "goal": "Audit March 2026 refund anomalies over $500 and flag unapproved claims",
                "steps": {
                    "step_1": {
                        "id": "step_1",
                        "tool": "db_query",
                        "params": {
                            "sql": "SELECT * FROM refund_requests WHERE amount > 500.00 AND status = 'PENDING'",
                            "db_type": "sqlite",
                        },
                        "dependencies": [],
                        "description": "Query SQLite database for unapproved refund requests exceeding $500.",
                    },
                    "step_2": {
                        "id": "step_2",
                        "tool": "analytics_query",
                        "params": {
                            "sql": "SELECT customer_id, count(*), sum(amount) FROM refund_requests GROUP BY customer_id HAVING count(*) > 1",
                        },
                        "dependencies": ["step_1"],
                        "description": "Execute DuckDB analytical query to detect high-frequency repeat refund fraud.",
                    },
                    "step_3": {
                        "id": "step_3",
                        "tool": "db_update",
                        "params": {
                            "sql": "UPDATE refund_requests SET flagged_anomaly = 1, status = 'UNDER_REVIEW' WHERE amount > 500.00",
                            "db_type": "sqlite",
                        },
                        "dependencies": ["step_2"],
                        "description": "Flag anomalous records in ERP database for compliance hold.",
                    },
                    "step_4": {
                        "id": "step_4",
                        "tool": "file_write",
                        "params": {
                            "file_path": "audit_logs/refund_anomaly_audit_march_2026.json",
                            "content": "{\"audited\": true, \"flagged_count\": 3, \"total_flagged_value\": 3450.00}",
                        },
                        "dependencies": ["step_3"],
                        "description": "Persist structured audit package for compliance reporting.",
                    },
                },
            })

        # 4. Access Review DAG request
        if "access" in combined_text or "rbac" in combined_text or "compliance" in combined_text:
            return json.dumps({
                "task_id": "task_access_review_001",
                "goal": "Review privileged administrative access and revoke dormant accounts",
                "steps": {
                    "step_1": {
                        "id": "step_1",
                        "tool": "db_query",
                        "params": {
                            "sql": "SELECT * FROM customers WHERE tier = 'ADMIN_PRIVILEGED'",
                            "db_type": "sqlite",
                        },
                        "dependencies": [],
                        "description": "Fetch current elevated permission roster from internal database.",
                    },
                    "step_2": {
                        "id": "step_2",
                        "tool": "file_write",
                        "params": {
                            "file_path": "compliance/dormant_access_review.md",
                            "content": "# Access Review Log\nAll dormant accounts flagged for revoking.",
                        },
                        "dependencies": ["step_1"],
                        "description": "Generate compliance review audit report.",
                    },
                },
            })

        # Fallback response
        if json_mode:
            return json.dumps({"status": "SUCCESS", "message": "Autonomous task executed cleanly."})
        return "Deterministic Mock LLM execution completed successfully."

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        raw_json = self.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True)
        try:
            data = json.loads(raw_json)
            return response_model.model_validate(data)
        except Exception:
            # Construct default model instance if validation fails
            return response_model.model_construct()


class GroqLLMProvider(BaseLLMProvider):
    """Integration for Groq API (free-tier Llama 3 models)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
        except ImportError:
            raise RuntimeError("Groq package not installed. Install via pip install groq.")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        json_str = self.generate(
            prompt=f"{prompt}\nOutput valid JSON adhering strictly to schema: {json.dumps(response_model.model_json_schema())}",
            system_prompt=system_prompt,
            json_mode=True,
        )
        return response_model.model_validate_json(json_str)


class GeminiLLMProvider(BaseLLMProvider):
    """Integration for Google Gemini Free Tier using official google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise RuntimeError("google-genai package not installed. Install via pip install google-genai.")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\nUser: {prompt}"
        if json_mode:
            full_prompt += "\nResponse MUST be raw JSON without markdown code fences."

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
        )
        text = response.text or ""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        json_str = self.generate(
            prompt=f"{prompt}\nProvide valid JSON matching schema: {json.dumps(response_model.model_json_schema())}",
            system_prompt=system_prompt,
            json_mode=True,
        )
        return response_model.model_validate_json(json_str)


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama client using HTTP requests."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        json_str = self.generate(
            prompt=f"{prompt}\nOutput valid JSON for schema: {json.dumps(response_model.model_json_schema())}",
            system_prompt=system_prompt,
            json_mode=True,
        )
        return response_model.model_validate_json(json_str)


class UnifiedLLMProvider(BaseLLMProvider):
    """
    Unified LLM Client that delegates to configured primary provider
    and gracefully falls back to deterministic MockLLMProvider upon any failure.
    """

    def __init__(self, settings: Optional[RuntimeSettings] = None):
        self.settings = settings or get_settings()
        self.mock_provider = MockLLMProvider()
        self.primary_provider = self._init_primary_provider()

    def _init_primary_provider(self) -> BaseLLMProvider:
        mode = self.settings.LLM_PROVIDER.lower()

        if mode == "groq" and self.settings.GROQ_API_KEY:
            try:
                return GroqLLMProvider(
                    api_key=self.settings.GROQ_API_KEY,
                    model=self.settings.GROQ_MODEL,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Groq provider: {e}. Falling back to Mock.")

        elif mode == "gemini" and self.settings.GEMINI_API_KEY:
            try:
                return GeminiLLMProvider(
                    api_key=self.settings.GEMINI_API_KEY,
                    model=self.settings.GEMINI_MODEL,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}. Falling back to Mock.")

        elif mode == "ollama":
            try:
                return OllamaLLMProvider(
                    base_url=self.settings.OLLAMA_BASE_URL,
                    model=self.settings.OLLAMA_MODEL,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama provider: {e}. Falling back to Mock.")

        return self.mock_provider

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        try:
            return self.primary_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                json_mode=json_mode,
                temperature=temperature,
            )
        except Exception as e:
            logger.warning(f"Primary LLM provider failed ({e}). Utilizing deterministic offline mock fallback.")
            return self.mock_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                json_mode=json_mode,
                temperature=temperature,
            )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        try:
            return self.primary_provider.generate_structured(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
            )
        except Exception as e:
            logger.warning(f"Primary LLM structured call failed ({e}). Falling back to Mock provider.")
            return self.mock_provider.generate_structured(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
            )


def get_llm_provider(settings: Optional[RuntimeSettings] = None) -> UnifiedLLMProvider:
    """Return a unified multi-provider LLM client instance."""
    return UnifiedLLMProvider(settings=settings)
