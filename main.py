# LangGraph-based Epic Evaluator
from typing import Optional, List, Dict
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv
import json
import time # Import the time module

# Load API key
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

# ------------------ Models ------------------ #

class ElementEvaluation(BaseModel):
    element: str
    quality: str
    explanation: str
    recommendations: str
    feedback: Optional[str] = None # Renamed from refined_recommendations to feedback

class EpicState(BaseModel):
    raw_text: str
    parsed: Optional[Dict] = None
    evaluations: List[ElementEvaluation] = []
    current_element: Optional[str] = None
    current_content: Optional[str] = None
    refinement_needed: Optional[bool] = False
    done: bool = False
    epic_index: Optional[int] = None # Added to keep track of the epic number for file naming

# ------------------ Output Parsers ------------------ #

parser_schema = [
    ResponseSchema(name="Title", description="Epic title"),
    ResponseSchema(name="Problem Statement", description="Problem"),
    ResponseSchema(name="Product Outcome & Instrumentation", description="Outcome"),
    ResponseSchema(name="Requirements - User Stories", description="Stories"),
    ResponseSchema(name="Non-Functional Requirements", description="NFRs")
]
parser = StructuredOutputParser.from_response_schemas(parser_schema)

eval_schema = [
    ResponseSchema(name="quality", description="HIGH, MEDIUM, LOW"),
    ResponseSchema(name="explanation", description="Why this score"),
    ResponseSchema(name="recommendations", description="How to improve")
]
eval_parser = StructuredOutputParser.from_response_schemas(eval_schema)

# ------------------ Nodes ------------------ #

def parser_node(state: EpicState):
    prompt = PromptTemplate(
        input_variables=["epic_text"],
        template="""Extract and organize the following elements from the epic text. If an element is not present, leave it empty.

Elements to extract:
- Title: The title of the epic
- Problem Statement: The problem being addressed
- Product Outcome & Instrumentation: The measurable outcomes and how they will be measured
- Requirements - User Stories: The user stories describing functionality
- Non-Functional Requirements: Any non-functional requirements specified

Return in this exact JSON format:
{{
    "Title": "extracted title",
    "Problem Statement": "extracted problem statement",
    "Product Outcome & Instrumentation": "extracted outcomes",
    "Requirements - User Stories": "extracted user stories",
    "Non-Functional Requirements": "extracted NFRs"
}}

Epic Text:
{epic_text}"""
    )
    chain = prompt | llm
    result = chain.invoke({"epic_text": state.raw_text})
    time.sleep(1) # Added delay after LLM call
    try:
        data = json.loads(result.content)
    except json.JSONDecodeError:
        data = parser.parse(result.content) 
    
    # Ensure all required keys are present with proper formatting
    required_keys = ["Title", "Problem Statement", "Product Outcome & Instrumentation", 
                     "Requirements - User Stories", "Non-Functional Requirements"]
    for key in required_keys:
        if key not in data:
            data[key] = ""
            
    return {"parsed": data}

def element_router(state: EpicState):
    # Determine which elements have already been evaluated
    evaluated_elements_names = {e.element for e in state.evaluations}
    
    # Identify all elements expected to be parsed
    all_parsed_elements_names = set(state.parsed.keys())
    
    # Find any element that has been parsed but not yet evaluated
    unevaluated_elements = [
        k for k in all_parsed_elements_names 
        if k not in evaluated_elements_names
    ]
    
    if not unevaluated_elements: # If there are no unevaluated elements left
        return {"current_element": None, "current_content": None, "done": True}
    else:
        # Pick the first unevaluated element (or any consistent order)
        next_element_name = unevaluated_elements[0]
        next_element_content = state.parsed[next_element_name]
        return {
            "current_element": next_element_name, 
            "current_content": next_element_content, 
            "done": False
        }

def element_evaluator(state: EpicState):
    if state.current_element is None:
        return {"evaluations": state.evaluations}
    
    QUALITY_STANDARDS = """Quality Standards for Epic Elements:

Title:
- HIGH: Clear, concise, specific, and memorable
- MEDIUM: Clear but could be more specific or engaging
- LOW: Vague, too long, or unclear

Problem Statement:
- HIGH: Clear problem, quantified impact, specific context
- MEDIUM: Problem identified but impact or context unclear
- LOW: Vague problem, no context or impact stated

Product Outcome & Instrumentation:
- HIGH: Specific, measurable outcomes with clear metrics
- MEDIUM: Outcomes stated but metrics unclear
- LOW: No clear outcomes or measurements

Requirements - User Stories:
- HIGH: Complete user stories (As a..., I want..., So that...)
- MEDIUM: Basic user stories with some missing elements
- LOW: Incomplete or unclear user stories

Non-Functional Requirements:
- HIGH: Specific, measurable, testable requirements
- MEDIUM: Requirements stated but not fully measurable
- LOW: Vague or missing requirements"""

    # Guardrails for quality scores
    VALID_QUALITIES = {"HIGH", "MEDIUM", "LOW", "ERROR"}
    MIN_EXPLANATION_LENGTH = 20
    MAX_RETRIES = 3
    
    prompt = PromptTemplate(
        input_variables=["element", "content", "standards"],
        partial_variables={"format_instructions": eval_parser.get_format_instructions()},
        template="""
Evaluate the element based on standards.

Standards:
{standards}

Element: {element}
Content: {content}

{format_instructions}

IMPORTANT:
1. Quality MUST be one of: HIGH, MEDIUM, LOW
2. Explanation must be at least 20 words and justify the quality score
3. Recommendations must be specific and actionable
"""
    )
    chain = prompt | llm
    
    quality = "ERROR"
    explanation = "Evaluation failed due to an unexpected error."
    recommendations = "Review the LLM response and API status."
    result_content = "" # Initialize to empty string

    # Add retry logic with guardrails
    for attempt in range(MAX_RETRIES):
        try:
            result = chain.invoke({
                "element": state.current_element,
                "content": state.current_content,
                "standards": QUALITY_STANDARDS
            })
            time.sleep(1) # Added delay after LLM call
            result_content = result.content # Store content for potential error reporting
            parsed = eval_parser.parse(result_content)
            
            # Validate quality score
            quality = parsed['quality']
            if quality not in VALID_QUALITIES:
                raise ValueError(f"Invalid quality score: {quality}")
                
            # Validate explanation length
            explanation = parsed['explanation']
            if len(explanation.split()) < MIN_EXPLANATION_LENGTH:
                raise ValueError(f"Explanation too short: {len(explanation.split())} words")
                
            recommendations = parsed['recommendations']
            # If we get here, all validations passed
            break
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:  # Last attempt
                print(f"Warning: Failed to evaluate element '{state.current_element}' after {MAX_RETRIES} attempts. Error: {e}. LLM raw response was: '{result_content}'")
                explanation = f"Evaluation failed after {MAX_RETRIES} attempts: {e}. This might be due to API quota exhaustion or an invalid LLM response."
                recommendations = "Check your Google Cloud API quota for Generative Language API and ensure LLM returns valid JSON. You may need to wait for quota reset or increase your quota."
    
    return {
        "evaluations": state.evaluations + [ElementEvaluation(
            element=state.current_element,
            quality=quality,
            explanation=explanation,
            recommendations=recommendations
        )],
        "refinement_needed": quality == "LOW" # Set to True if quality is LOW
    }

def refinement_node(state: EpicState):
    # Find the last evaluation added, which should be the one that triggered refinement
    if not state.evaluations or not state.refinement_needed:
        return {"refinement_needed": False}

    last_evaluation = state.evaluations[-1]

    # Only refine if the quality is LOW
    if last_evaluation.quality == "LOW":
        print(f"Generating feedback for '{last_evaluation.element}'...")
        refinement_prompt = PromptTemplate(
            input_variables=["element", "content", "explanation", "current_recommendations"],
            template="""Given the following evaluation for an epic element, provide more detailed, actionable suggestions for improvement.

            Element: {element}
            Content: {content}
            Quality: LOW
            Explanation: {explanation}
            Current Recommendations: {current_recommendations}

            Provide specific, concrete steps or examples that the team can follow to improve this element to a HIGH quality. Ensure the suggestions are actionable and clear.
            """
        )
        refinement_chain = refinement_prompt | llm
        
        refined_suggestions_result = refinement_chain.invoke({
            "element": last_evaluation.element,
            "content": state.parsed.get(last_evaluation.element, ""), # Use content from parsed state for context
            "explanation": last_evaluation.explanation,
            "current_recommendations": last_evaluation.recommendations
        })
        time.sleep(1) # Add delay after LLM call

        # Update the last evaluation with feedback
        updated_evaluations = list(state.evaluations) # Create a mutable copy
        updated_evaluations[-1].feedback = refined_suggestions_result.content # Changed to .feedback
        
        return {
            "evaluations": updated_evaluations,
            "refinement_needed": False # Reset the flag after refinement
        }
    else:
        # If refinement not needed (e.g., quality is not LOW), just proceed
        return {"refinement_needed": False}

def aggregate_node(state: EpicState):
    print(f"\nFINAL REPORT for Epic {state.epic_index}:")
    # Convert Pydantic models to dictionaries for JSON serialization
    report_data = [eval_item.model_dump() for eval_item in state.evaluations]
    
    # Create evaluation_results directory if it doesn't exist
    os.makedirs("evaluation_results", exist_ok=True)
    
    # Generate unique filename with date and time
    current_time = time.strftime("%Y%m%d_%H%M%S")
    output_filename = f"evaluation_results/epic_evaluation_{state.epic_index}_{current_time}.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {output_filename}")
    except IOError as e:
        print(f"Error saving report to file {output_filename}: {e}")

    # Also print to console for immediate review
    print(json.dumps(report_data, indent=2, ensure_ascii=False))

    return {"done": True}

# ------------------ Graph ------------------ #

# Create the graph
graph = StateGraph(EpicState)

# Add nodes
graph.add_node("parser", parser_node)
graph.add_node("router", element_router)
graph.add_node("evaluator", element_evaluator)
graph.add_node("refiner", refinement_node) # Refinement node added
graph.add_node("aggregate", aggregate_node)

# Set flow
graph.set_entry_point("parser")
graph.add_edge("parser", "router")

graph.add_conditional_edges(
    "router", lambda state: "aggregate" if state.done else "evaluator"
)
graph.add_conditional_edges(
    "evaluator", lambda state: "refiner" if state.refinement_needed else "router"
)
graph.add_edge("refiner", "router") # After refinement, go back to router to process next elements
graph.add_edge("aggregate", END)   # Add explicit end edge

# Compile the graph
epic_flow = graph.compile()

# ------------------ Run ------------------ #
if __name__ == "__main__":
    sample_epics = [
        """Title: Streamlined Smart Inventory Management for Retailers

        Problem Statement: Retailers face challenges in managing inventory efficiently, leading to stockouts, overstocking, and lost sales opportunities. A smart inventory management system is needed to provide real-time stock tracking, automated restocking recommendations, and analytics to enhance decision-making.

        User Stories:
        1. As a store manager, I want to view real-time inventory levels across all store locations, so I can identify low-stock items and plan restocking.
        2. As a warehouse staff member, I want to receive automated alerts for items that need restocking, so I can prioritize my tasks efficiently.""",

        """Title: Enhanced Customer Onboarding Flow

        Problem Statement: New users struggle with the current onboarding process, leading to high drop-off rates and increased support tickets during initial setup. This epic aims to redesign the onboarding experience to be more intuitive and guided, thereby improving user activation and reducing support overhead.

        Non-Functional Requirements:
        - The onboarding flow must load within 2 seconds on standard broadband connections.
        - User data collected during onboarding must comply with GDPR regulations."""
    ]

    for i, epic in enumerate(sample_epics, 1):
        print(f"\nEvaluating Epic {i}:")
        print("-" * 80)
        final_state = epic_flow.invoke(EpicState(raw_text=epic, epic_index=i))
        print("-" * 80)
        time.sleep(4) # Pause for 4 seconds