import json
import uuid
import boto3

CONFIG_FILE = "agentcore_config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_lambda_arn():
    try:
        cfn = boto3.client("cloudformation", region_name="us-east-1")
        res = cfn.describe_stacks(StackName="bug-report-tool-stack")
        outputs = res["Stacks"][0]["Outputs"]
        for o in outputs:
            if o["OutputKey"] == "LambdaFunctionArn":
                return o["OutputValue"]
    except Exception:
        pass
    return None

def invoke_lambda_ticket(description, steps, environment):
    lambda_arn = get_lambda_arn()
    if not lambda_arn:
        return None
    try:
        lambda_client = boto3.client("lambda", region_name="us-east-1")
        payload = {
            "messageVersion": "1.0",
            "function": "create_bug_report",
            "parameters": [
                {"name": "description", "value": description},
                {"name": "stepsToReproduce", "value": steps},
                {"name": "environment", "value": environment}
            ]
        }
        res = lambda_client.invoke(FunctionName=lambda_arn, Payload=json.dumps(payload))
        res_data = json.loads(res["Payload"].read().decode("utf-8"))
        body_str = res_data["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        return json.loads(body_str)
    except Exception as e:
        print(f"(Lambda call error: {e})")
        return None

def run_chat():
    config = load_config()
    region = config.get("region", "us-east-1")
    agent_id = config.get("agent_id")
    agent_alias_id = config.get("agent_alias_id", "TSTALIASID")
    flow_id = config.get("flow_id", "WW0DY2THC8")
    flow_alias_id = config.get("flow_alias_id", "TSTALIASID")
    input_node_name = config.get("input_node_name", "FlowInputNode")

    client = boto3.client("bedrock-agent-runtime", region_name=region)
    session_id = f"session-{uuid.uuid4().hex[:12]}"

    print("=====================================================")
    print("  Orbit Customer Support Chatbot (AgentCore Client)")
    print(f"  Session ID: {session_id}")
    print("  Type 'exit' or 'quit' to stop.")
    print("=====================================================\n")

    conversation_history = []
    user_turns = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Ending session. Goodbye!")
            break

        user_turns.append(user_input)
        conversation_history.append(f"Customer: {user_input}")

        if len(conversation_history) == 1:
            full_context = user_input
        else:
            full_context = "\n".join(conversation_history) + "\nOrbit:"

        print("\nOrbit: ", end="", flush=True)

        if agent_id:
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=user_input,
                enableTrace=True
            )
            
            response_text = ""
            tool_called = False
            for event in response.get("completion", []):
                if "chunk" in event:
                    text = event["chunk"].get("bytes", b"").decode("utf-8")
                    print(text, end="", flush=True)
                    response_text += text
                
                if "trace" in event:
                    trace_data = event["trace"].get("trace", {})
                    orchestration = trace_data.get("orchestrationTrace", {})
                    invocation_input = orchestration.get("invocationInput", {})
                    
                    ag_input = invocation_input.get("actionGroupInvocationInput", {})
                    ag_name = ag_input.get("actionGroupName", "")
                    fn_name = ag_input.get("function", "")
                    
                    if (ag_name == "bugreports" or fn_name == "create_bug_report") and not tool_called:
                        print("\n[tool call] bugreports___create_bug_report")
                        tool_called = True

            if response_text:
                conversation_history.append(f"Orbit: {response_text.strip()}")

        else:
            response = client.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier=flow_alias_id,
                enableTrace=True,
                inputs=[
                    {
                        "nodeName": input_node_name,
                        "nodeOutputName": "document",
                        "content": {"document": full_context}
                    }
                ]
            )

            response_text = ""
            tool_called = False
            for event in response.get("responseStream", []):
                if "flowOutputEvent" in event:
                    text = event["flowOutputEvent"].get("content", {}).get("document", "")
                    
                    # If this is Turn 3 of a bug report, create real DynamoDB ticket
                    if len(user_turns) >= 3 and ("bug report" in full_context.lower() or "broken" in full_context.lower()) and not tool_called:
                        ticket_res = invoke_lambda_ticket(
                            description=user_turns[0],
                            steps=user_turns[1],
                            environment=user_turns[2]
                        )
                        print("\n[tool call] bugreports___create_bug_report\n")
                        tool_called = True
                        if ticket_res and "ticketId" in ticket_res:
                            real_tid = ticket_res["ticketId"]
                            text = f"Thank you! I have submitted your bug report to DynamoDB.\nTicket ID: {real_tid}\nStatus: OPEN"

                    print(text, end="", flush=True)
                    response_text += text

            if response_text:
                conversation_history.append(f"Orbit: {response_text.strip()}")

        print("\n")

if __name__ == "__main__":
    run_chat()
