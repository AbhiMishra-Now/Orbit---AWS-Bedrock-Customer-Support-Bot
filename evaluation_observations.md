# Orbit Customer Support Chatbot - Evaluation Observations & Test Results

## 1. Test Suite Overview (`flow-tests.json`)
The evaluation dataset was generated using `flow-tests.json`, which contains representative test cases covering all 3 required execution paths:
1. **Platform Question Path (`test-1-covered-faq-returns`)**:
   - **Prompt**: `"What is your return policy?"`
   - **Expected Behavior**: Grounded response citing the 30-day return policy directly from `online_shop_faq.md`.
2. **Other Requests Path (`test-2-uncovered-faq-redirect`)**:
   - **Prompt**: `"Do you ship to Antarctica?"`
   - **Expected Behavior**: Polite decline for unlisted shipping destinations + redirect to human support at `1-800-555-0199`.
3. **Bug Report Path (`test-3-bug-report-turn-1`)**:
   - **Prompt**: `"My checkout button is broken."`
   - **Expected Behavior**: Acknowledges the issue politely and asks for the summary `description` as the first required parameter without prematurely invoking tools.

---

## 2. Evaluation Dataset (`output_eval_dataset.jsonl`)
- **Format**: Valid JSON Lines (`JSONL`) storing 1 valid JSON object per line.
- **Validation**: Verified with `Get-Content output_eval_dataset.jsonl | ForEach-Object { $_ | ConvertFrom-Json }`.
- **Destination**: Uploaded to S3 evaluation bucket `mak-support-eval-026090557065`.

---

## 3. Bedrock Evaluation Job & Correctness Score
- **Bedrock Evaluation Job ARN**: `arn:aws:bedrock:us-east-1:026090557065:evaluation-job/oae0j0dv9vac`
- **Evaluator Model**: `amazon.nova-pro-v1:0` (Amazon Nova Pro)
- **Task Type**: `QuestionAndAnswer`
- **Metric**: `Builtin.Accuracy`
- **Observations & Analysis**:
  - All test cases aligned 100% with the required system prompt routing and grounded FAQ context.
  - The model correctly routes platform questions to `online_shop_faq.md` without hallucinating policies.
  - The model correctly enforces human support fallback (`1-800-555-0199`) for out-of-scope requests.
  - The model strictly enforces sequential parameter collection before bug report ticket creation.
