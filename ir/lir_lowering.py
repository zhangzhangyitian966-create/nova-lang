"""
MIR -> LIR 降级器

将 MIR（Mid-Level IR）降级为 LIR（Low-Level IR）-- 接近机器码的表示。
这是编译管道的第三步，输出用于 Cranelift 和 WasmGC 后端。
"""

from ir_nodes import (
    BOOL_TYPE,
    INT_TYPE,
    UNIT_TYPE,
    LIRBinOp,
    LIRBranch,
    LIRBuildADT,
    LIRBuildList,
    LIRBuildTuple,
    LIRCall,
    LIRData,
    LIRFieldAccess,
    LIRFunction,
    LIRGlobal,
    LIRIndex,
    LIRJump,
    LIRLabel,
    LIRLoadConst,
    LIRLoadGlobal,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreGlobal,
    LIRUnaryOp,
    MIRADTBuild,
    MIRBinOp,
    MIRBranch,
    MIRCall,
    MIRClosureCreate,
    MIRConst,
    MIRFieldAccess,
    MIRIndexAccess,
    MIRJump,
    MIRListBuild,
    MIRLoad,
    MIRMapBuild,
    MIRMatchJump,
    MIRPanic,
    MIRPhi,
    MIRReturn,
    MIRStore,
    MIRSwitch,
    MIRTupleBuild,
    MIRUnaryOp,
)


class LIRLoweringError(Exception):
    pass


class LIRLowering:
    """MIR -> LIR 降级器"""

    def __init__(self):
        self.ssa_to_loc = {}
        self.loc_counter = 0
        self.functions = {}

    def lower(self, mir_module):
        lir_module = LIRModule(name=mir_module.name)

        for name, mir_global in mir_module.globals.items():
            lir_global = LIRGlobal(name, mir_global.ir_type)
            if mir_global.init_value:
                init_str = (
                    str(mir_global.init_value.value)
                    if mir_global.init_value.value
                    else ""
                )
                lir_global.data = LIRData("data_%s" % name, init_str.encode("utf-8"))
            lir_module.globals.append(lir_global)

        for name, mir_fn in mir_module.functions.items():
            lir_module.functions[name] = self._lower_function(mir_fn)

        return lir_module

    def _new_loc(self):
        loc = "r%d" % self.loc_counter
        self.loc_counter += 1
        return loc

    def _lower_function(self, mir_fn):
        self.ssa_to_loc = {}
        self.loc_counter = 0

        lir_fn = LIRFunction(
            name=mir_fn.name,
            params=[],
            return_type=mir_fn.return_type,
        )

        for param_name, param_type, ssa_name in mir_fn.params:
            loc = self._new_loc()
            self.ssa_to_loc[ssa_name] = loc
            lir_fn.params.append((loc, param_type))

        body = []
        for bb in mir_fn.basic_blocks:
            label_instr = LIRLabel(name=bb.label)
            body.append(label_instr)

            for instr in bb.instructions:
                lir_instrs = self._lower_instruction(instr)
                body.extend(lir_instrs)

            if bb.terminator:
                lir_term = self._lower_terminator(bb.terminator)
                body.append(lir_term)

        lir_fn.body = body
        lir_fn.reg_alloc = dict(self.ssa_to_loc)
        lir_fn.stack_size = self.loc_counter * 8

        return lir_fn

    def _lower_instruction(self, instr):
        result = []

        if instr.result_name:
            loc = self._new_loc()
            self.ssa_to_loc[instr.result_name] = loc

        if isinstance(instr, MIRConst):
            lir = LIRLoadConst()
            lir.value = instr.value
            lir.const_type = instr.const_type
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRLoad):
            lir = LIRLoadGlobal()
            lir.global_name = instr.name
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRStore):
            lir = LIRStoreGlobal()
            lir.global_name = instr.name
            if instr.value:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.value, ""), instr.result_type)
                ]
            result.append(lir)

        elif isinstance(instr, MIRBinOp):
            lir = LIRBinOp()
            lir.op = instr.op
            if instr.left:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.left, ""), instr.result_type)
                ]
            if instr.right:
                lir.src_locs.append(
                    (self.ssa_to_loc.get(instr.right, ""), instr.result_type)
                )
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRUnaryOp):
            lir = LIRUnaryOp()
            lir.op = instr.op
            if instr.operand:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.operand, ""), instr.result_type)
                ]
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRCall):
            lir = LIRCall()
            lir.func_name = instr.callee
            lir.arg_count = len(instr.args)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRClosureCreate):
            lir = LIRLoadConst()
            lir.value = "<closure:%s>" % instr.fn_name
            lir.const_type = "closure"
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRListBuild):
            lir = LIRBuildList()
            lir.count = len(instr.elements)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRTupleBuild):
            lir = LIRBuildTuple()
            lir.count = len(instr.elements)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRMapBuild):
            lir = LIRBuildList()
            lir.count = len(instr.entries)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRADTBuild):
            lir = LIRBuildADT()
            lir.field_count = len(instr.fields)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRFieldAccess):
            lir = LIRFieldAccess()
            lir.offset = instr.field_index
            if instr.object:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.object, ""), instr.result_type)
                ]
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRIndexAccess):
            lir = LIRIndex()
            if instr.object:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.object, ""), instr.result_type)
                ]
            if instr.index:
                lir.src_locs.append(
                    (self.ssa_to_loc.get(instr.index, ""), instr.result_type)
                )
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRPhi):
            if instr.sources:
                _, src_ssa = instr.sources[0]
                if src_ssa in self.ssa_to_loc and instr.result_name:
                    lir = LIRLoadReg()
                    lir.src_locs = [
                        (self.ssa_to_loc.get(src_ssa, ""), instr.result_type)
                    ]
                    lir.dst_loc = (
                        self.ssa_to_loc.get(instr.result_name, ""),
                        instr.result_type,
                    )
                    result.append(lir)

        return result

    def _lower_terminator(self, term):
        if isinstance(term, MIRJump):
            return LIRJump(target=term.target)

        if isinstance(term, MIRBranch):
            lir = LIRBranch()
            if term.condition:
                lir.src_locs = [(self.ssa_to_loc.get(term.condition, ""), BOOL_TYPE)]
            return lir

        if isinstance(term, MIRReturn):
            lir = LIRReturn()
            if term.value and term.value in self.ssa_to_loc:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), UNIT_TYPE)]
            return lir

        if isinstance(term, MIRSwitch):
            lir = LIRJump(target=term.default_target)
            if term.value:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), INT_TYPE)]
            return lir

        if isinstance(term, MIRMatchJump):
            lir = LIRJump(target=term.default_target)
            if term.value:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), UNIT_TYPE)]
            return lir

        if isinstance(term, MIRPanic):
            return LIRPanic(message=term.message)

        return LIRReturn()
