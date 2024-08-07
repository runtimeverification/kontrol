# Generated from src/kontrol/solidity/Solidity.g4 by ANTLR 4.13.2
from antlr4 import *

if "." in __name__:
    from .SolidityParser import SolidityParser
else:
    from SolidityParser import SolidityParser


# This class defines a complete listener for a parse tree produced by SolidityParser.
class SolidityListener(ParseTreeListener):

    # Enter a parse tree produced by SolidityParser#expression.
    def enterExpression(self, ctx: SolidityParser.ExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#expression.
    def exitExpression(self, ctx: SolidityParser.ExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#RelationalExpression.
    def enterRelationalExpression(self, ctx: SolidityParser.RelationalExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#RelationalExpression.
    def exitRelationalExpression(self, ctx: SolidityParser.RelationalExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#AndExpression.
    def enterAndExpression(self, ctx: SolidityParser.AndExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#AndExpression.
    def exitAndExpression(self, ctx: SolidityParser.AndExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#BooleanLiteral.
    def enterBooleanLiteral(self, ctx: SolidityParser.BooleanLiteralContext):
        pass

    # Exit a parse tree produced by SolidityParser#BooleanLiteral.
    def exitBooleanLiteral(self, ctx: SolidityParser.BooleanLiteralContext):
        pass

    # Enter a parse tree produced by SolidityParser#NotExpression.
    def enterNotExpression(self, ctx: SolidityParser.NotExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#NotExpression.
    def exitNotExpression(self, ctx: SolidityParser.NotExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#OrExpression.
    def enterOrExpression(self, ctx: SolidityParser.OrExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#OrExpression.
    def exitOrExpression(self, ctx: SolidityParser.OrExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#ParenthesizedBooleanExpression.
    def enterParenthesizedBooleanExpression(self, ctx: SolidityParser.ParenthesizedBooleanExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#ParenthesizedBooleanExpression.
    def exitParenthesizedBooleanExpression(self, ctx: SolidityParser.ParenthesizedBooleanExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#SubtractExpression.
    def enterSubtractExpression(self, ctx: SolidityParser.SubtractExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#SubtractExpression.
    def exitSubtractExpression(self, ctx: SolidityParser.SubtractExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#DivideExpression.
    def enterDivideExpression(self, ctx: SolidityParser.DivideExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#DivideExpression.
    def exitDivideExpression(self, ctx: SolidityParser.DivideExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#AddExpression.
    def enterAddExpression(self, ctx: SolidityParser.AddExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#AddExpression.
    def exitAddExpression(self, ctx: SolidityParser.AddExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#MultiplyExpression.
    def enterMultiplyExpression(self, ctx: SolidityParser.MultiplyExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#MultiplyExpression.
    def exitMultiplyExpression(self, ctx: SolidityParser.MultiplyExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#AtomExpression.
    def enterAtomExpression(self, ctx: SolidityParser.AtomExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#AtomExpression.
    def exitAtomExpression(self, ctx: SolidityParser.AtomExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#Variable.
    def enterVariable(self, ctx: SolidityParser.VariableContext):
        pass

    # Exit a parse tree produced by SolidityParser#Variable.
    def exitVariable(self, ctx: SolidityParser.VariableContext):
        pass

    # Enter a parse tree produced by SolidityParser#LengthAccess.
    def enterLengthAccess(self, ctx: SolidityParser.LengthAccessContext):
        pass

    # Exit a parse tree produced by SolidityParser#LengthAccess.
    def exitLengthAccess(self, ctx: SolidityParser.LengthAccessContext):
        pass

    # Enter a parse tree produced by SolidityParser#ArrayElement.
    def enterArrayElement(self, ctx: SolidityParser.ArrayElementContext):
        pass

    # Exit a parse tree produced by SolidityParser#ArrayElement.
    def exitArrayElement(self, ctx: SolidityParser.ArrayElementContext):
        pass

    # Enter a parse tree produced by SolidityParser#MappingElement.
    def enterMappingElement(self, ctx: SolidityParser.MappingElementContext):
        pass

    # Exit a parse tree produced by SolidityParser#MappingElement.
    def exitMappingElement(self, ctx: SolidityParser.MappingElementContext):
        pass

    # Enter a parse tree produced by SolidityParser#AddressLiteral.
    def enterAddressLiteral(self, ctx: SolidityParser.AddressLiteralContext):
        pass

    # Exit a parse tree produced by SolidityParser#AddressLiteral.
    def exitAddressLiteral(self, ctx: SolidityParser.AddressLiteralContext):
        pass

    # Enter a parse tree produced by SolidityParser#IntegerLiteral.
    def enterIntegerLiteral(self, ctx: SolidityParser.IntegerLiteralContext):
        pass

    # Exit a parse tree produced by SolidityParser#IntegerLiteral.
    def exitIntegerLiteral(self, ctx: SolidityParser.IntegerLiteralContext):
        pass

    # Enter a parse tree produced by SolidityParser#ParenthesizedArithmeticExpression.
    def enterParenthesizedArithmeticExpression(self, ctx: SolidityParser.ParenthesizedArithmeticExpressionContext):
        pass

    # Exit a parse tree produced by SolidityParser#ParenthesizedArithmeticExpression.
    def exitParenthesizedArithmeticExpression(self, ctx: SolidityParser.ParenthesizedArithmeticExpressionContext):
        pass

    # Enter a parse tree produced by SolidityParser#BlockAccess.
    def enterBlockAccess(self, ctx: SolidityParser.BlockAccessContext):
        pass

    # Exit a parse tree produced by SolidityParser#BlockAccess.
    def exitBlockAccess(self, ctx: SolidityParser.BlockAccessContext):
        pass

    # Enter a parse tree produced by SolidityParser#MsgAccess.
    def enterMsgAccess(self, ctx: SolidityParser.MsgAccessContext):
        pass

    # Exit a parse tree produced by SolidityParser#MsgAccess.
    def exitMsgAccess(self, ctx: SolidityParser.MsgAccessContext):
        pass

    # Enter a parse tree produced by SolidityParser#ContractVariableAccess.
    def enterContractVariableAccess(self, ctx: SolidityParser.ContractVariableAccessContext):
        pass

    # Exit a parse tree produced by SolidityParser#ContractVariableAccess.
    def exitContractVariableAccess(self, ctx: SolidityParser.ContractVariableAccessContext):
        pass

    # Enter a parse tree produced by SolidityParser#ContractVariableArrayElement.
    def enterContractVariableArrayElement(self, ctx: SolidityParser.ContractVariableArrayElementContext):
        pass

    # Exit a parse tree produced by SolidityParser#ContractVariableArrayElement.
    def exitContractVariableArrayElement(self, ctx: SolidityParser.ContractVariableArrayElementContext):
        pass


del SolidityParser
