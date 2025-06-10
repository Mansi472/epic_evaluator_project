# Epic Evaluator - Detailed Workflow & Functionality Explanation

## Table of Contents
1. [Overview](#overview)
2. [Code Structure](#code-structure)
3. [Workflow Steps](#workflow-steps)
4. [Component Details](#component-details)
5. [Quality Standards](#quality-standards)
6. [Example Usage](#example-usage)

## Overview

The Epic Evaluator is an AI-powered tool that analyzes and evaluates Agile Epics using Google's Gemini AI model. It helps teams improve their epic quality by providing detailed feedback and recommendations.

## Code Structure

```
epic_evaluator_project/
├── main.py              # Main application file
├── requirements.txt     # Project dependencies
├── README.md           # Project documentation
├── workflow.md         # Workflow documentation
├── Explanation.md      # Code implementation guide
└── evaluation_results/ # Output directory
```

## Workflow Steps

1. **Epic Parsing**
   - Input: Raw epic text
   - Process: Extracts key elements (Title, Problem Statement, etc.)
   - Output: Structured dictionary of epic elements

2. **Element Routing**
   - Input: Parsed epic elements
   - Process: Determines next element to evaluate
   - Output: Current element and content for evaluation

3. **Quality Evaluation**
   - Input: Single epic element
   - Process: Evaluates against quality standards
   - Output: Quality score (HIGH/MEDIUM/LOW) with explanations

4. **Refinement (if needed)**
   - Input: LOW quality elements
   - Process: Generates detailed improvement suggestions
   - Output: Additional actionable feedback

5. **Report Generation**
   - Input: All evaluations
   - Process: Compiles final report
   - Output: JSON file with timestamp

## Component Details

### 1. State Management
```python
class EpicState(BaseModel):
    raw_text: str                      # Original epic text
    parsed: Optional[Dict] = None      # Parsed elements
    evaluations: List[ElementEvaluation] = []  # Evaluation results
    current_element: Optional[str] = None      # Current element being processed
    current_content: Optional[str] = None      # Content of current element
    refinement_needed: Optional[bool] = False  # Refinement flag
    done: bool = False                 # Processing complete flag
    epic_index: Optional[int] = None   # Epic identifier
```

### 2. Quality Evaluation Model
```python
class ElementEvaluation(BaseModel):
    element: str         # Element name
    quality: str        # HIGH/MEDIUM/LOW
    explanation: str    # Quality justification
    recommendations: str # Improvement suggestions
    feedback: Optional[str] = None  # Detailed feedback for LOW quality
```

## Quality Standards

### Title Standards
- **HIGH**: Clear, concise, specific, and memorable
- **MEDIUM**: Clear but could be more specific or engaging
- **LOW**: Vague, too long, or unclear

### Problem Statement Standards
- **HIGH**: Clear problem, quantified impact, specific context
- **MEDIUM**: Problem identified but impact or context unclear
- **LOW**: Vague problem, no context or impact stated

### Product Outcome Standards
- **HIGH**: Specific, measurable outcomes with clear metrics
- **MEDIUM**: Outcomes stated but metrics unclear
- **LOW**: No clear outcomes or measurements

### User Stories Standards
- **HIGH**: Complete user stories (As a..., I want..., So that...)
- **MEDIUM**: Basic user stories with some missing elements
- **LOW**: Incomplete or unclear user stories

### Non-Functional Requirements Standards
- **HIGH**: Specific, measurable, testable requirements
- **MEDIUM**: Requirements stated but not fully measurable
- **LOW**: Vague or missing requirements

## Example Usage

### Input Epic Example
```
Title: Streamlined Smart Inventory Management

Problem Statement: 
Retailers face challenges in managing inventory efficiently, 
leading to stockouts and overstocking.

User Stories:
As a store manager, I want to view real-time inventory levels,
so I can identify low-stock items.
```

### Output Example
```json
{
  "element": "Title",
  "quality": "MEDIUM",
  "explanation": "The title is clear but could be more specific...",
  "recommendations": "Add industry context and specific value...",
  "feedback": null
}
```

## Error Handling & Reliability

1. **Retry Logic**
   - Maximum 3 retries for LLM calls
   - Rate limiting with 1-second delays
   - Detailed error messages

2. **Validation**
   - Quality score validation
   - Minimum explanation length (20 words)
   - API key verification

3. **Output Safety**
   - Unique file names with timestamps
   - UTF-8 encoding
   - Pretty-printed JSON format

## Best Practices for Epic Writing

1. **Title**
   - Be specific and memorable
   - Include the main value proposition
   - Keep it concise

2. **Problem Statement**
   - Quantify the impact
   - Provide clear context
   - State the current challenges

3. **Product Outcomes**
   - Define measurable metrics
   - Include success criteria
   - Specify measurement methods

4. **User Stories**
   - Use standard format
   - Include acceptance criteria
   - Focus on user value

5. **Non-Functional Requirements**
   - Make them measurable
   - Include specific metrics
   - Define acceptance criteria 