import json
import boto3

REGION = "us-east-1"
STACK_NAME = "bug-report-testing-stack"

def main():
    cfn = boto3.client("cloudformation", region_name=REGION)
    bedrock = boto3.client("bedrock", region_name=REGION)

    print("Retrieving CloudFormation testing stack outputs...")
    res = cfn.describe_stacks(StackName=STACK_NAME)
    outputs = res["Stacks"][0]["Outputs"]

    bucket_name = None
    role_arn = None

    for out in outputs:
        if out["OutputKey"] == "EvalDatasetBucketName":
            bucket_name = out["OutputValue"]
        elif out["OutputKey"] == "BedrockEvalRoleArn":
            role_arn = out["OutputValue"]

    if not bucket_name or not role_arn:
        print("Error: Could not find stack outputs from bug-report-testing-stack.")
        return

    print(f"Bucket Name: {bucket_name}")
    print(f"Role ARN: {role_arn}")

    dataset_s3_uri = f"s3://{bucket_name}/output_eval_dataset.jsonl"
    output_s3_uri = f"s3://{bucket_name}/eval-results/"

    import time
    job_name = f"orbit-eval-job-{int(time.time())}"
    job_description = "Bedrock Evaluation for Orbit Customer Support Chatbot"

    eval_config = {
        "automated": {
            "datasetMetricConfigs": [
                {
                    "taskType": "QuestionAndAnswer",
                    "dataset": {
                        "name": "OrbitEvalDataset",
                        "datasetLocation": {
                            "s3Uri": dataset_s3_uri
                        }
                    },
                    "metricNames": ["Builtin.Accuracy"]
                }
            ]
        }
    }

    inference_config = {
        "models": [
            {
                "bedrockModel": {
                    "modelIdentifier": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0"
                }
            }
        ]
    }

    output_config = {
        "s3Uri": output_s3_uri
    }

    print("Creating Bedrock Evaluation Job...")
    try:
        response = bedrock.create_evaluation_job(
            jobName=job_name,
            jobDescription=job_description,
            roleArn=role_arn,
            evaluationConfig=eval_config,
            inferenceConfig=inference_config,
            outputDataConfig=output_config
        )
        print("\nEvaluation Job Created Successfully!")
        print(f"Job ARN: {response.get('jobArn')}")
    except Exception as e:
        print(f"\nError creating evaluation job: {e}")

if __name__ == "__main__":
    main()