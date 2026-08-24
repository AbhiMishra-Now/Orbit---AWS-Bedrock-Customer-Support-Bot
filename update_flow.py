import boto3
import json
import time

REGION = "us-east-1"
FLOW_ID = "WW0DY2THC8"

def main():
    client = boto3.client("bedrock-agent", region_name=REGION)

    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()

    with open("online_shop_faq.md", "r", encoding="utf-8") as f:
        faq = f.read()

    full_prompt = template.replace("{{FAQ}}", faq)

    formatting_rule = """
OUTPUT FORMATTING INSTRUCTIONS:
- Speak directly to the customer as Orbit.
- NEVER output internal reasoning, categorization metadata, chain-of-thought analysis, or headers like "Platform Questions Response:" or "The user inquiry falls under...".
- Provide ONLY the direct, helpful conversational response to the customer.

Customer Query:
{{document}}
"""

    full_prompt += "\n" + formatting_rule

    print("Fetching Flow configuration...")
    flow_info = client.get_flow(flowIdentifier=FLOW_ID)
    definition = flow_info["definition"]

    # Update Node definition
    for node in definition["nodes"]:
        if node["name"] == "Prompt_1":
            inline = node["configuration"]["prompt"]["sourceConfiguration"]["inline"]
            inline["templateConfiguration"]["text"]["text"] = full_prompt
            inline["templateConfiguration"]["text"]["inputVariables"] = [
                {"name": "document"}
            ]
            inline["modelId"] = "us.amazon.nova-pro-v1:0"
            node["inputs"] = [
                {
                    "name": "document",
                    "type": "String",
                    "expression": "$.data"
                }
            ]

    # Update Connection definition so targetInput is "document"
    for conn in definition["connections"]:
        if conn["source"] == "FlowInputNode" and conn["target"] == "Prompt_1":
            conn["configuration"]["data"]["targetInput"] = "document"

    print("Updating Flow definition in Amazon Bedrock...")
    client.update_flow(
        flowIdentifier=FLOW_ID,
        name=flow_info["name"],
        executionRoleArn=flow_info["executionRoleArn"],
        definition=definition
    )

    print("Preparing Flow...")
    client.prepare_flow(flowIdentifier=FLOW_ID)

    time.sleep(5)

    print("Updating Flow Alias...")
    aliases = client.list_flow_aliases(flowIdentifier=FLOW_ID).get("flowAliasSummaries", [])
    alias_id = None
    for a in aliases:
        if a["name"] in ("TSTALIASID", "live", "default") or a["id"] == "TSTALIASID":
            alias_id = a["id"]
            break

    if alias_id:
        client.update_flow_alias(
            flowIdentifier=FLOW_ID,
            aliasIdentifier=alias_id,
            name="TSTALIASID",
            routingConfiguration=[{"flowVersion": "DRAFT"}]
        )
        print(f"Flow Alias {alias_id} updated successfully!")

    time.sleep(5)

    print("\nSUCCESS! Flow updated with strict turn-by-turn bug collection rules.")

if __name__ == "__main__":
    main()

