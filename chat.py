import json
import uuid
import boto3

CONFIG_FILE = "agentcore_config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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

        print("\nOrbit: ", end="", flush=True)

        if agent_id:
            # AgentCore Harness invoke_agent
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=user_input,
                enableTrace=True
            )
            
            tool_called = False
            for event in response.get("completion", []):
                if "chunk" in event:
                    text = event["chunk"].get("bytes", b"").decode("utf-8")
                    print(text, end="", flush=True)
                
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

        else:
            # Bedrock Runtime Flow Client
            response = client.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier=flow_alias_id,
                enableTrace=True,
                inputs=[
                    {
                        "nodeName": input_node_name,
                        "nodeOutputName": "document",
                        "content": {"document": user_input}
                    }
                ]
            )

            tool_called = False
            for event in response.get("responseStream", []):
                if "flowOutputEvent" in event:
                    text = event["flowOutputEvent"].get("content", {}).get("document", "")
                    print(text, end="", flush=True)
                
                if "flowTraceEvent" in event:
                    trace_data = event["flowTraceEvent"].get("trace", {})
                    node_name = str(trace_data.get("nodeName", ""))
                    if ("Lambda" in node_name or "bugreports" in node_name) and not tool_called:
                        print("\n[tool call] bugreports___create_bug_report")
                        tool_called = True

        print("\n")

if __name__ == "__main__":
    run_chat()
