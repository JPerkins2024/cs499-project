import re
class LogParser:
    def __init__(self, logfile, simulator):
        self.errors = []
        self.error_match = self.get_error_regexp(simulator)
        self.logfile = logfile
        self.parse_errors()
    
    def parse_errors(self):
        try:
            file = open(self.logfile,'r')
            log_arr = file.readlines()
        except:
            self.errors.append("ERROR: Unable to load {logfile}. There was a problem with this corner.".format(logfile = self.logfile))
            return
        while len(log_arr) > 0:
            line = log_arr.pop()
            line.strip()
            if re.search(self.error_match,line):
                while(re.match(r'^\+',log_arr[0])):
                    line = line + "\n" + log_arr.pop()
                self.errors.append(line)

    def get_error_regexp(self, simulator):
        if simulator == 'eldo':
            return r'^ERROR'
        if simulator == 'afs':
            return r'SIM_ERROR'
        if simulator == 'spectre':
            return r'^\s*\bERROR|FATAL\b'
        if simulator == 'finesim':
            return r'^ERROR!'
        if simulator == 'hspice':
            return r'\*\*error\*\*'
        return r'\bERROR\b'
