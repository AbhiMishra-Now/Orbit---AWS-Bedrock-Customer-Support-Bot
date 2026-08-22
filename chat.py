#!/usr/bin/env python3
import json
import os
import sys
import uuid
import boto3

CONFIG_FILE = "agentcore_config.json"

def main():
    flow_id = None
    flow_alias_id = None
    node_name = "FlowInputNode"

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            flow_id = config.get("flow_id")
            flow_alias_id = config.get("flow_alias_id")
            node_name = config.get("input_node_name", "FlowInputNode")

    if not flow_id:
        flow_id = input("Enter your Bedrock Flow ID: ").strip()
    if not flow_alias_id:
        flow_alias_id = input("Enter your Bedrock Flow Alias ID (or press Enter for default TSTALIASID): ").strip() or "TSTALIASID"

    # Save to config for future runs
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "flow_id": flow_id,
            "flow_alias_id": flow_alias_id,
            "input_node_name": node_name,
            "region": "us-east-1"
        }, f, indent=2)

    session = boto3.Session(region_name="us-east-1")
    client = session.client("bedrock-agent-runtime")

    print("\n=====================================================")
    print("  Orbit Customer Support Chatbot (Bedrock Flow Client)")
    print(f"  Flow ID: {flow_id} | Alias: {flow_alias_id}")
    print("  Type 'exit' or 'quit' to stop.")
    print("=====================================================\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Ending chat session. Goodbye!")
                break

            resp = client.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier=flow_alias_id,
                inputs=[
                    {
                        "nodeName": node_name,
                        "nodeOutputName": "document",
                        "content": {"document": user_input}
                    }
                ]
            )

            last_text = None
            for event in resp.get("responseStream", []):
                if "flowOutputEvent" in event:
                    oe = event["flowOutputEvent"]
                    last_text = oe.get("content", {}).get("document")
                    break
                elif "flowMultiTurnInputRequestEvent" in event:
                    ce = event["flowMultiTurnInputRequestEvent"]
                    last_text = ce.get("content", {}).get("document")
                    break

            if last_text:
                print(f"Orbit: {last_text}\n")
            else:
                print("Orbit: (Response received)\n")

        except KeyboardInterrupt:
            print("\nExiting session...")
            break
        except Exception as e:
            print(f"Error during chat invocation: {e}\n")

if __name__ == "__main__":
    main()

