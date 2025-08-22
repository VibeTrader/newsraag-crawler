from datetime import datetime, timezone
import pytz
from loguru import logger

# Define the PST timezone identifier for pytz
PST_TIMEZONE_IDENTIFIER = "America/Los_Angeles"

try:
    PST = pytz.timezone(PST_TIMEZONE_IDENTIFIER)
except pytz.exceptions.UnknownTimeZoneError:
    logger.error(f"Could not load timezone info for {PST_TIMEZONE_IDENTIFIER} using pytz.")
    PST = None
except Exception as e:
    logger.error(f"Unexpected error loading timezone {PST_TIMEZONE_IDENTIFIER} with pytz: {e}")
    PST = None

def convert_to_pst(dt: datetime) -> datetime | None:
    """Converts a timezone-aware datetime object to PST using pytz.

    Args:
        dt: A timezone-aware datetime object.

    Returns:
        A new datetime object representing the same time in PST,
        or None if conversion fails (e.g., PST not loaded or input is naive).
    """
    if PST is None:
        logger.error("PST timezone info (pytz) not loaded. Cannot convert.")
        return None
    if dt.tzinfo is None:
        logger.warning("Input datetime is naive (no timezone info). Cannot convert reliably.")
        # You might want to assume UTC if appropriate for your source data
        # dt = dt.replace(tzinfo=pytz.utc) 
        return None
    try:
        # If already aware, convert directly
        return dt.astimezone(PST)
    except Exception as e:
        logger.error(f"Error converting datetime {dt} to PST using pytz: {e}")
        return None

def get_current_pst_time() -> datetime | None:
    """Gets the current time in PST using pytz.
    
    Returns:
        A timezone-aware datetime object representing the current time in PST,
        or None if PST timezone info isn't loaded.
    """
    if PST is None:
        logger.error("PST timezone info (pytz) not loaded. Cannot get current PST time.")
        return None
    try:
        # Get current UTC time and convert to PST
        utc_now = datetime.now(pytz.utc)
        return utc_now.astimezone(PST)
    except Exception as e:
        logger.error(f"Error getting current PST time using pytz: {e}")
        return None 