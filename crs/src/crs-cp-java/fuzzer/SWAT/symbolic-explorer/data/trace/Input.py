class Input:
    """
    Represents a symbolic input with its concrete value from a trace.

    Attributes:
        name (str): The symbolic name of the input.
        value (any): The concrete value of the input.
        type (str): The data type of the input parameter.
        lower_bound (any): The (symbolic) lower bound for the value of the input parameter, if applicable.
        upper_bound (any): The (symbolic) upper bound for the value of the input parameter, if applicable.
    """

    def __init__(self, name, value, type, lower_bound, upper_bound, hard_constraints):
        """
        Initializes a new instance of the Input class.

        Args:
            name (str): The symbolic name of the input.
            value (any): The concrete value of the input.
            type (str): The data type of the input parameter.
            lower_bound (any): The (symbolic) lower bound for the value of the input parameter, if applicable.
            upper_bound (any): The (symbolic) upper bound for the value of the input parameter, if applicable.
        """
        self.name = name
        self.value = value
        self.type = type
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.hard_constraints = hard_constraints

    def __repr__(self):
        lb = self.lower_bound
        ub = self.upper_bound
        if type(lb) == type(''):
            lb = lb.strip()
        if type(ub) == type(''):
            ub = ub.strip()
        value = self.value
        if self.type == 'String':
            list_value = eval(value)
            #print(list_value)
            if type(list_value) == type([]):
                new_list_value = []
                for item in list_value:
                    while True:
                        remainder = item & 0xff
                        new_list_value.append(remainder)
                        if item < 256:
                            break
                        else:
                            item = item >> 8
                list_value = new_list_value
            #print(list_value)
            value = bytes(list_value)

        r_str =     f'object(Input): name: {self.name} type: {self.type} '
        r_str +=    f'value: {repr(value)} '
        r_str +=    f'lb: {lb} ub: {ub} '
        r_str +=    f'hard_constraints_len : {len(self.hard_constraints)}'
        for c in self.hard_constraints:
            r_str += f"\nINPUT HARD CONSTRAINTS :   {c}"
        return r_str
