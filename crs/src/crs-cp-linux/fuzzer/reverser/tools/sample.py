sample1 = """
    // INPUT is the start of the input format.
    // INPUT will be [CMD_CNT (4byte) ][ CMD_CNT chunks of CMD]
    INPUT ::= CMD_CNT { size: 4 }
              CMD[CMD_CNT]

    // CMD will be CMD1 or CMD2 if the example program has two commands.
    CMD   ::= CMD1
            | CMD2

    CMD1  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAG { size: 4 }
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA1_SIZE }     // the size of DATA1 is DATA_SIZE
              DATA2_SIZE { size: 4 }
              DATA2 { size: DATA2_SIZE }

    CMD2  ::= OPCODE { size: 4, value: 1}
              FLAG { size: 4}
    """

sample2 = """
    INPUT ::= CMD_CNTR { size: 4 }
              CMDI[CMD_CNTR]

    CMDI   ::= CMD0
            | CMD1

    CMD0  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAGG { size: 4 }
              DATA0_SIZE { size: 4 }
              DATA0 { size: DATA0_SIZE }     // the size of DATA1 is DATA_SIZE
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA1_SIZE }

    CMD1  ::= OPCODE { size: 4, value: 1}
              FLAGG { size: 4}
    """

sample3 = """
    INPUT ::= CMD_CNTR { size: 4 }
              CMDI[CMD_CNTR]

    CMDI   ::= CMD0
            | CMD1

    CMD0  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAGG { size: 4 }
              DATA0_SIZE { size: 4 }
              DATA0 { size: DATA0_SIZE }     // the size of DATA1 is DATA_SIZE
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA1_SIZE }

    CMD1  ::= OPCODE { size: 4, value: 1}
              FLAG { size: 4}
    """

sample4 = """
INPUT ::= COMMAND_CNT { size: 4 }
          COMMAND[COMMAND_CNT]

COMMAND ::= SETUP
          | LOOKUP

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE, type: string }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE, type: string }
"""

sample5 = """
INPUT ::= COMMAND_CNT { size: 4 }
          COMMAND[COMMAND_CNT]

COMMAND ::= SETUP
          | LOOKUP

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE }
"""

sample6 = """
INPUT ::= SIZE { size: 4 }
          TABLE { size: SIZE }
          LOOP
          LOOP

LOOP ::= TABLE_SIZE { size: 4 }
              TABLE { size: TABLE_SIZE }
              SET_SIZE { size: 4 }
              SET { size: SET_SIZE }
"""

sample7 = """
INPUT ::= SIZE { size: 4 }
          TABLE { size: SIZE }
          LOOP[2]

LOOP ::= TABLE_SIZE { size: 4 }
              TABLE { size: TABLE_SIZE }
              SET_SIZE { size: 4 }
              SET { size: SET_SIZE }

"""

sample8 = """
INPUT ::= SIZE { size: 4 }
          TABLE { size: SIZE }
          LOOP

LOOP ::= LOOP_BODY
         LOOP_BODY

LOOP_BODY ::= TABLE_SIZE { size: 4 }
              TABLE { size: TABLE_SIZE }
              SET_SIZE { size: 4 }
              SET { size: SET_SIZE }
"""

sample9 = """
INPUT ::= SIZE { size: 4 }
          TABLE { size: SIZE }
          TABLE_SIZE { size: 4 }
          TABLE { size: TABLE_SIZE }
          SET_SIZE { size: 4 }
          SET { size: SET_SIZE }
          TABLE { size: TABLE_SIZE }
          SET_SIZE { size: 4 }
          SET { size: SET_SIZE }
"""

sample10 = """
INPUT ::= TEST_CNT { size: 4 }
          COMMAND[3]

COMMAND ::= SETUP
            TEST_UNION

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

TEST_UNION ::=  LOOKUP
             |  DUMMY

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE }

DUMMY ::=   DATA { size: 16 }
            DATA2 { size: 8 }
            

"""

sample11 = """
INPUT ::= TEST_CNT { size: 4 }
          COMMAND
          COMMAND
          COMMAND

COMMAND ::= SETUP
            TEST_UNION

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

TEST_UNION ::=  LOOKUP
             |  DUMMY

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE }

DUMMY ::=   DATA { size: 16 }
            DATA2 { size: 8 }
            

"""

sample12 = """
INPUT ::= TEST_CNT { size: 4 }
          COMMAND
          COMMAND
          COMMAND

COMMAND ::= SETUP
            TEST_UNION

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

TEST_UNION ::=  LOOKUP
             |  DUMMY

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE }

DUMMY ::=   DATA { size: 16 }
            DATA2 { size: 8 }
            

"""

sample13 = """
INPUT ::= COMMAND_CNT { size: 4 }
          COMMAND[COMMAND_CNT]

COMMAND ::= SETUP
          | LOOKUP

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4, type: string }
          DATA { size: SIZE }

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE, type: string }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE, type: string }
"""

sample14 = """
INPUT ::= COMMAND_CNT { size: 4 }
          COMMAND[COMMAND_CNT]

COMMAND ::= SETUP
          | LOOKUP

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4, type: string }
          DATA { size: SIZE }

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           SET_DATA { size: SET_SIZE, type: string }
"""

sample15 = """
    INPUT ::= CMD_CNTR { size: 4 }
              CMDI[CMD_CNTR]

    CMDI   ::= CMD0
             | CMD1

    CMD0  ::= OPCODE { size: 4, value: 1}
              FLAGG { size: 4}

    CMD1  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAGG { size: 4 }
              DATA0_SIZE { size: 4 }
              DATA0 { size: DATA0_SIZE }     // the size of DATA1 is DATA_SIZE
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA1_SIZE }
    """

sample16 = """
    INPUT ::= CMD_CNTR { size: 4 }
              CMDI[CMD_CNTR]

    CMDI   ::= CMD1
             | CMD0

    CMD0  ::= OPCODE { size: 4, value: 1}
              FLAGG { size: 4}

    CMD1  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAGG { size: 4 }
              DATA0_SIZE { size: 4 }
              DATA0 { size: DATA0_SIZE }     // the size of DATA1 is DATA_SIZE
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA0_SIZE }
    """

# TODO with loose parental scoping, this is actually invalid b/c SIZE
#      already exist in CMD2 parent's scope
sample17 = """
    INPUT ::= SIZE { size: 4 }
              CMD1 { size: SIZE }
              CMD2

    CMD2 ::= SIZE { size: 4 }
             CMD1 { size: SIZE }
             CMD3

    CMD3 ::= FLAG { size: 4 }
    """

# Manufactered e.g. where CMD2 isn't used
sample18 = """
    INPUT ::= SIZE { size: 4 }
              CMD1 { size: SIZE }
              CMD2

    CMD2 ::= FLAG { size: 4 }

    CMD3 ::= SIZE { size: 4 }
             CMD1 { size: SIZE }
             CMD2
    """

sample19 = """
INPUT ::= TEST_CNT { size: 4 }
          COMMAND[TEST_CNT]

COMMAND ::= SETUP
            TEST_UNION

SETUP ::= OPCODE { size: 4, value: 0 }
          SIZE { size: 4 }
          DATA { size: SIZE }

TEST_UNION ::=  LOOKUP
             |  DUMMY

LOOKUP ::= OPCODE { size: 4, value: 1 }
           TABLE_SIZE { size: 4 }
           TABLE_DATA { size: TABLE_SIZE }
           SET_SIZE { size: 4 }
           DUMMY [SET_SIZE]

DUMMY ::=   DATA { size: 16 }
            DATA2 { size: 8 }
            

"""

sample20 = """
INPUT ::= SIZE { size: 4 }
          COMMAND

COMMAND ::= DATA { size: SIZE }
"""
sample21 = """
INPUT ::= v2 { size: 4 }
          v1[v2]
v0 ::= v2 { size: 4, value: 0 }
       v3 { size: 4 }
       v4 { size: v3 }
v1 ::= v0
"""

sample22 = """
INPUT ::= v2 { size: 4 }
          v1[v2]
v1 ::= v2 { size: 4, value: 0 }
         v3 { size: 4 }
         v4 { size: v3 }
v0 ::= v1
"""