import re

from loop.commons.context.models import RequiresContext
from loop.framework.action.models import Action
from loop.framework.effect.variants import (
    CompilableEffect,
    DumbEffect,
    EmptyEffect,
    SoundEffect,
    UnknownErrorEffect,
    VulnerableEffect,
    WrongFormatEffect,
    WrongPatchEffect,
)
from loop.framework.picker.protocols import PickerProtocol
from loop.framework.seed.models import Seed
from loop.framework.seed.variants import ErrorSeed, InitialSeed, PlainSeed
from loop.framework.wire.context import WireContext


class RediaPicker(PickerProtocol):

    def of_dumb(
        self, action: Action, effect: DumbEffect
    ) -> RequiresContext[Seed, WireContext]:
        # TODO: parse the error message from the effect
        # stderr = effect.stderr

        return RequiresContext(
            lambda _: ErrorSeed(message="Your previous code is not compilable.")
        )

    def of_compilable(
        self, action: Action, effect: CompilableEffect
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(
            lambda _: ErrorSeed(message="Your previous code is not functional.")
        )

    def of_sound(
        self, action: Action, effect: SoundEffect
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(
            lambda _: PlainSeed("Is there any other way to fix the bug?")
        )  # TODO

    def of_vulnerable(
        self, action: Action, effect: VulnerableEffect
    ) -> RequiresContext[Seed, WireContext]:
        def _(context: WireContext):
            bugs = re.findall(r"\] (BUG: .*)", effect.run_pov_stdout)
            return ErrorSeed(
                message="Your previous code is vulnerable:\n" + "\n".join(bugs)
            )

        return RequiresContext(_)

    def of_wrong_format(
        self, action: Action, effect: WrongFormatEffect
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(
            lambda _: ErrorSeed(
                message="""Every *SEARCH/REPLACE block* must use this format:
1. The file path alone on a line, eg: FILE: main.py
2. The opening fence and code language, eg: ```python
3. !!!! CRITICAL !!! The start of search block: <<<<<<< SEARCH
4. A contiguous chunk of lines to search for in the existing source code
5. The dividing line: =======
6. The lines to replace into the source code
7. The end of the replace block: >>>>>>> REPLACE
8. The closing fence: ```

Use this format for each SEARCH/REPLACE block:
file: [file_path]
```[language]
<<<<<<< SEARCH
[existing code to be replaced]
=======
[new code to replace the existing code]
>>>>>>> REPLACE
```

DO NOT change the existing code in the SEARCH block, even if it seems incorrect format.
"""
            )
        )

    def of_empty(
        self,
        action: Action,
        effect: EmptyEffect,
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(lambda _: InitialSeed())  # TODO

    def of_unknown_error(
        self, action: Action, effect: UnknownErrorEffect
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(lambda _: InitialSeed())  # TODO

    def of_wrong_patch(
        self,
        action: Action,
        effect: WrongPatchEffect,
    ) -> RequiresContext[Seed, WireContext]:
        return RequiresContext(
            lambda _: ErrorSeed(
                message="""Use this format for each SEARCH/REPLACE block:
file: [file_path]
```[language]
<<<<<<< SEARCH
[existing code to be replaced]
=======
[new code to replace the existing code]
>>>>>>> REPLACE
```
You should not change the existing code in the SEARCH block, even if it seems incorrect format.
"""
            )
        )
