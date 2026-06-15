import os
import json
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Dynamically inject the key-value pairs from your root .env file into the system environment.
# override=True ensures Streamlit's cached process doesn't ignore the .env on re-runs.
load_dotenv(override=True)

# LangChain's ChatGoogleGenerativeAI specifically looks for GOOGLE_API_KEY.
# This bridges your GEMINI_API_KEY into the expected variable name automatically.
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# ==========================================
# 1. DATA SCHEMAS
# ==========================================

class ReviewAnalysis(BaseModel):
    sentiment: str = Field(description="The emotional tone of the review (e.g., Positive, Negative, Neutral)")
    escalation_required: bool = Field(description="True if the review contains high-risk elements or serious complaints")
    escalation_reason: str = Field(description="The primary reason for escalation, or empty string if not applicable")
    draft_response: str = Field(description="A highly tailored, professional response draft complying with all brand rules")


# ==========================================
# 2. HELPER UTILITIES
# ==========================================

def _load_brand_config(profile_filename: str) -> Tuple[Dict[str, Any], str]:
    """
    Handles file I/O operations and builds conditional string fragments 
    for the LLM prompt based on the brand profile context.
    """
    config_path = os.path.join("config", profile_filename)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"The brand profile '{profile_filename}' could not be located.")
        
    with open(config_path, "r", encoding="utf-8") as f:
        brand_config = json.load(f)

    # Construct the trigger validation guidelines dynamically
    triggers = brand_config.get("escalation_triggers", {})
    trigger_instructions = ""
    if triggers.get("legal_threats"):
        trigger_instructions += "- Flag as true if the user mentions lawyers, suing, legal actions, or lawsuits.\n"
    if triggers.get("damaged_items"):
        trigger_instructions += "- Flag as true if the user mentions broken, shattered, or physically damaged products.\n"

    return brand_config, trigger_instructions


# ==========================================
# 3. CORE PROCESSING PIPELINE
# ==========================================

def generate_review_response(review_text: str, profile_filename: str = "brand_rules.json") -> ReviewAnalysis:
    """
    Analyzes a customer review and generates a structured response 
    utilizing native LangChain structured output pipelines.
    """
    # 1A. Load and parse the targeted brand rules configuration
    brand_config, trigger_instructions = _load_brand_config(profile_filename)

    # 1B. Extract configuration parameters with safe fallbacks.
    # Supports BOTH flat schema (Suburban_Boutique.json style) and nested schema
    # (brand_rules.json style) so all profiles work without modification.
    brand_name = brand_config.get("brand_name", "Our Brand")

    # Flat schema: "tone" key. Nested schema: "tone_guidelines.professionalism"
    tone_guidelines = brand_config.get("tone_guidelines", {})
    brand_tone = brand_config.get("tone") or tone_guidelines.get("professionalism", "professional and polite")

    # Flat schema: "max_discount_allowed". Nested schema: "resolution_policies.max_allowed_discount_percent"
    resolution_policies = brand_config.get("resolution_policies", {})
    raw_discount = brand_config.get("max_discount_allowed") or resolution_policies.get("max_allowed_discount_percent", 0)
    max_discount = f"{raw_discount}%" if isinstance(raw_discount, (int, float)) else str(raw_discount)

    # Flat schema: top-level "prohibited_phrases". Nested schema: "tone_guidelines.prohibited_phrases"
    prohibited_phrases = ", ".join(
        brand_config.get("prohibited_phrases") or tone_guidelines.get("prohibited_phrases", [])
    )
    
    # 1C. Initialize the modern structured LLM engine
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Fixed: gemini-3.1-flash-lite does not exist 
        temperature=0.2
    )
    structured_llm = llm.with_structured_output(ReviewAnalysis)

    # 1D. Construct clean system instruction templates using standard LCEL inputs
    system_instruction = (
        "You are an elite automated reputation management assistant for '{brand_name}'.\n\n"
        "Your core directive is to analyze incoming customer feedback and draft a response adhering strictly "
        "to these localized brand compliance parameters:\n"
        "- TONE: You must write exclusively in a {brand_tone} tone.\n"
        "- FINANCIAL LIMIT: Never offer compensation or a discount exceeding {max_discount}.\n"
        "- PROHIBITED PHRASES: Do NOT use any of these phrases or close variations: [{prohibited_phrases}].\n\n"
        "CRITICAL ESCALATION PROTOCOLS:\n"
        "{trigger_instructions}"
        "If an escalation protocol is met, set escalation_required to True and state the reason concisely."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("user", "Analyze the following customer review:\n\n{review_text}")
    ])

    # 1E. Assemble and invoke the declarative LCEL chain execution block
    chain = prompt_template | structured_llm
    
    parsed_output = chain.invoke({
        "brand_name": brand_name,
        "brand_tone": brand_tone,
        "max_discount": max_discount,
        "prohibited_phrases": prohibited_phrases,
        "trigger_instructions": trigger_instructions,
        "review_text": review_text
    })

    return parsed_output