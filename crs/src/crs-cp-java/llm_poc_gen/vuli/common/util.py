from vuli.common.decorators import consume_exc
import os


def field_validation(target: dict, fields: set[str], exception=True) -> bool:
    non_exist_fields = list(filter(lambda x: not x in target, fields))
    if len(non_exist_fields) == 0:
        return True
    if exception:
        nl = "\n"
        raise RuntimeError(f"Field Not Exist:{nl}{nl.join(non_exist_fields)}")
    return False


def path_validation(paths: list[str], exception=True) -> bool:
    non_exist_paths = list(filter(lambda x: not os.path.exists(x), paths))
    if len(non_exist_paths) == 0:
        return True
    if exception:
        nl = "\n"
        raise RuntimeError(f"Path Not Exist:{nl}{nl.join(non_exist_paths)}")
    return False


@consume_exc(default=0)
def get_sort_key_from_id(id: str) -> int:
    return int(id.split("_")[1])
