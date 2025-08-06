from vuli.common.decorators import consume_exc_method
from vuli.common.singleton import Singleton


class Vuln(metaclass=Singleton):
    class InnerData:
        def __init__(self, sink: str):
            self.sink: str = sink
            self.sentinels: set[str] = set()

    __table: dict[str, InnerData] = {
        "OSCommandInjection": InnerData("command_injection"),
        "Deserialization": InnerData("deserialization"),
        "ExpressionLanguageInjection": InnerData("el_injection"),
        "LdapInjection": InnerData("ldap_injection"),
        "NamingContextLookup": InnerData("naming_context_look_up"),
        "ReflectiveCall": InnerData("reflective_call"),
        "RegexInjection": InnerData("regex_injection"),
        "ScriptEngineInjection": InnerData("script_injection"),
        "SqlInjection": InnerData("sql_injection"),
        "ServerSideRequestForgery": InnerData("ssrf"),
        "XPathInjection": InnerData("xpath_injection"),
        "ArbitraryFileReadWrite": InnerData("arbitrary_file_read_write"),
    }

    @consume_exc_method(default=False)
    def add_sentinel(self, vulnerability: str, sentinel: str) -> bool:
        self.__table[vulnerability].sentinels.add(sentinel)
        return True

    @consume_exc_method(default=None)
    def clean_sentinels(self):
        for value in self.__table.values():
            value.sentinels.clear()

    @consume_exc_method(default=[])
    def get_sentinels(self, vulnerability: str) -> list[any]:
        return list(self.__table[vulnerability].sentinels)

    @consume_exc_method(default=[])
    def get_vulns(self) -> list[str]:
        result: list[str] = list(self.__table.keys())
        return sorted(result)

    @consume_exc_method(default="")
    def get_sink(self, key: str) -> str:
        return self.__table[key].sink
