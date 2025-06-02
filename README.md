# Epic Evaluator

A tool to evaluate Agile Epics based on predefined quality standards using Google's Gemini AI model.

## Setup Instructions

### 1. Create and Activate Virtual Environment

For Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

For Linux/Mac:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Running the Application
```bash
python main.py
```

## Features
- Evaluates epic titles
- Analyzes problem statements
- Assesses product outcomes and instrumentation
- Reviews user stories
- Provides quality ratings and recommendations

## Output
The evaluation results will be saved in JSON format in the `evaluation_results` directory.

## Usage

Run the main script:
```bash
python main.py
```

The script will evaluate sample Agile Epics and provide detailed assessments including:
- Title evaluation
- Problem Statement analysis
- Product Outcome & Instrumentation review
- Requirements/User Stories assessment
- Non-Functional Requirements evaluation

Each element is rated as HIGH, MEDIUM, or LOW quality with detailed explanations and recommendations for improvement.

## Environment Variables

Required environment variables:
- `GOOGLE_API_KEY`: Your Google API key for accessing the Gemini API

## Sample Output

The program will output JSON-formatted evaluations for each epic, including:
- Quality ratings
- Detailed explanations
- Actionable recommendations

## Error Troubleshooting

If you encounter LLM-related errors, please check:
1. Your API key is correctly set in the `.env` file
2. You have enabled the Gemini API in your Google Cloud Console
3. Your API key has the necessary permissions
4. You have sufficient API quota available 