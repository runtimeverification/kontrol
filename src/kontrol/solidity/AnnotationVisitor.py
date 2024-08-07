from kevm_pyk.kevm import KEVM
from pyk.kast import KInner
from pyk.kast.inner import KApply, KSort, KVariable
from pyk.kast.manip import abstract_term_safely
from pyk.prelude.kbool import FALSE, TRUE
from pyk.prelude.kint import intToken

from ..foundry import Foundry
from ..solc_to_k import Contract, StorageField
from .SolidityParser import SolidityParser
from .SolidityVisitor import SolidityVisitor


class AnnotationVisitor(SolidityVisitor):
    def __init__(
        self,
        method: Contract.Method | Contract.Constructor,
        foundry: Foundry,
        storage_fields: tuple[StorageField, ...],
        contract_name: str,
    ):
        self.method = method
        self.foundry = foundry
        self.storage_fields = storage_fields
        self.contract_name = contract_name

    # def visitAndExpression(self, ctx: SolidityParser.AndExpressionContext):
    #     left = self.visit(ctx.booleanExpression(0))
    #     right = self.visit(ctx.booleanExpression(1))
    #     return left and right

    # def visitOrExpression(self, ctx: SolidityParser.OrExpressionContext):
    #     left = self.visit(ctx.booleanExpression(0))
    #     right = self.visit(ctx.booleanExpression(1))
    #     return left or right

    # def visitNotExpression(self, ctx: SolidityParser.NotExpressionContext):
    #     value = self.visit(ctx.booleanExpression())
    #     return not value

    def visitRelationalExpression(self, ctx: SolidityParser.RelationalExpressionContext) -> KApply:
        left = self.visit(ctx.arithmeticExpression(0))
        right = self.visit(ctx.arithmeticExpression(1))

        op = ctx.RelOp().getText()

        # Map operators to KLabel applications
        operator_mapping = {
            '<=': '_<=Int_',
            '>=': '_>=Int_',
            '==': '_==Int_',
            '!=': '_=/=Int_',
            '<': '_<Int_',
            '>': '_>Int_',
        }

        if op in operator_mapping:
            operator_label = operator_mapping[op]
        else:
            raise ValueError(f'Unsupported operator in a precondition: {op}')

        return KApply(operator_label, left, right)

    def visitBooleanLiteral(self, ctx: SolidityParser.BooleanLiteralContext) -> KInner:
        return TRUE if ctx.getText() == 'true' else FALSE

        # def visitAddExpression(self, ctx: SolidityParser.AddExpressionContext):
        #     left = self.visit(ctx.arithmeticExpression(0))
        #     right = self.visit(ctx.arithmeticExpression(1))
        #     return left + right

        # def visitSubtractExpression(self, ctx: SolidityParser.SubtractExpressionContext):
        #     left = self.visit(ctx.arithmeticExpression(0))
        #     right = self.visit(ctx.arithmeticExpression(1))
        #     return left - right

        # def visitMultiplyExpression(self, ctx: SolidityParser.MultiplyExpressionContext):
        #     left = self.visit(ctx.arithmeticExpression(0))
        #     right = self.visit(ctx.arithmeticExpression(1))
        #     return left * right

        # def visitDivideExpression(self, ctx: SolidityParser.DivideExpressionContext):
        #     left = self.visit(ctx.arithmeticExpression(0))
        #     right = self.visit(ctx.arithmeticExpression(1))
        #     return left / right

    def visitVariable(self, ctx: SolidityParser.VariableContext) -> KInner:
        var_name = ctx.getText()
        for input in self.method.inputs:
            if input.name == var_name:
                # TODO(palina): add support for complex types
                return abstract_term_safely(KVariable('_###SOLIDITY_ARG_VAR###_'), base_name=f'V{input.arg_name}')

        # TODO: add support for storage fields
        for field in self.storage_fields:
            if field.label == var_name:
                storage_map: KInner = KVariable(self.contract_name + '_STORAGE', sort=KSort('Map'))
                return KEVM.lookup(storage_map, intToken(field.slot))
                # return abstract_term_safely(KVariable('_###SOLIDITY_STORAGE_VAR###_'), base_name=f'V{field.name}')
        # for field in self.method.contract.storage_fields:
        # if field.name == var_name:
        # Perform the necessary action for a matching storage field
        # break  # Exit the loop once the matching field is found
        raise ValueError(f'Not implemented yet: {var_name}')

    # def visitContractVariableAccess(self, ctx: SolidityParser.ContractVariableAccessContext):
    #     contract_name = ctx.VariableName(0).getText()
    #     var_name = ctx.VariableName(1).getText()

        # TODO (palina): add support for contract variables
        # - find contract
        # - find variables
        # - lookup
        # return self.contracts.get(contract_name, {}).get(var_name, 0)

    # def visitLengthAccess(self, ctx: SolidityParser.LengthAccessContext):
    #     var_name = ctx.variableName().getText()
    #     return len(self.context.get(var_name, ""))

    # def visitArrayElement(self, ctx: SolidityParser.ArrayElementContext):
    #     var_name = ctx.variableName().getText()
    #     index = int(ctx.INTEGER().getText())
    #     return self.context.get(var_name, [])[index]

    # def visitMappingElement(self, ctx: SolidityParser.MappingElementContext):
    #     var_name = ctx.variableName().getText()
    #     key = ctx.variableName().getText()
    #     return self.context.get(var_name, {}).get(key, 0)

    # def visitAddressLiteral(self, ctx: SolidityParser.AddressLiteralContext):
    #     return ctx.getText()

    def visitIntegerLiteral(self, ctx: SolidityParser.IntegerLiteralContext) -> KInner:
        return intToken(ctx.getText())
