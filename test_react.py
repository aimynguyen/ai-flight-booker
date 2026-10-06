from agents.react_agent import agent


result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": """
Book me the cheapest valid flight from SGN to DAD
on 2026-10-07.

The flight must depart before 12:00
and cost at most 2,000,000 VND.

Complete the booking and payment.
"""
        }
    ]
})


print("\n===== FINAL RESULT =====\n")

print(result)


print("\n===== MESSAGES =====\n")

for message in result["messages"]:

    print("\n--------------------")

    print(type(message).__name__)

    print(message.content)

    if hasattr(message, "tool_calls") and message.tool_calls:
        print("TOOL CALLS:")

        for call in message.tool_calls:
            print(call)
