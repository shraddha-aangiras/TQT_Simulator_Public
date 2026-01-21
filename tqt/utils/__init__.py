from datetime import datetime


def current_time():
    """

    Returns
    -------
    Current date and time in a consistent format, used for monitoring long-running measurements
    """
    return datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
