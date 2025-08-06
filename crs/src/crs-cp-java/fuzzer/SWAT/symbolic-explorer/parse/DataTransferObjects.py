
from typing import List, Optional

from pydantic import BaseModel


class TraceItem(BaseModel):
    iid: int
    constraint: Optional[str] = None
    branched: bool
    type: str
    inst: Optional[str] = None

class InputItem(BaseModel):
    name: str
    value: str
    type: str
    lowerBound: str
    upperBound: str
    hard_constraints: List[str]

class VariableItem(BaseModel):
    variableName: str
    variableType: str
    variableIndex: int

class ConstraintRequest(BaseModel):
    trace: List[TraceItem]
    inputs: List[InputItem]
    symbolicVariables: List[VariableItem]
