import psutil

class Resource:
    __memory: int = 12
    __memory_interval: int = 12
    __memory_max: int = 50

    __timeout: int = 90
    __timeout_interval: int = 60
    __timeout_max: int = 300

    __calldepth: int = 4
    __calldepth_interval: int = 2
    __calldepth_max: int = 12

    def __init__(self):
        memory_max = int(psutil.virtual_memory().total / (1024 ** 3) * 0.9)
        if memory_max > 50:
            memory_max = 50
        self.__memory_max = memory_max

        if self.__memory > self.__memory_max:
            self.__memory = self.__memory_max

    def get_memory(self) -> int:
        return self.__memory

    def get_timeout(self) -> int:
        return self.__timeout

    def get_calldepth(self) -> int:
        return self.__calldepth

    def increase(self) -> bool:
        memory = self.__memory + self.__memory_interval
        if memory > self.__memory_max:
            memory = self.__memory_max

        timeout = self.__timeout + self.__timeout_interval
        if timeout > self.__timeout_max:
            timeout = self.__timeout_max

        calldepth = self.__calldepth + self.__calldepth_interval
        if calldepth > self.__calldepth_max:
            calldepth = self.__calldepth_max

        isUpdated: bool = (
            memory != self.__memory or
            timeout != self.__timeout or
            calldepth != self.__calldepth
        )

        self.__memory = memory
        self.__timeout = timeout
        self.__calldepth = calldepth

        return isUpdated
        




