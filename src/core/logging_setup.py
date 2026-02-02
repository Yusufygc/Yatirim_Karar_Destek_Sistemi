import logging
import sys

def setup_logging():
    """
    Configures the logging for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # You can add FileHandler here if needed
        ]
    )
    logger = logging.getLogger("YatirimApp")
    return logger

logger = setup_logging()
