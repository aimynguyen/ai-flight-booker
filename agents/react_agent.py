import code
import os
from unittest import result
from dotenv import load_dotenv
from langchain.tools import tool
from tools import get_booking, pay, search_flights, book_seat
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from harness import BudgetTracker, LoopDetector, check_completion, check_permission,handoff,make_payment,check_flight_constraint


load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Thiếu API key Gemini. Hãy tạo file .env với GOOGLE_API_KEY=...")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=api_key,
)

budget_tracker = BudgetTracker()
loop_detector = LoopDetector()


@tool
def search_flights_tool(origin: str, destination: str, date: str):
    """Search for flights from origin to destination on a given date."""
    budget_tracker.count()

    if budget_tracker.exceeded(): 
        return handoff("Step budget exceeded.") 
    if not check_permission("search_flights"): 
        return handoff("Agent cannot search flights.") 
    if loop_detector.check("search_flights"): 
        return handoff("Agent detected a loop.") 
    return search_flights(origin, destination, date)

@tool
def book_seat_tool(flight_id: str):
    """Book a seat on a flight."""
    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    if not check_permission("book_seat"):
        return handoff("Agent cannot book a seat.")

    if loop_detector.check("book_seat"):
        return handoff("Agent detected a loop.")

    constraint_result = check_flight_constraint(flight_id)
    if constraint_result["status"] != "ok":
        return handoff(f"Flight {flight_id} does not satisfy the booking constraints.")

    return book_seat(flight_id)

@tool
def pay_tool(code: str):
    """Pay for a booking."""
    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    if loop_detector.check("pay"):
        return handoff("Agent detected a loop.")

    return make_payment(code)

@tool
def get_booking_tool(code: str):    
    """Get booking information."""
    budget_tracker.count()

    if budget_tracker.exceeded():
        return handoff("Step budget exceeded.")

    if not check_permission("get_booking"):
        return handoff("Agent cannot get booking information.")

    if loop_detector.check("get_booking"):
        return handoff("Agent detected a loop.")

    completed = check_completion(code) 
    result["completed"] = completed 
    
    if completed: 
        result["message"] = "Booking completed successfully." 
    else: 
        result["message"] = "Booking is not completed." 
    return result


TOOLS = [
    search_flights_tool,
    book_seat_tool,
    pay_tool,
    get_booking_tool
]

agent = create_agent(llm, tools=TOOLS)

