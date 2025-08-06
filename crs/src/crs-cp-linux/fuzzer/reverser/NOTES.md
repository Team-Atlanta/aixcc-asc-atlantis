# Observations
## Tasks April 17
- mention in report the input size not being part of data blob condition
- @Andrew resolve the preprocessor macros to integers
- @Saketh create a verifier
  - what data structure the `test_lang.py` stores the output as
  - run a pass on the data structure and assert some conditions
- formally define language
- JSON output
- @Andrew determine if adding conditionals + multi-value fields is stable for LLM's output
- @Daniel write a prompt that describes the output's grammar
## LHS naming
Within the scope of a rule, an identifier would be defined uniquely. However,
the identifier is not unique globally. E.g. SIZE being defined for each message
type.

I think we can assume no cycles in our grammar.

**Unique identifiers vs assuming acyclic**

## Rule structuring
RHS elements can either be link to another rule, or a primitive (identified with
parentheses).

We can have arrays of a rule. So far this is only seen for the command array.

A rule can either be switch (with pipes) or a composition (no pipes, just
newlines)

For primitives, valid fields are `size` and `value`. Size is mandatory. If value
is defined, this data blob must obey that fixed value. Otherwise data blob is
free to use arbitrary values.

## Field ordering
Issue arises when size is specified before the value. Unless we have custom
parsing rule to recognize the link between size and value, need to enforce
ordering.

## Resolve switch stmt variable / value
CROMU 00001 uses macros for some case constants.

## Special formatting for input
Because inputs are function args, the size is not in the data blob itself.
**For blob generation, need to not consider the input size as part of data blob**
```
INPUT ::= BLOB_SIZE { size: 4 }
          BLOB { size: BLOB_SIZE }
```


## Specifying multiple values
If we want to fix certain values to a variable, we can do the following:
```
// Some option for command 1 which may only use the values 0, 5, 7, and 10
COMMAND1_OPTION ::= CREATE { size: 4, value: 0 }
                  | READ { size: 4, value: 5 }
                  | WRITE { size: 4, value: 7 }
                  | DESTROY { size: 4, value: 10 }

COMMAND1 ::= OPCODE { size: 4, value: 1 }
             COMMAND1_OPTION
             BINARY_SIZE { size: 4 }
             BINARY_DATA { size: BINARY_DATA }
```

Alternative is to introduce a new syntax for multiple values. Could be more
efficient for data blob generator.
```
// Some option for command 1 which may only use the values 0, 5, 7, and 10
COMMAND1 ::= OPCODE { size: 4, value: 1 }
             COMMAND1_OPTION { size: 4, values: [0, 5, 7, 10] }
             BINARY_SIZE { size: 4 }
             BINARY_DATA { size: BINARY_DATA }
```

If we want to apply this to the command enum, we need conditionals.
```
COMMAND ::= COMMAND_TYPE { size: 4, values: [0, 1] }
            DATA

DATA ::= SEND_PACKET { COMMAND_TYPE == 0 } 
       | SEND_NETLINK_PACKET { COMMAND_TYPE == 1 }
```

**Test which format is LLM friendly**

CVE-2022-0185 having issues with opcode generation.
