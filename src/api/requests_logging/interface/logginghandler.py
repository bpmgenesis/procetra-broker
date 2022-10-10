import logging

class LoggingHandler(object):
    def __init__(self):
        pass

    def debug(self, msg):
        """
        Logs a debug message
        Parameters
        -----------
        msg
            Message
        """
        raise Exception("LoggingHandler debug not implemented")

    def info(self, msg):
        """
        Logs an info message
        Parameters
        ------------
        msg
            Message
        """
        raise Exception("LoggingHandler info not implemented")

    def warning(self, msg):
        """
        Logs a warning message
        Parameters
        ------------
        msg
            Message
        """
        raise Exception("LoggingHandler warning not implemented")

    def error(self, msg):
        """
        Logs an error message
        Parameters
        ------------
        msg
            Message
        """
        raise Exception("LoggingHandler error not implemented")