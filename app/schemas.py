from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict




# ===== 共通 =====
Mode = Literal["lite", "bank", "enterprise"]
Tone = Literal["sales", "exec", "operator"]


# ===== Sales Flow =====
class ObjectionQA(BaseModel):
    model_config = ConfigDict(extra="forbid")  # ←これが additionalProperties: false になる

    objection: str = Field(..., description="想定される反論/懸念")
    answer: str = Field(..., description="切り返しの回答")


class CorePack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    summary_200: str
    key_points: list[str]
    decisions: list[str]
    action_items: list[str]
    next_steps: list[str]
    proposal_outline: list[str]
    objections_qa: list[ObjectionQA] = Field(default_factory=list)
    followup_email_subject: str
    followup_email_body: str

    missing_info: list[str] = Field(default_factory=list)




class BankAddon(BaseModel):
    internal_control_points: list[str] = Field(default_factory=list)
    audit_ready_points: list[str] = Field(default_factory=list)
    risk_scenarios: list[str] = Field(default_factory=list)

    # ★ここが今回の本命（ペアで持つ）
    approval_qas: list[ExpectedQA] = Field(default_factory=list)





class EnterpriseAddon(BaseModel):
    kpi_targets: List[str] = []
    rollout_plan: List[str] = []
    roi_story: List[str] = []


class SalesFlowRequest(BaseModel):
    memo: str
    mode: Mode = "lite"
    tone: Tone = "sales"
    company: Optional[str] = None
    customer_name: Optional[str] = None
    product: Optional[str] = None


class SalesFlowResponse(BaseModel):
    core: CorePack
    addons: dict[str, Any] = {}
    meta: dict[str, Any] = {}


# ===== 既存API用（main.pyが使っている） =====
class EmailRequest(BaseModel):
    customer_name: str
    customer_company: str
    email_type: str
    context: str
    key_points: Optional[List[str]] = None


class EmailResponse(BaseModel):
    subject: str
    body: str
    tone: str
    next_action: Optional[str] = None


class MeetingSummaryRequest(BaseModel):
    customer_name: str
    customer_company: str
    meeting_date: str
    meeting_content: str


class MeetingSummaryResponse(BaseModel):
    summary: str
    key_points: List[str]
    decisions: List[str]
    concerns: List[str]
    next_actions: List[str]


class ProposalRequest(BaseModel):
    customer_name: str
    customer_company: str
    customer_industry: str
    customer_challenges: str
    our_services: str
    proposal_goal: str


class ProposalSection(BaseModel):
    title: str
    key_points: List[str]


class ExpectedQA(BaseModel):
    question: str = Field(..., description="想定される質問")
    answer: str = Field(..., description="質問への回答")



class ProposalResponse(BaseModel):
    title: str
    sections: List[ProposalSection]
    expected_qa: List[ExpectedQA]


class ConversationCreate(BaseModel):
    customer_id: str
    customer_name: str
    customer_company: str
    conversation_type: str
    content: str
    metadata: Optional[dict] = None


class Conversation(BaseModel):
    id: int
    customer_id: str
    customer_name: str
    customer_company: str
    conversation_type: str
    content: str
    metadata: Optional[dict]
    created_at: str
# --- pydantic v2: forward refs / rebuild ---
SalesFlowResponse.model_rebuild()
SalesFlowRequest.model_rebuild()

CorePack.model_rebuild()
SalesFlowResponse.model_rebuild()
