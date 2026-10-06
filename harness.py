from tools import get_booking, pay, search_flights, book_seat, TOOLS, LOG, FLIGHTS, BOOKINGS
from dataclasses import dataclass
from datetime import date
import tools

@dataclass
class Constraints:
    origin: str = "SGN"
    destination: str = "DAD"
    date: date = date(2026, 10, 7)
    depart_before: str = "12:00"      # morning flight
    max_price: int = 2_000_000        # VND

    def to_prompt(self) -> str:
        return (
            f"Book one ticket {self.origin} -> {self.destination} "
            f"on {self.date}, "
            f"departing before {self.depart_before}, "
            f"price at most {self.max_price:,} VND."
        )

    def is_ok(self, flight) -> bool:

        if flight.origin != self.origin:
            return False

        if flight.destination != self.destination:
            return False

        if flight.date != self.date:
            return False

        if flight.departure >= self.depart_before:
            return False

        if flight.price > self.max_price:
            return False

        if flight.available_seats <= 0:
            return False

        return True


CONSTRAINTS = Constraints()

def check_flight_constraint(flight_id):
    for flight in tools.FLIGHTS[tools.CASE]:
        if flight.flight_id == flight_id:
            if CONSTRAINTS.is_ok(flight):
                return {"status": "ok"}
            return {"status": "not_ok"}

    return False

def check_completion(code):

    if code is None:
        return False

    booking = get_booking(code)

    if booking["status"] != "ok":
        return False

    if booking["booking"]["paid"] == False:
        return False

    booking_data = booking["booking"]

    if booking_data["origin"] != CONSTRAINTS.origin:
        return False
    
    if booking_data["destination"] != CONSTRAINTS.destination:
        return False

    if booking_data["date"] != CONSTRAINTS.date:
        return False

    if booking_data["departure"] >= CONSTRAINTS.depart_before:
        return False

    if booking_data["price"] > CONSTRAINTS.max_price:
        return False

    return True

PERMISSIONS = {
    "search_flights": True,
    "book_seat": True,
    "pay": True,
    "get_booking": True
}

def check_permission(action):

    if action not in PERMISSIONS:
        return False

    return PERMISSIONS[action]

def handoff(reason):

    return {
        "status": "handoff",
        "reason": reason
    }

def make_payment(code):

    if check_permission("pay") == False:
        return handoff("Agent does not have permission to pay.")

    result = pay(code)

    LOG.append({
        "action": "pay",
        "code": code,
        "result": result
    })

    return result

@dataclass
class LoopDetector:
    last_action:str = None
    repeat_count:int = 0

    def check(self, action):

        if action == self.last_action:
            self.repeat_count += 1
        else:
            self.last_action = action
            self.repeat_count = 1

        if self.repeat_count >= 2:
            return True

        return False

@dataclass
class BudgetTracker:
    max_steps: int = 10
    steps: int = 0

    def count(self):
        self.steps += 1

    def exceeded(self):

        if self.steps >= self.max_steps:
            return True

        return False

