"""
Kiwi.com Tequila API service
"""
import httpx
from typing import Optional
from datetime import datetime, timedelta
from app.core.config import settings


class KiwiService:
    """Service for interacting with Kiwi.com Tequila API"""
    
    def __init__(self):
        self.api_key = settings.KIWI_API_KEY
        self.base_url = settings.KIWI_API_BASE
        self.headers = {"apikey": self.api_key} if self.api_key else {}
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Optional[datetime] = None,
        return_date: Optional[datetime] = None,
        adults: int = 1,
        currency: str = "USD",
        limit: int = 10,
    ) -> dict:
        """
        Search for flights using Kiwi Tequila API
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (defaults to tomorrow if not provided)
            return_date: Return date for round trips
            adults: Number of adult passengers
            currency: Currency code
            limit: Maximum number of results
            
        Returns:
            dict: API response with flight data
        """
        # Default dates
        if not departure_date:
            departure_date = datetime.utcnow() + timedelta(days=1)
        
        params = {
            "fly_from": origin,
            "fly_to": destination,
            "date_from": departure_date.strftime("%d/%m/%Y"),
            "date_to": departure_date.strftime("%d/%m/%Y"),
            "adults": adults,
            "curr": currency,
            "limit": limit,
            "sort": "price",
        }
        
        # Add return date for round trips
        if return_date:
            params["return_from"] = return_date.strftime("%d/%m/%Y")
            params["return_to"] = return_date.strftime("%d/%m/%Y")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v2/search",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                # Return empty data on error
                return {"data": [], "error": str(e)}
    
    async def get_airport_info(self, iata_code: str) -> dict:
        """Get airport information by IATA code"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/locations",
                    headers=self.headers,
                    params={"term": iata_code, "location_types": "airport"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                if data.get("locations"):
                    return data["locations"][0]
                return {}
            except httpx.HTTPError:
                return {}
    
    async def get_cheapest_destinations(
        self,
        origin: str,
        max_price: Optional[float] = None,
        currency: str = "USD",
    ) -> list:
        """Get cheapest destinations from an origin airport"""
        params = {
            "term": origin,
            "curr": currency,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v2/flights/radial",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                
                flights = data.get("data", [])
                if max_price:
                    flights = [f for f in flights if f.get("price", 0) <= max_price]
                
                return flights
            except httpx.HTTPError:
                return []
