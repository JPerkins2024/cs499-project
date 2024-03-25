#! /usr/bin/env python
"""
Created on Mon Jun 26 08:06:59 CDT 2023
Forked from IFXLogger package created by Luis Poeller

@author: wellsjeremy
"""
import time
import sys
from termcolor import colored


class Singleton(type):
    """Singleton pattern."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Return same instance."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Logger(metaclass=Singleton):
    """Logger class to have uniform console output."""

    def __init__(self, logFile: str = None, logLevel: str = "INFO", timeOutput=True, printSummary=True):
        """
        Parameters
        ----------
        logFile : str, optional
            output file. The default is None.
        logLevel : str, optional
            Minimum level for output. The default is "INFO".
        timeOutput : TYPE, optional
            Output of elapsed time. The default is True.
        printSummary : TYPE, optional
            Output of message summary after finish. The default is True.
        """
        if logFile is not None:
            self.__logFile = open(logFile, "w")
        else:
            self.__logFile = None
        self.__logLevel = logLevel.upper()
        self.__timeOutput = timeOutput
        self.__doPrintSummary = printSummary
        self.__startTime = time.time()
        self.__context = None

        self.__summary = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "FATAL": 0}

    def __del__(self):
        """Print log summary when exiting."""
        self.clearContext()
        if self.__doPrintSummary:
            self.__printSummary()
        if self.__logFile is not None:
            self.__logFile.close()

    def setLogLevel(self, logLevel: str):
        """Change logging level."""
        if logLevel.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"]:
            self.__logLevel = logLevel.upper()
        else:
            self.warning(f"Unknown logLevel '{logLevel}' specified")

    def setContext(self,context: str):
        self.__context = context

    def clearContext(self):
        self.__context = None



    def debug(self, message: str, force: bool = False, color: str = None, bold: bool = False, underline: bool = False,
              start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'debug'.

        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is None.
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is False.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.__log(message, level="DEBUG", force=force, color=color, bold=bold, underline=underline, start=start, end=end)

    def info(self, message: str, force: bool = False, color: str = None, bold: bool = False, underline: bool = False,
             start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'info'.

        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is None.
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is False.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.__log(message, level="INFO", force=force, color=color, bold=bold, underline=underline, start=start, end=end)

    def warning(self, message: str, force: bool = False, color: str = 'yellow', bold: bool = False, underline: bool = False,
                start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'warning'.

        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is "yellow".
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is False.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.__log(message, level="WARNING", force=force, color=color, bold=bold, underline=underline, start=start, end=end)

    def warning_once(self, message: str, force: bool = False, color: str = 'yellow', bold: bool = False, underline: bool = False,
                start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'warning'.


        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is "yellow".
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is False.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.warning_cache = getattr(self,"warning_cache",False) or dict()
        if self.warning_cache.get(message):
            return
        self.__log(message, level="WARNING", force=force, color=color, bold=bold, underline=underline, start=start, end=end)
        self.warning_cache[message] = True

    def error(self, message: str, force: bool = False, color: str = 'red', bold: bool = False, underline: bool = False,
              start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'error'.

        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is "red".
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is True.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.__log(message, level="ERROR", force=force, color=color, bold=bold, underline=underline, start=start, end=end)

    def fatal(self, message: str, force: bool = False, color: str = 'red', bold: bool = True, underline: bool = False,
              start: str = "", end: str = "\n\r"):
        """
        Print message with logLevel 'fatal'. Aborts program afterwards.

        Parameters
        ----------
        message : str
            message to be printed.
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is "red".
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is True.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        self.__log(message, level="FATAL", force=force, color=color, bold=bold, underline=underline, start=start, end=end)
        sys.exit(1)

    def __log(self, message: str, level: str, force: bool = False, color: str = None, bold: bool = False,
              underline: bool = False, start: str = "", end: str = "\n\r"):
        """
        Print message with given logLevel.

        Parameters
        ----------
        message : str
            message to be printed.
        level : str
            logLevel
        force : bool, optional
            if true, will always be printed, independent of the global logLevel setting. The default is False.
        color : str, optional
            message will be printed in given color. The default is None.
            Possible colors are: grey, red, green, yellow, blue, magenta, cyan, white
        bold : bool, optional
            prints message in bold. The default is False.
        underline : bool, optional
            prints message underlined. The default is False.
        start : str, optional
            will be put before the whole message.
        end : str, optional
            will be put after the whole message.
        """
        level = level.upper()
        levelTable = {"DEBUG": 1, "INFO": 2, "WARNING": 3, "ERROR": 4, "FATAL": 5}
        levelFmt = "{:<10}".format(f"[{level}]")
        if self.__timeOutput:
            timeFmt = " [%s]" % time.strftime("%H:%M:%S", time.gmtime(time.time()))
            timeFmtRel = " [%s]" % time.strftime("%H:%M:%S", time.gmtime(time.time() - self.__startTime))
        else:
            timeFmt = ""
            timeFmtRel = ""
        if self.__context:
            context = f"{self.__context}"
        else:
            context = ""
        message = str(message)
        if "\n" in message:
            message = message.split("\n")
            for m in message:
                self.__log(m, level=level, force=force, color=color)
            return

        attrs = []
        if bold:
            attrs.append("bold")
        if underline:
            attrs.append("underline")
        if color:
            available_colors = ["grey", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
            if color not in available_colors:
                self.warning(f"Specified color '{color}' of following message not available, possible colors are: "
                             f"{available_colors}")
                color = None
        context_color="blue"
        contextStr=""
        coloredContextStr=""
        if context:
            contextStr=f"[ {context} ]"
            coloredContextStr = f"[ {colored(context,context_color)} ]"


        messageStr = f"{levelFmt}{timeFmtRel} {coloredContextStr} " + colored(message, color, attrs=attrs)
        messageLog = f"{levelFmt}{timeFmt} {contextStr} {message}"
        if self.__logFile is not None:
            self.__logFile.write(f"{messageLog}\n")
        if levelTable[level] >= levelTable[self.__logLevel] or force is True:
            sys.stdout.write(f"{start}{messageStr}{end}")
            if force is False:
                self.__summary[level] += 1

    def __printSummary(self):
        """Print log summary with number of printed messages per level."""
        self.__log("----- message summary -----", level="INFO", force=True)
        for level in self.__summary:
            levelFmt = "{:<10}".format(f"[{level}]")
            self.__log(f"      {levelFmt} : {self.__summary[level]}", level="INFO", force=True)
        sys.stdout.write("\n\r")
