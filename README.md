# Orbit: Customer Support Chatbot with Amazon Bedrock AgentCore

## Project Overview
**Orbit** is an intelligent customer support chatbot designed for a fictional online shop. Built using **Amazon Bedrock AgentCore**, it demonstrates advanced prompt engineering by handling complex routing, multi-turn information gathering, and tool execution without external classifiers or condition nodes.

The chatbot classifies user intent into three distinct paths:
1.  **Bug Reports:** Collects description, reproduction steps, and environment details one-by-one before filing a ticket via Lambda.
2.  **Platform Questions:** Answers queries about orders, shipping, and returns using an embedded FAQ document.
3.  **Other Requests:** Politely redirects out-of-scope inquiries to human support.

## AWS Services & Technology Stack
This project leverages a serverless architecture on AWS:

*   **Amazon Bedrock AgentCore (Managed Harness):** Orchestrates the agent loop, session memory, and model inference.
*   **Amazon Nova Pro (`us.amazon.nova-pro-v1:0`):** The foundational model powering Orbit's reasoning and natural language generation.
*   **AWS Lambda:** Executes the `create_bug_report` tool to persist data.
*   **Amazon DynamoDB:** Stores bug report tickets with high availability (configured for 12k RPS / 4k WPS).
*   **Amazon Bedrock Flows:** Used for visual orchestration and testing of the support logic.
*   **Amazon Bedrock Evaluations:** Automated LLM-as-a-judge testing to verify response correctness.

## Key Features & Implementation Details

### 1. Single-Prompt Routing Architecture
Unlike traditional flows that use separate classifier nodes, Orbit relies entirely on a highly optimized `system_prompt.txt`. This prompt enforces strict category definitions and prevents hallucination by grounding FAQ answers exclusively in the provided reference document.

### 2. Stateful Multi-Turn Bug Collection
For bug reports, Orbit does not overwhelm the user. It uses the harness's stateful session memory to collect three required fields (`description`, `stepsToReproduce`, `environment`) sequentially. The tool is only invoked once all data is verified.

### 3. Security Guardrails
The system prompt includes explicit instructions to resist prompt injection attempts, ensuring Orbit remains focused on customer support tasks and protects internal logic.

## Evidence of Implementation

### A. Visual Flow Orchestration
The support logic is visually mapped in Amazon Bedrock Flows, connecting user input through prompt processing and Lambda execution to the final output.
 <img width="1359" height="566" alt="brave_screenshot_us-east-1 console aws amazon com (4)" src="https://github.com/user-attachments/assets/f74d4e08-6f5b-4417-ac84-fe515e17d9b6" />

*(See screenshot: OrbitCustomerSupportFlow showing Prompt Node connected to Lambda Function Node)*

### B. Tool Execution & Data Persistence
When a bug is reported, Orbit triggers the `create-bug-report` Lambda function. The function receives structured parameters and successfully writes to DynamoDB.
<img width="1290" height="523" alt="brave_screenshot_us-east-1 console aws amazon com (3)" src="https://github.com/user-attachments/assets/eaafb33f-e43f-4b6b-81a8-52120be49a03" />

*(See screenshot: Lambda console showing successful event with description, steps, and environment)*

### C. Infrastructure Scalability
The backend is supported by a provisioned DynamoDB table capable of handling peak traffic loads without latency.
<img width="701" height="206" alt="brave_screenshot_us-east-1 console aws amazon com (2)" src="https://github.com/user-attachments/assets/aca8ebf1-8230-4f2b-be8e-880709eccc7e" />
*(See screenshot: BugReports table active with 12,000 Read Units/sec capacity)*

## Testing & Evaluation
Automated testing was conducted using `harness-tests.json` covering all three routing categories, including edge cases. Results were evaluated via **Bedrock Evaluations** using the `Builtin.Correctness` metric, confirming high accuracy in intent classification and response grounding.

## How to Run Locally
1.  Ensure AWS CLI is configured for `us-east-1`.
2.  Deploy infrastructure: `aws cloudformation deploy --template-file cloudformation-tool.yaml ...`
3.  Setup Gateway: `python setup_gateway.py`
4.  Update Prompt: Edit `system_prompt.txt` and run `python create_harness.py`
5.  Chat: `python chat.py`

## Author
Built as part of the AWS Agent Engineer Project 1 .
