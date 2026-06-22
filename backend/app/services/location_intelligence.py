"""
NeoFace Trust Engine — Location Intelligence Service (Module 4)

Computes location-based risk signals without allowing location to dominate.

Features:
  - Known location detection (low risk)
  - New city detection (moderate risk)
  - New country detection (elevated risk)
  - Impossible travel detection (high risk)
  - VPN/Proxy detection (slight increase)
  - Location never auto-rejects authentication

Philosophy:
  Location is a SUPPORTING SIGNAL only.
  Maximum contribution: LOCATION_WEIGHT = 0.05
  Biometric signals (face, liveness) are primary decision factors.

Design for global, mobile-first authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.core.logging import logger


@dataclass
class GeoLocation:
    """Geolocation data from IP/device."""
    
    city: str | None
    country_code: str  # ISO 3166-1 alpha-2 (e.g., 'IN', 'US', 'DE')
    latitude: float | None
    longitude: float | None
    ip_address: str | None
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    timezone: str | None = None
    timestamp: datetime | None = None


@dataclass
class LocationHistory:
    """User's recent authentication locations."""
    
    known_countries: set[str]  # Countries where user has authenticated
    known_cities: set[str]     # Cities where user has authenticated
    last_login_location: GeoLocation | None
    last_login_time: datetime | None


@dataclass
class LocationRiskResult:
    """Output from location risk calculation."""
    
    location_risk: float       # 0.0–1.0 (overall location risk)
    travel_risk: float        # 0.0–1.0 (impossible travel, anomalies)
    vpn_risk: float           # 0.0–1.0 (VPN/proxy detected)
    location_classification: str  # known | new_city | new_country | none
    final_location_risk: float # Weighted composite, never > 0.05 contribution
    flags: list[str]          # Human-readable risk indicators


class LocationIntelligenceService:
    """
    Compute location-based authentication risk.
    
    Stateless service — all location history is passed as input.
    """

    # Distance-based thresholds (in km)
    IMPOSSIBLE_TRAVEL_MIN_DISTANCE = 500.0  # km
    IMPOSSIBLE_TRAVEL_TIME_HOURS = 2.0      # hours to travel minimum distance

    # Risk scoring
    KNOWN_LOCATION_RISK = 0.0
    NEW_CITY_RISK = 0.2
    NEW_COUNTRY_RISK = 0.5
    IMPOSSIBLE_TRAVEL_RISK = 0.9
    VPN_RISK = 0.15
    TOR_RISK = 0.5

    # Maximum contribution to final trust score (5%)
    LOCATION_WEIGHT = 0.05

    @staticmethod
    def calculate_location_risk(
        current_location: GeoLocation,
        history: LocationHistory,
    ) -> LocationRiskResult:
        """
        Evaluate location-based risk.
        
        Args:
            current_location: Current authentication location.
            history: User's historical locations.
            
        Returns:
            LocationRiskResult with location_risk, travel_risk, vpn_risk.
        """
        flags: list[str] = []
        
        # ── 1. VPN/Proxy Detection ───────────────────────────────────────────
        vpn_risk = LocationIntelligenceService._calculate_vpn_risk(
            current_location, flags
        )
        
        # ── 2. Location Classification ───────────────────────────────────────
        location_risk, classification = LocationIntelligenceService._classify_location(
            current_location, history, flags
        )
        
        # ── 3. Impossible Travel Detection ──────────────────────────────────
        travel_risk = LocationIntelligenceService._calculate_travel_risk(
            current_location, history, flags
        )
        
        # ── Composite (capped at LOCATION_WEIGHT) ──────────────────────────
        # Weights: location_risk (60%) + travel_risk (30%) + vpn_risk (10%)
        final_location_risk = (
            0.60 * location_risk +
            0.30 * travel_risk +
            0.10 * vpn_risk
        )
        final_location_risk = min(final_location_risk, 1.0)

        logger.debug(
            "location_intelligence.risk",
            location_risk=round(location_risk, 3),
            travel_risk=round(travel_risk, 3),
            vpn_risk=round(vpn_risk, 3),
            classification=classification,
            final_location_risk=round(final_location_risk, 3),
            flags=flags[:5],
        )

        return LocationRiskResult(
            location_risk=location_risk,
            travel_risk=travel_risk,
            vpn_risk=vpn_risk,
            location_classification=classification,
            final_location_risk=final_location_risk,
            flags=flags,
        )

    @staticmethod
    def _classify_location(
        current_location: GeoLocation,
        history: LocationHistory,
        flags: list[str],
    ) -> tuple[float, str]:
        """
        Classify current location relative to user's history.
        
        Returns:
            (risk_score, classification_string)
        """
        if not current_location.country_code:
            return 0.5, "unknown_location"

        # Known location (same city)
        if (current_location.city and
            current_location.city in history.known_cities):
            flags.append(f"known_city:{current_location.city}")
            return LocationIntelligenceService.KNOWN_LOCATION_RISK, "known"

        # New city but known country
        if current_location.country_code in history.known_countries:
            flags.append(f"new_city_known_country:{current_location.city},{current_location.country_code}")
            return LocationIntelligenceService.NEW_CITY_RISK, "new_city"

        # First login in country
        flags.append(f"new_country:{current_location.country_code}")
        return LocationIntelligenceService.NEW_COUNTRY_RISK, "new_country"

    @staticmethod
    def _calculate_travel_risk(
        current_location: GeoLocation,
        history: LocationHistory,
        flags: list[str],
    ) -> float:
        """
        Detect impossible travel (too far in too little time).
        
        Example: Delhi to Germany in 15 minutes.
        """
        if (history.last_login_location is None or
            history.last_login_time is None):
            # No previous location to compare
            return 0.0

        last_loc = history.last_login_location
        
        # Can't calculate without coordinates
        if (current_location.latitude is None or
            current_location.longitude is None or
            last_loc.latitude is None or
            last_loc.longitude is None):
            return 0.0

        # ── Calculate distance (Haversine formula) ────────────────────────────
        distance_km = LocationIntelligenceService._haversine_distance(
            last_loc.latitude,
            last_loc.longitude,
            current_location.latitude,
            current_location.longitude,
        )

        # ── Calculate time elapsed ────────────────────────────────────────────
        if current_location.timestamp and history.last_login_time:
            time_diff = current_location.timestamp - history.last_login_time
            hours_elapsed = time_diff.total_seconds() / 3600.0
        else:
            return 0.0  # Can't determine time

        # ── Check for impossible travel ──────────────────────────────────────
        if distance_km < LocationIntelligenceService.IMPOSSIBLE_TRAVEL_MIN_DISTANCE:
            # Not far enough to be impossible
            return 0.0

        # Minimum plausible travel speed (km/h)
        avg_speed = distance_km / max(hours_elapsed, 0.01)
        max_plausible_speed = 1000.0  # Commercial flight ~ 900 km/h

        if avg_speed > max_plausible_speed:
            # Impossible travel detected
            flags.append(
                f"impossible_travel:{distance_km:.0f}km_in_{hours_elapsed:.1f}h"
            )
            logger.warning(
                "location_intelligence.impossible_travel",
                distance_km=round(distance_km, 1),
                hours_elapsed=round(hours_elapsed, 2),
                avg_speed=round(avg_speed, 1),
            )
            return LocationIntelligenceService.IMPOSSIBLE_TRAVEL_RISK

        return 0.0

    @staticmethod
    def _calculate_vpn_risk(
        current_location: GeoLocation,
        flags: list[str],
    ) -> float:
        """Detect VPN/Proxy/Tor usage."""
        if current_location.is_tor:
            flags.append("tor_detected")
            logger.info("location_intelligence.tor_detected")
            return LocationIntelligenceService.TOR_RISK

        if current_location.is_vpn or current_location.is_proxy:
            service = "vpn" if current_location.is_vpn else "proxy"
            flags.append(f"{service}_detected")
            logger.debug(f"location_intelligence.{service}_detected")
            return LocationIntelligenceService.VPN_RISK

        return 0.0

    @staticmethod
    def _haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate great-circle distance between two coordinates (km).
        
        Args:
            lat1, lon1: Starting latitude/longitude (degrees)
            lat2, lon2: Ending latitude/longitude (degrees)
            
        Returns:
            Distance in kilometers
        """
        import math
        
        R = 6371.0  # Earth radius in km
        
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = (
            math.sin(dlat / 2.0) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.asin(math.sqrt(a))
        
        return R * c

    @staticmethod
    def add_to_history(
        history: LocationHistory,
        location: GeoLocation,
        successful_auth: bool = True,
    ) -> LocationHistory:
        """
        Update location history after an authentication event.
        
        Args:
            history: Current location history.
            location: Current authentication location.
            successful_auth: Whether authentication succeeded (default True).
            
        Returns:
            Updated LocationHistory (new object, history is unchanged).
        """
        if not successful_auth or not location.country_code:
            # Don't add failed authentication locations
            return history

        updated_known_countries = set(history.known_countries)
        updated_known_cities = set(history.known_cities)

        updated_known_countries.add(location.country_code)
        if location.city:
            updated_known_cities.add(location.city)

        return LocationHistory(
            known_countries=updated_known_countries,
            known_cities=updated_known_cities,
            last_login_location=location,
            last_login_time=location.timestamp or datetime.utcnow(),
        )
