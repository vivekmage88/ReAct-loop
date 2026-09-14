# Tool Calling

A minimal agent loop using OpenAI function calling. The model is given three read-only tools over a fake product catalog and decides which to call, in what order, to answer a question.

No framework — just the OpenAI SDK and a `while` loop, so the mechanics are visible.

---

## The idea

The model cannot run code. It emits a structured request saying which function it wants called and with what arguments. Your code validates the request, executes it, and sends the result back. The model then either answers or asks for another tool.

```
question + tool schemas ──> model
                              │
                     ┌────────┴────────┐
                 no tool           tool call
                     │                 │
                answer         your code validates
                                       │
                               your code executes
                                       │
                               result sent back ──┐
                                       │          │
                                       └──────────┘
```

The loop exits when the model stops requesting tools.

---

## Tools

| Tool | Input | Returns |
|---|---|---|
| `get_order_status` | order ID | status, total, courier |
| `check_inventory` | exact SKU | in-stock flag, quantity |
| `find_sku_by_name` | product name | matching SKU |

---

## Multi-step tool use

Asking *"do you have the leather backpack?"* takes two rounds, because the question gives a product name and `check_inventory` needs a SKU:

```
round 1: ['find_sku_by_name']
round 2: ['check_inventory']

Yes, we have the leather backpack in stock. There are 12 available.
```

The second call depends on the first call's output. That chaining is what separates an agent from a function router.

A question the tools cannot answer exits in one round:

```
round 1: ['find_sku_by_name']

It seems I couldn't find any product listed under the name "running shoes."
```

And a question unrelated to the tools makes no tool call at all — one API call rather than two.

---

## Notes

**The model never executes anything.** It produces text; a tool call is structured text meaning *please run this*. `run_tool` maps a name to a function through an explicit list of branches. Dynamic lookup such as `globals()[name](**arguments)` would let the model call anything in the program.

**A tool call is untrusted input.** The model emits calls based on text it has read, which may include user input or document contents. With write operations — cancel an order, issue a refund — authorisation belongs in the executing code, not in the prompt. A system prompt is not a security control.

**Tools return dicts, never raise.** A missing order returns `{"error": "No order found with id 9999"}`, which the model relays as a sentence. An exception would break the loop instead of becoming part of the conversation.

**`max_rounds` bounds the loop.** A confused model can request the same tool indefinitely. Every agent needs a cap.

**Descriptions are prompts.** The model chooses tools by reading the `description` field. During development, the note "requires an exact SKU, call find_sku_by_name first" was attached to the wrong tool, and the model consistently skipped the inventory check — returning a plausible answer reached by the wrong route, with no error to indicate it.

**The model is stateless.** Conversation memory is the full message list resent on every call. It grows without limit and every token is billed on every turn, so production systems truncate or summarise older turns.

---

## What this cannot do

- Branch on state — every round has the same shape
- Persist across a restart — kill the process and the conversation is gone
- Track anything beyond the message list, such as retry counts or approval status
- Be inspected easily when it misbehaves

Those are the problems a graph-based framework addresses.

---

## Run it

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install openai python-dotenv

cp .env.example .env   # add OPENAI_API_KEY
python tools.py
```
