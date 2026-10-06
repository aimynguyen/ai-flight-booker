import tools
import agents.react_agent as react_module

from agents.react_agent import agent as react_agent
from agents.plan_then_execute import execute_plan
from agents.hybrid_agent import execute_hybrid
from harness import BudgetTracker, LoopDetector


REQUEST = """
Book me the cheapest valid flight from SGN to DAD
on 2026-10-07.

The flight must depart before 12:00
and cost at most 2,000,000 VND.

Complete the booking and payment.
"""


def reset_state(case_name):
    tools.CASE = case_name
    tools.BOOKINGS.clear()

    for flights in tools.FLIGHTS.values():
        for flight in flights:
            flight.available_seats = 5

    react_module.budget_tracker = BudgetTracker()
    react_module.loop_detector = LoopDetector()


def count_react_steps(result):
    steps = 0

    for message in result["messages"]:
        if hasattr(message, "tool_calls") and message.tool_calls:
            steps += len(message.tool_calls)

    return steps


def check_react_success(result):
    for message in result["messages"]:
        content = str(message.content).lower()

        if "successfully booked and paid" in content:
            return True

        if "booking completed successfully" in content:
            return True

        if "paid" in content and "booking code" in content:
            return True

    return False


def check_react_adaptive(result):
    book_attempts = 0

    for message in result["messages"]:
        if not hasattr(message, "tool_calls"):
            continue

        for call in message.tool_calls:
            if call.get("name") == "book_seat_tool":
                book_attempts += 1

    return "Yes" if book_attempts > 1 else "No"


def run_react(case_name):
    reset_state(case_name)

    try:
        result = react_agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": REQUEST
                }
            ]
        })

        return {
            "agent": "ReAct",
            "success": check_react_success(result),
            "steps": count_react_steps(result),
            "adaptive": check_react_adaptive(result),
            "result": str(result["messages"][-1].content)
        }

    except Exception as e:
        return {
            "agent": "ReAct",
            "success": False,
            "steps": 0,
            "adaptive": "No",
            "result": "ERROR: " + str(e)
        }


def run_plan_then_execute(case_name):
    reset_state(case_name)

    try:
        result = execute_plan(REQUEST)
        success = result.get("status") == "success"

        if success:
            steps = 5
        else:
            message = result.get("message", "")

            if "Could not find flights" in message:
                steps = 1
            elif "No flight satisfies" in message:
                steps = 2
            elif "Could not book" in message:
                steps = 3
            elif "Payment failed" in message:
                steps = 4
            elif "not completed" in message:
                steps = 5
            else:
                steps = 0

        return {
            "agent": "Plan-then-Execute",
            "success": success,
            "steps": steps,
            "adaptive": "No",
            "result": str(result)
        }

    except Exception as e:
        return {
            "agent": "Plan-then-Execute",
            "success": False,
            "steps": 0,
            "adaptive": "No",
            "result": "ERROR: " + str(e)
        }


def run_hybrid(case_name):
    reset_state(case_name)

    try:
        result = execute_hybrid(REQUEST)
        success = result.get("status") == "success"

        if "tried_flights" in result:
            tried_count = len(result["tried_flights"])
            steps = 3 + 2 * tried_count
            adaptive = "Yes" if tried_count > 1 else "No"
        else:
            steps = 0
            adaptive = "No"

        return {
            "agent": "Hybrid",
            "success": success,
            "steps": steps,
            "adaptive": adaptive,
            "result": str(result)
        }

    except Exception as e:
        return {
            "agent": "Hybrid",
            "success": False,
            "steps": 0,
            "adaptive": "No",
            "result": "ERROR: " + str(e)
        }


def run_evaluation():
    cases = ["success", "fail", "booking_failure"]
    results = []

    for case_name in cases:
        print()
        print("=" * 70)
        print("CASE:", case_name.upper())
        print("=" * 70)

        print("\n[1/3] Running ReAct...")
        react_result = run_react(case_name)

        print("\n[2/3] Running Plan-then-Execute...")
        plan_result = run_plan_then_execute(case_name)

        print("\n[3/3] Running Hybrid...")
        hybrid_result = run_hybrid(case_name)

        results.append({
            "case": case_name,
            "react": react_result,
            "plan": plan_result,
            "hybrid": hybrid_result
        })

    return results


def print_comparison(results):
    print("\n")
    print("=" * 100)
    print("FINAL EVALUATION")
    print("=" * 100)

    print(
        f"{'CASE':<12}"
        f"{'AGENT':<22}"
        f"{'SUCCESS':<10}"
        f"{'STEPS':<8}"
        f"{'ADAPTIVE':<12}"
    )

    print("-" * 100)

    for case_result in results:
        for result in [
            case_result["react"],
            case_result["plan"],
            case_result["hybrid"]
        ]:
            print(
                f"{case_result['case']:<12}"
                f"{result['agent']:<22}"
                f"{str(result['success']):<10}"
                f"{result['steps']:<8}"
                f"{result['adaptive']:<12}"
            )

    print("=" * 100)


def print_final_results(results):
    print("\n")
    print("=" * 100)
    print("FINAL RESULTS")
    print("=" * 100)

    for case_result in results:
        print("\nCASE:", case_result["case"].upper())

        print("\n--- ReAct ---")
        print(case_result["react"]["result"])

        print("\n--- Plan-then-Execute ---")
        print(case_result["plan"]["result"])

        print("\n--- Hybrid ---")
        print(case_result["hybrid"]["result"])


if __name__ == "__main__":
    results = run_evaluation()
    print_comparison(results)
    print_final_results(results)
