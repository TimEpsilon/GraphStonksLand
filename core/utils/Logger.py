import logging

class Logger:
    def __init__(self, cls, instance):
        self.instance = instance
        self.logger = logging.getLogger(cls.__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(f'%(name)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def log(self, message):
        self.logger.debug(f'{getattr(self.instance, "thisNode", "UNKNOWN")} - {message}')
