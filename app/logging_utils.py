import logging, sys

def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt="time=%(asctime)s level=%(levelname)s msg=%(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    return root
