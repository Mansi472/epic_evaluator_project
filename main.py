import os
from dotenv import load_dotenv
import json
import logging
import google.generativeai as genai
from typing import Dict
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Google API key
google_api_key = os.getenv('GOOGLE_API_KEY')
if not google_api_key:
    raise ValueError("Please set GOOGLE_API_KEY in your .env file")

# Configure Google Gemini
genai.configure(api_key=google_api_key)

# Quality standards for epic evaluation
QUALITY_STANDARDS = """
Element: Title
Quality Standard:
- Short and concise (no more than 10 words)
- Descriptive (capture the essence of the epic)
- Convey the primary objective of the epic (value of doing the epic)
Example: "Enable Password Reset for Registered Users to Regain Account Access"

Element: Problem Statement
Quality Standard:
- Clear: Free of jargon and ambiguity, the description should be easy for all team members and stakeholders to understand
- Comprehensive: The problem statement needs to contain three elements: (1) A description of the problem being solved, (2) a high level description of the feature addressing, and (3) the value for the customer
- Concise: It should be written without unnecessary detail or redundancy
Example: "Users struggle to regain access to their accounts when they forget their passwords. The current process is difficult and customers are abandoning the product or require help from support agents. This epic will implement a password reset feature, integrated with existing user management systems, to enable users to regain access to their account. This feature will reduce customer support requests for password recovery by 30%, improving user retention and reducing operational costs."

Element: Product Outcome & Instrumentation
Quality Standard:
- Describes overall goals of this feature
- Good product goals should measure things like adoption, feature retention, satisfaction, engagement or impressions, general usage, completion percentages and speed
- Bad product goals are measurements around lagging metrics like churn, revenue, customer health, renewal, etc
- Instrumentation refers to metrics that can be used to measure the goals, e.g. click-throughs etc
Example: "Outcome: Reduce time to recover access by 50%, or increase number of users that can recover access to their account without help from support, Metric: Reduced number of support tickets on this topic"

Element: Requirements - User Stories
Quality Standard:
- Clear: Written in a clear and user-centric way to communicate requirements
- Structured: Written in a structured and consistent format to ensure clarity, understanding, and alignment across the team
- Complete: Complete in terms of what is needed for the overall feature
Structure should be as follows: As a [user role], I want [goal] so that [reason/benefit]
Example: "As a registered user, I need to be able to reset my password so that I can regain access to my account if I forget it."
"""

class EpicEvaluator:
    def __init__(self):
        logger.info("Initializing Gemini model...")
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("Model initialized successfully")

    def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemini model."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise

    def identify_elements(self, epic_text: str) -> Dict[str, str]:
        """Identifies and extracts elements from the epic text."""
        prompt = f"""Analyze the following epic and extract its elements.

Return ONLY a JSON object in this exact format, with no additional text or explanation:
{{
    "Title": "extracted title or empty string",
    "Problem Statement": "extracted problem statement or empty string",
    "Product Outcome & Instrumentation": "extracted outcome and instrumentation or empty string",
    "Requirements - User Stories": "extracted user stories or empty string",
    "Non-Functional Requirements": "extracted non-functional requirements or empty string"
}}

Epic to analyze:
{epic_text}

Remember: Only return the JSON object, nothing else."""

        try:
            response = self._generate_response(prompt)
            logger.info(f"Raw response: {response}")
            
            if not response:
                raise ValueError("Received empty response from API")
                
            # Clean up the response
            response = response.strip()
            
            # Try to find JSON in the response
            try:
                # First try direct JSON parsing
                return json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    raise ValueError("No JSON object found in response")
                    
                json_str = response[start_idx:end_idx + 1]
                return json.loads(json_str)
                
        except Exception as e:
            logger.error(f"Error parsing elements response: {str(e)}")
            raise ValueError(f"Failed to parse elements from epic: {str(e)}")

    def evaluate_element(self, element_name: str, element_content: str) -> Dict:
        """Evaluates a single epic element against quality standards."""
        if not element_content:
            return {
                "element": element_name,
                "quality": "Element Not Found",
                "explanation": "This element was not found in the epic text.",
                "recommendations": f"Add a {element_name} section following the quality standards provided."
            }

        prompt = f"""You are a quality assurance expert for Agile Epics. Evaluate the following epic element against the provided quality standards.

Quality Standards:
{QUALITY_STANDARDS}

Element to evaluate: {element_name}
Content: {element_content}

Return ONLY a JSON object in this exact format, with no additional text or explanation:
{{
    "quality": "HIGH|MEDIUM|LOW",
    "explanation": "your detailed explanation here",
    "recommendations": "your specific recommendations here"
}}

Remember: Only return the JSON object, nothing else."""

        try:
            response = self._generate_response(prompt)
            logger.info(f"Raw response for {element_name}: {response}")
            
            if not response:
                raise ValueError("Received empty response from API")
                
            # Clean up the response
            response = response.strip()
            
            # Try to find JSON in the response
            try:
                # First try direct JSON parsing
                result = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    raise ValueError("No JSON object found in response")
                    
                json_str = response[start_idx:end_idx + 1]
                result = json.loads(json_str)
            
            return {
                "element": element_name,
                **result
            }
        except Exception as e:
            logger.error(f"Error evaluating element {element_name}: {str(e)}")
            raise ValueError(f"Failed to evaluate element {element_name}: {str(e)}")

    def evaluate_epic(self, epic_text: str) -> Dict:
        """
        Evaluates an Agile Epic text and provides quality assessments.
        
        Args:
            epic_text (str): The full text of the Agile Epic to evaluate
            
        Returns:
            dict: A JSON object containing the evaluation results
        """
        try:
            # Step 1: Identify elements
            logger.info("Starting epic evaluation...")
            elements = self.identify_elements(epic_text)
            logger.info(f"Identified elements: {elements}")
            
            # Step 2: Evaluate each element
            assessments = []
            for element_name, content in elements.items():
                assessment = self.evaluate_element(element_name, content)
                assessments.append(assessment)
            
            return {"assessments": assessments}
            
        except Exception as e:
            logger.error(f"Error in epic evaluation: {str(e)}")
            raise

def save_to_json(data: Dict, filename: str):
    """Save data to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved results to {filename}")
    except Exception as e:
        logger.error(f"Error saving to {filename}: {str(e)}")

def main():
    # Create results directory if it doesn't exist
    results_dir = "evaluation_results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Test with sample inputs from the requirements
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

    evaluator = EpicEvaluator()
    
    for i, epic in enumerate(sample_epics, 1):
        print(f"\n--- Evaluating Sample Epic {i} ---")
        try:
            # Get current timestamp for unique filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(results_dir, f"epic_{i}_evaluation_{timestamp}.json")
            
            # Evaluate epic
            result = evaluator.evaluate_epic(epic)
            
            # Save to JSON file
            save_to_json(result, filename)
            
            # Print results
            print("\nFinal Evaluation:")
            print(json.dumps(result, indent=2))
            print(f"\nResults saved to: {filename}")
            
        except Exception as e:
            print(f"Error evaluating epic {i}: {str(e)}")

if __name__ == "__main__":
    main()