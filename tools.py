from models import Flight, BookingResponse;
from datetime import date;

#region mock data
FLIGHTS = {

    "success": [

        Flight(
            flight_id="VN122",
            airline="Vietnam Airlines",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=1_850_000,
            available_seats=5
        ),

        Flight(
            flight_id="QH118",
            airline="Bamboo Airways",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="15:40",
            arrival="17:10",
            price=1_640_000,
            available_seats=5
        ),

        Flight(
            flight_id="VJ604",
            airline="VietJet Air",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=1_480_000,
            available_seats=5
        ),

        Flight(
            flight_id="VN124",
            airline="Vietnam Airlines",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="11:30",
            arrival="13:00",
            price=2_480_000,
            available_seats=5
        )

    ],

    "fail": [

        Flight(
            flight_id="VJ604",
            airline="VietJet Air",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=2_480_000,
            available_seats=5
        ),

        Flight(
            flight_id="QH118",
            airline="Bamboo Airways",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="15:40",
            arrival="17:10",
            price=1_640_000,
            available_seats=5
        ),

        Flight(
            flight_id="VN122",
            airline="Vietnam Airlines",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=2_480_000,
            available_seats=5
        )

    ],
    "booking_failure": [
        Flight(
            flight_id="VJ604",
            airline="VietJet Air",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=1_480_000,
            available_seats=5
        ),
        Flight(
            flight_id="VN122",
            airline="Vietnam Airlines",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="08:10",
            arrival="09:40",
            price=1_850_000,
            available_seats=5
        ),
        Flight(
            flight_id="QH118",
            airline="Bamboo Airways",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="15:40",
            arrival="17:10",
            price=1_640_000,
            available_seats=5
        ),
        Flight(
            flight_id="VN124",
            airline="Vietnam Airlines",
            origin="SGN",
            destination="DAD",
            date=date(2026, 10, 7),
            departure="11:30",
            arrival="13:00",
            price=2_480_000,
            available_seats=5
        )
    ]

}

#endregion

#region mock tools

CASE = "success" 
BOOKINGS = {} 
FORCED_BOOKING_FAILURES = {
    "booking_failure": ["VJ604"]
}

def search_flights(origin, destination, date):
    """Search flights by route and date."""

    result = []

    for flight in FLIGHTS[CASE]:

        if ( flight.origin == origin 
            and flight.destination == destination
            and flight.date.isoformat() == date ):
                result.append(flight)

    return {
        "status": "ok",
        "flights": result
    }


def book_seat(flight_id):
    """Hold a seat on a flight."""

    flight = None

    for f in FLIGHTS[CASE]:
        if f.flight_id == flight_id:
            flight = f
            break

    if flight is None:
        return {
            "status": "not_found",
            "flight_id": flight_id
        }
    
    if flight_id in FORCED_BOOKING_FAILURES.get(CASE, []):
        return {
        "status": "booking_failed",
        "flight_id": flight_id
    }

    if flight.available_seats <= 0:
        return {
            "status": "no_seats",
            "flight_id": flight_id
        }

    flight.available_seats = flight.available_seats - 1

    code = flight_id + "-12A"

    BOOKINGS[code] = {
        "code": code,
        "paid": False,
        "flight_id": flight.flight_id,
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "date": flight.date,
        "price": flight.price,
        "departure": flight.departure,
    }

    return {
        "status": "ok",
        "booking": BOOKINGS[code]
    }

def pay(code):
    """Pay for a booking."""

    if code not in BOOKINGS:
        return {
            "status": "not_found",
            "code": code
        }

    BOOKINGS[code]["paid"] = True

    return {
        "status": "ok",
        "booking": BOOKINGS[code]
    }


def get_booking(code):
    """Get booking information."""

    if code not in BOOKINGS:
        return {
            "status": "not_found"
        }

    return {
        "status": "ok",
        "booking": BOOKINGS[code]
    }

TOOLS = [ search_flights, book_seat, pay, get_booking ]

#endregion
LOG = []