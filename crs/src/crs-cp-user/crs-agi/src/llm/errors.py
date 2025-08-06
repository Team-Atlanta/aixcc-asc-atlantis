# A list of exceptions in the plugin calls
class PluginErrorGivingUp(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class PluginErrorRetry(Exception):
    def __init__(self, reason, summary):
        super().__init__(f"reason: {reason}\nsummary:{summary}")
        self.reason = reason
        self.summary = summary


class PluginSuccess(Exception):
    def __init__(self, summary):
        super().__init__(summary)
        self.summary = summary


class PluginErrorTimeout(Exception):
    pass


class PluginErrorTokenLimit(Exception):
    pass


