class Special:
    def __init__(self, id, trace_id, has_branched, inst):
        self.id = id
        self.trace_id = trace_id
        self.has_branched = has_branched
        self.inst = inst

    def __repr__(self):
        #return f'[SPECIAL OBJ] id: {self.id} trace_id: {self.trace_id} has_branched: {self.has_branched} inst: {self.inst}'
        return ''
