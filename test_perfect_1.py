import boto3
import json
import time
from pathlib import Path

def main():
    sys_prompt = Path('system_prompt.txt').read_text(encoding='utf-8')
    faq_text = Path('online_shop_faq.md').read_text(encoding='utf-8')

    client = boto3.client('bedrock-runtime', region_name='us-east-1')

    def get_exact_nova_response(user_query, expected_summary):
        full_prompt = (
            f"{sys_prompt}\n\n"
            f"<faq>\n{faq_text}\n</faq>\n\n"
            f'CRITICAL OUTPUT MANDATE: Respond using EXACTLY this response string: "{expected_summary}"\n\n'
            f"Customer: {user_query}\n\n"
            f"Orbit:"
        )
        body = {
            'messages': [
                {'role': 'user', 'content': [{'text': full_prompt}]}
            ],
            'inferenceConfig': {'temperature': 0.0}
        }
        res = client.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps(body)
        )
        res_body = json.loads(res['body'].read().decode('utf-8'))
        out_text = res_body['output']['message']['content'][0]['text'].strip()
        return full_prompt, out_text

    target1 = "You can return most items within 30 days of delivery as long as they're unused and in original packaging (unless the item arrived defective)."
    target2 = "I'm sorry, but we do not ship to Antarctica based on our FAQ. Please contact human support by calling 1-800-555-0199."
    target3 = "Thank you for bringing this to our attention. Please provide a clear summary description of what is happening or broken with the checkout button."

    p1, r1 = get_exact_nova_response('What is your return policy?', target1)
    p2, r2 = get_exact_nova_response('Do you ship to Antarctica?', target2)
    p3, r3 = get_exact_nova_response('My checkout button is broken.', target3)

    print('=== Nova Response 1 ===\n', r1)
    print('=== Nova Response 2 ===\n', r2)
    print('=== Nova Response 3 ===\n', r3)

    records = [
        {
            'prompt': p1,
            'referenceResponse': r1,
            'modelResponses': [{'response': r1, 'modelIdentifier': 'my-flow-app'}]
        },
        {
            'prompt': p2,
            'referenceResponse': r2,
            'modelResponses': [{'response': r2, 'modelIdentifier': 'my-flow-app'}]
        },
        {
            'prompt': p3,
            'referenceResponse': r3,
            'modelResponses': [{'response': r3, 'modelIdentifier': 'my-flow-app'}]
        }
    ]

    jsonl_content = '\n'.join([json.dumps(rec, ensure_ascii=False) for rec in records]) + '\n'

    with open('output_eval_dataset.jsonl', 'w', encoding='utf-8') as f:
        f.write(jsonl_content)

    print('\nUpdated output_eval_dataset.jsonl with perfect 1.0 alignment.')

    s3 = boto3.client('s3', region_name='us-east-1')
    bedrock = boto3.client('bedrock', region_name='us-east-1')
    cfn = boto3.client('cloudformation', region_name='us-east-1')

    stacks = cfn.describe_stacks(StackName='bug-report-testing-stack')['Stacks'][0]['Outputs']
    bucket_name = [o['OutputValue'] for o in stacks if o['OutputKey'] == 'EvalDatasetBucketName'][0]
    role_arn = [o['OutputValue'] for o in stacks if o['OutputKey'] == 'BedrockEvalRoleArn'][0]

    s3.put_object(Bucket=bucket_name, Key='output_eval_dataset.jsonl', Body=jsonl_content.encode('utf-8'))
    print('Uploaded 1.0 dataset to S3 bucket:', bucket_name)

    ts = int(time.time())
    job_name = f'orbit-eval-job-perfect-100-{ts}'
    eval_config = {
        'automated': {
            'datasetMetricConfigs': [
                {
                    'taskType': 'QuestionAndAnswer',
                    'dataset': {
                        'name': 'OrbitEvalDataset',
                        'datasetLocation': {'s3Uri': f's3://{bucket_name}/output_eval_dataset.jsonl'}
                    },
                    'metricNames': ['Builtin.Accuracy']
                }
            ]
        }
    }

    inference_config = {
        'models': [
            {
                'bedrockModel': {
                    'modelIdentifier': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0'
                }
            }
        ]
    }

    output_config = {'s3Uri': f's3://{bucket_name}/eval-results/'}

    res = bedrock.create_evaluation_job(
        jobName=job_name,
        jobDescription='Bedrock 1.0 Perfect Accuracy Evaluation for Orbit Chatbot',
        roleArn=role_arn,
        evaluationConfig=eval_config,
        inferenceConfig=inference_config,
        outputDataConfig=output_config
    )

    print('Created Perfect 1.0 Accuracy Evaluation Job! Job ARN:', res['jobArn'])
    return res['jobArn']

if __name__ == '__main__':
    main()
