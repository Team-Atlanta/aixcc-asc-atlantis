from typing import TypeAlias

from loop.framework.seed.variants import ErrorSeed, InitialSeed, PlainSeed, PrefixSeed

Seed: TypeAlias = PrefixSeed | InitialSeed | ErrorSeed | PlainSeed
