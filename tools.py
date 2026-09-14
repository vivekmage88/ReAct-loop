import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# SKu Check function
def find_sku_by_name(product_name: str) -> dict:
    catalog = {
        "leather backpack": "SKU-BAG-001",
        "cotton t-shirt": "SKU-CLO-002",
        "steel watch": "SKU-JEW-001",
    }
    key = product_name.strip().lower()
    if key not in catalog:
        return {"error": f"No product found with the name {product_name}"}
    return {"sku": catalog[key]}

# Order status check function
def get_order_status(order_id: str) -> dict:
    fake_orders = {
        "1001": {"status": "shipped", "total": "249.50", "courier": "BlueDart"},
        "1002": {"status": "processing", "total": "99.00", "courier": None},
        "1003": {"status": "cancelled", "total": "150.00", "courier": None},
    }

    if order_id not in fake_orders:
        return {"error": f"No order found with id {order_id}"}

    return fake_orders[order_id]

# Inventory check function
def check_inventory(sku:str):
    fake_inventory = {
        "SKU-BAG-001": {"in_stock": True, "quantity": 12},
        "SKU-CLO-002": {"in_stock": False, "quantity": 0},
        "SKU-JEW-001": {"in_stock": True, "quantity": 3},
    }
    if sku not in fake_inventory:
        return {"error": f"NO Sku found wuth this sku {sku}"}
    return fake_inventory[sku]

# Tool schema to Guide an LLM to which tool to use on conditional basis with prompt & Description
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up the current status of a customer order by its ID. Use this whenever a customer asks about an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, for example 1001",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check stock level for a product by its exact SKU. If the user gave a product name rather than a SKU, call find_sku_by_name first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "The product sku, for example SKU-BAG-001",
                    }
                },
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_sku_by_name",
            "description": "Find a product's SKU from its name. Use this when the user refers to a product by name instead of a SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The product, for example leather backpack",
                    }
                },
                "required": ["product_name"],
            },
        },
    }   
]

def run_tool(name: str, arguments: dict) -> dict:
    if name == "get_order_status":
        return get_order_status(**arguments)
    if name == "check_inventory":
        return check_inventory(**arguments)
    if name == "find_sku_by_name":
        return find_sku_by_name(**arguments)
    return {"error": f"Unknown tool: {name}"}

# Main Function to call LLM
def ask(question: str, max_rounds: int = 5) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [{"role": "user", "content": question}]

    for round_num in range(max_rounds):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        print(f"round {round_num + 1}: {[c.function.name for c in message.tool_calls]}")
        messages.append(message)

        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments)
            result = run_tool(call.function.name, arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "Gave up after too many tool rounds."
if __name__ == "__main__":
    print(ask("do you have the running shoes?"))