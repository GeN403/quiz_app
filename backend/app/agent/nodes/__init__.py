"""
LangGraph クイズ生成ワークフロー: 5 ノード実装
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

from fastapi import HTTPException
from pydantic import ValidationError
from google.api_core import exceptions as google_exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.source_resolver import SourceResolver
from app.core.prompt_builder import (
    build_prompt_url_mode,
    build_prompt_decompose_claims,
    build_prompt_verify_claim,
    build_prompt_rewrite_quiz,
)
from app.clients.gemini_client import parse_json_with_retry
from app.models.quiz import QuizData
from app.agent.state import (
    AgentState,
    ClaimEntry,
    EvidenceEntry,
    VerificationResult,
    VerificationSnapshot,
    DisambiguationParametersModel,
    JudgementResult,
)
from app.agent.services.loop_control import LoopControlService
from app.agent.services.disambiguation import (
    MinorDisambiguationService,
    MajorDisambiguationService,
)


# ---------------------------------------------------------------------------
# Task 2.1: validate_input ノード
# ---------------------------------------------------------------------------

from app.agent.nodes.validate_input import validate_input
from app.agent.nodes.fetch_source import fetch_source


# ---------------------------------------------------------------------------
# Task 3.1: generate_quiz ノードファクトリ
# ---------------------------------------------------------------------------

from app.agent.nodes.generate_quiz import make_generate_quiz_node
from app.agent.nodes.parse_output import parse_output


# ---------------------------------------------------------------------------
# Task 3.1 / 3.2: resolve_topic_input ノードファクトリ
# ---------------------------------------------------------------------------

from app.agent.nodes.resolve_topic_input import make_resolve_topic_input_node


from app.agent.nodes.decompose_claims import make_decompose_claims_node


from app.agent.nodes.collect_evidence import make_collect_evidence_node


from app.agent.nodes.verify_claims import (
    MAX_VERIFICATION_RETRIES,
    make_verify_claims_node,
)
from app.agent.nodes.rewrite_quiz import make_rewrite_quiz_node
