import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import (
    search_flights,
    book_seat
)

from harness import (
    check_flight_constraint,
    check_completion,
    make_payment,
    handoff,
    BudgetTracker
)

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "Thiếu API key Gemini. Hãy tạo file .env với GOOGLE_API_KEY=..."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=api_key,
)

def create_plan(user_request):
    """
    Ask the LLM to create a fixed execution plan.
    """

    prompt = f""" You are a flight booking planner.
                Create a simple step-by-step plan for this request:
                {user_request}

            The plan must follow this order:

            1. Search for available flights.
            2. Select the cheapest flight that satisfies all constraints.
            3. Book the selected flight.
            4. Pay for the booking.
            5. Verify that the booking is completed.

            Return only the numbered plan.
            """

    response = llm.invoke(prompt)

    return response.content


def execute_plan(user_request):
    """
    Execute the flight booking plan.
    """

    budget_tracker = BudgetTracker()
    plan = create_plan(user_request)

    print("\n===== PLAN =====\n")
    print(plan)

    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    flights_result = search_flights(
        "SGN",
        "DAD",
        "2026-10-07"
    )

    if flights_result["status"] != "ok":
        return {
            "status": "failed",
            "message": "Could not find flights."
        }

    flights = flights_result["flights"]

    budget_tracker.count()

    valid_flights = []

    for flight in flights:
        constraint_result = check_flight_constraint(
            flight.flight_id
        )

        if constraint_result["status"] == "ok":
            valid_flights.append(flight)

    if len(valid_flights) == 0:
        return {
            "status": "failed",
            "message": "No flight satisfies all constraints."
        }

    selected_flight = min(
        valid_flights,
        key=lambda flight: flight.price
    )

    print("\n===== SELECTED FLIGHT =====\n")
    print(selected_flight)

    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    booking_result = book_seat(
        selected_flight.flight_id
    )

    if booking_result["status"] != "ok":
        return {
            "status": "failed",
            "message": "Could not book the flight."
        }

    booking = booking_result["booking"]
    booking_code = booking["code"]

    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    payment_result = make_payment(booking_code)

    if payment_result["status"] != "ok":
        return {
            "status": "failed",
            "message": "Payment failed."
        }

    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    completed = check_completion(booking_code)

    if not completed:
        return {
            "status": "failed",
            "message": "Booking is not completed."
        }

    return {
        "status": "success",
        "message": "Booking completed successfully.",
        "booking": booking
    }


if __name__ == "__main__":

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