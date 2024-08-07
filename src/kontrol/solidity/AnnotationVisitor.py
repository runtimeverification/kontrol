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

    def visitVariable(self, ctx: SolidityParser.VariableContext) -> KInner:
        var_name = ctx.getText()
        # Search for matches in function inputs
        for input in self.method.inputs:
            if input.name == var_name:
                # TODO: add support for complex types
                return abstract_term_safely(KVariable('_###SOLIDITY_ARG_VAR###_'), base_name=f'V{input.arg_name}')

        # Search for matches in contract storage fields
        for field in self.storage_fields:
            if field.label == var_name:
                storage_map: KInner = KVariable(self.contract_name + '_STORAGE', sort=KSort('Map'))
                return KEVM.lookup(storage_map, intToken(field.slot))

        raise ValueError(f'Variable {var_name} not found in function inputs or storage fields of {self.method.name}.')

    def visitContractVariableAccess(self, ctx: SolidityParser.ContractVariableAccessContext):
        contract_field_name: str = ctx.contractVariableAccessExpr().VariableName(0).getText()
        var_name: str = ctx.contractVariableAccessExpr().VariableName(1).getText()

        for field in self.storage_fields:
            if field.data_type.startswith('contract ') and field.label == contract_field_name:
                contract_type = field.data_type.split(' ')[1]

                # TODO: it is possible for a contact to have an interface annotation, `linked_interface`
                for full_contract_name, contract_obj in self.foundry.contracts.items():
                    # TODO: this is not enough, it is possible that the same contract comes with
                    # src% and test%, in which case we don't know automatically which one to choose
                    if full_contract_name.split('%')[-1] == contract_type:
                        for field in contract_obj.fields:
                            if field.label == var_name:
                                storage_map: KInner = KVariable(
                                    self.contract_name + '_' + contract_field_name.upper() + '_STORAGE', sort=KSort('Map')
                                )
                                return KEVM.lookup(storage_map, intToken(field.slot))

        raise ValueError(f'Variable {contract_field_name}.{var_name} not found.')

    def visitIntegerLiteral(self, ctx: SolidityParser.IntegerLiteralContext) -> KInner:
        return intToken(ctx.getText())

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
