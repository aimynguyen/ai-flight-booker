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
    Ask the LLM to create an initial plan.
    """

    prompt = f"""
                You are a flight booking planner.

                Create a simple plan for this request:

                {user_request}

                The plan should contain:

                1. Search flights.
                2. Select the cheapest valid flight.
                3. Book the flight.
                4. Pay for the booking.
                5. Verify the booking.

                If a step fails, the agent should be able to adapt
                and try another valid flight.

                Return only the numbered plan.
                """

    response = llm.invoke(prompt)

    return response.content

def find_cheapest_valid_flight(flights, tried_flights):
    """
    Find the cheapest valid flight that has not been tried yet.
    """

    valid_flights = []

    for flight in flights:

        if flight.flight_id in tried_flights:
            continue

        constraint_result = check_flight_constraint(
            flight.flight_id
        )

        if constraint_result["status"] == "ok":
            valid_flights.append(flight)

    if len(valid_flights) == 0:
        return None

    return min(
        valid_flights,
        key=lambda flight: flight.price
    )

def execute_hybrid(user_request):

    budget_tracker = BudgetTracker()


    plan = create_plan(user_request)

    print("\n===== INITIAL PLAN =====\n")
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

    tried_flights = []

    while True:

        budget_tracker.count()

        if budget_tracker.exceeded():
            return handoff("Step budget exceeded.")

        selected_flight = find_cheapest_valid_flight(
            flights,
            tried_flights
        )

        if selected_flight is None:
            return {
                "status": "failed",
                "message": "No more valid flights are available."
            }

        print("\n===== TRYING FLIGHT =====\n")
        print(selected_flight)

        tried_flights.append(
            selected_flight.flight_id
        )

        budget_tracker.count()

        if budget_tracker.exceeded():
            return handoff("Step budget exceeded.")

        booking_result = book_seat(
            selected_flight.flight_id
        )

        if booking_result["status"] != "ok":

            print("\n===== BOOKING FAILED =====\n")
            print(
                f"Flight {selected_flight.flight_id} "
                "could not be booked."
            )

            print("\n===== ADAPTING PLAN =====\n")
            print("Searching for another valid flight...")

            continue

        booking = booking_result["booking"]
        booking_code = booking["code"]

        print("\n===== BOOKING SUCCESS =====\n")
        print(booking)

        budget_tracker.count()

        if budget_tracker.exceeded():
            return handoff("Step budget exceeded.")

        payment_result = make_payment(
            booking_code
        )

        if payment_result["status"] != "ok":
            return {
                "status": "failed",
                "message": "Payment failed."
            }
        
        budget_tracker.count()

        if budget_tracker.exceeded():
            return handoff("Step budget exceeded.")

        completed = check_completion(
            booking_code
        )

        if completed:

            return {
                "status": "success",
                "message": "Booking completed successfully.",
                "booking": booking,
                "tried_flights": tried_flights
            }

        return {
            "status": "failed",
            "message": "Booking was created but completion check failed.",
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

    result = execute_hybrid(request)

    print("\n===== FINAL RESULT =====\n")
    print(result)