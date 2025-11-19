import logging

class ListHandler(logging.Handler):
    """
    A logging handler that appends log records to a list.
    This allows retrieving logs programmatically after execution.
    """
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_list.append(msg)
        except Exception:
            self.handleError(record)

