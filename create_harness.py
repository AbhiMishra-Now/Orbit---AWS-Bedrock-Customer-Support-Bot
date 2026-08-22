#!/usr/bin/env python3
import json
import os
import sys
import boto3

REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-pro-v1:0"
STACK_NAME = "bug-report-tool-stack"
CONFIG_FILE = "agentcore_config.json"

def get_lambda_arn(cfn_client):
    try:
        res = cfn_client.describe_stacks(StackName=STACK_NAME)
        outputs = res["Stacks"][0]["Outputs"]
        for out in outputs:
            if out["OutputKey"] == "LambdaFunctionArn":
                return out["OutputValue"]
    except Exception as e:
        print(f"Warning: Could not get Lambda ARN from CloudFormation: {e}")
    return None

def main():
    print("Reading system prompt and FAQ...")
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    with open("online_shop_faq.md", "r", encoding="utf-8") as f:
        faq_content = f.read()

    full_prompt = prompt_template.replace("{{FAQ}}", faq_content)

    cfn_client = boto3.client("cloudformation", region_name=REGION)
    bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
    iam_client = boto3.client("iam", region_name=REGION)

    lambda_arn = get_lambda_arn(cfn_client)

    # 1. Ensure Agent Execution Role exists or create a minimal one
    role_name = "OrbitBedrockAgentRole"
    try:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
    except iam_client.exceptions.NoSuchEntityException:
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        role_res = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Role for Orbit Bedrock Agent"
        )
        role_arn = role_res["Role"]["Arn"]
        
        # Attach AmazonBedrockFullAccess policy or custom inline policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        )
        if lambda_arn:
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="InvokeLambdaPolicy",
                PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "lambda:InvokeFunction",
                            "Resource": lambda_arn
                        }
                    ]
                })
            )
        import time
        print("Waiting for IAM Role propagation...")
        time.sleep(10)

    # 2. Check if agent exists
    agents = bedrock_agent.list_agents().get("agentSummaries", [])
    agent_id = None
    for a in agents:
        if a["agentName"] == "OrbitCustomerSupportAgent":
            agent_id = a["agentId"]
            break

    if agent_id:
        print(f"Updating existing Bedrock Agent (ID: {agent_id})...")
        res = bedrock_agent.update_agent(
            agentId=agent_id,
            agentName="OrbitCustomerSupportAgent",
            agentResourceRoleArn=role_arn,
            foundationModel=MODEL_ID,
            instruction=full_prompt
        )
    else:
        print("Creating new Bedrock Agent OrbitCustomerSupportAgent...")
        res = bedrock_agent.create_agent(
            agentName="OrbitCustomerSupportAgent",
            agentResourceRoleArn=role_arn,
            foundationModel=MODEL_ID,
            instruction=full_prompt
        )
        agent_id = res["agent"]["agentId"]

    # 3. Create or Update Action Group for Bug Reporting
    if lambda_arn:
        action_groups = bedrock_agent.list_agent_action_groups(
            agentId=agent_id,
            agentVersion="DRAFT"
        ).get("actionGroupSummaries", [])
        
        ag_exists = any(ag["actionGroupName"] == "bugreports" for ag in action_groups)
        
        ag_params = {
            "agentId": agent_id,
            "agentVersion": "DRAFT",
            "actionGroupName": "bugreports",
            "actionGroupExecutor": {"lambda": lambda_arn},
            "functionSchema": {
                "functions": [
                    {
                        "name": "create_bug_report",
                        "description": "Create a bug report ticket in DynamoDB",
                        "parameters": {
                            "description": {"type": "string", "description": "Bug description", "required": True},
                            "stepsToReproduce": {"type": "string", "description": "Steps to reproduce", "required": True},
                            "environment": {"type": "string", "description": "User environment", "required": True}
                        }
                    }
                ]
            }
        }

        if ag_exists:
            bedrock_agent.update_agent_action_group(**ag_params, actionGroupId="bugreports")
        else:
            bedrock_agent.create_agent_action_group(**ag_params)

    # 4. Prepare Agent
    print("Preparing agent...")
    bedrock_agent.prepare_agent(agentId=agent_id)

    # Agent Alias (default to TSTALIASID)
    alias_id = "TSTALIASID"

    config = {
        "agent_id": agent_id,
        "agent_alias_id": alias_id,
        "harness_arn": f"arn:aws:bedrock:{REGION}:agent/{agent_id}",
        "lambda_arn": lambda_arn,
        "region": REGION,
        "model_id": MODEL_ID
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Harness successfully updated and saved to {CONFIG_FILE}!")
    print(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()

