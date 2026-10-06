from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass 
class Flight:
    flight_id: str
    airline: str
    origin: str
    destination: str
    date: date
    departure: str
    arrival: str
    price: int
    available_seats: int

@dataclass
class BookingRequest:
    origin: str
    destination: str
    date: date
    passenger_name: str
    budget: Optional[int] = None

@dataclass
class BookingResponse:
    success: bool
    message: str    
    booking_id: Optional[str] = None
    flight_id: Optional[str] = None