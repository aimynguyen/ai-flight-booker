from agents.plan_then_execute import execute_plan


request = """
Book me the cheapest valid flight from SGN to DAD
on 2026-10-07.

The flight must depart before 12:00
and cost at most 2,000,000 VND.

Complete the booking and payment.
"""


result = execute_plan(request)

print("\n===== FINAL RESULT =====\n")
print(result)
