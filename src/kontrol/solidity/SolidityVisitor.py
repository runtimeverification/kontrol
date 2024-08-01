# Generated from src/kontrol/solidity/Solidity.g4 by ANTLR 4.13.1
from antlr4 import *

if "." in __name__:
    from .SolidityParser import SolidityParser
else:
    from SolidityParser import SolidityParser

# This class defines a complete generic visitor for a parse tree produced by SolidityParser.


class SolidityVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SolidityParser#expression.
    def visitExpression(self, ctx: SolidityParser.ExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#RelationalExpression.
    def visitRelationalExpression(self, ctx: SolidityParser.RelationalExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#AndExpression.
    def visitAndExpression(self, ctx: SolidityParser.AndExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#BooleanLiteral.
    def visitBooleanLiteral(self, ctx: SolidityParser.BooleanLiteralContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#NotExpression.
    def visitNotExpression(self, ctx: SolidityParser.NotExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#OrExpression.
    def visitOrExpression(self, ctx: SolidityParser.OrExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#ParenthesizedBooleanExpression.
    def visitParenthesizedBooleanExpression(self, ctx: SolidityParser.ParenthesizedBooleanExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#SubtractExpression.
    def visitSubtractExpression(self, ctx: SolidityParser.SubtractExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#DivideExpression.
    def visitDivideExpression(self, ctx: SolidityParser.DivideExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#AddExpression.
    def visitAddExpression(self, ctx: SolidityParser.AddExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#MultiplyExpression.
    def visitMultiplyExpression(self, ctx: SolidityParser.MultiplyExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#AtomExpression.
    def visitAtomExpression(self, ctx: SolidityParser.AtomExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#Variable.
    def visitVariable(self, ctx: SolidityParser.VariableContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#LengthAccess.
    def visitLengthAccess(self, ctx: SolidityParser.LengthAccessContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#ArrayElement.
    def visitArrayElement(self, ctx: SolidityParser.ArrayElementContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#MappingElement.
    def visitMappingElement(self, ctx: SolidityParser.MappingElementContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#AddressLiteral.
    def visitAddressLiteral(self, ctx: SolidityParser.AddressLiteralContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#IntegerLiteral.
    def visitIntegerLiteral(self, ctx: SolidityParser.IntegerLiteralContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#ParenthesizedArithmeticExpression.
    def visitParenthesizedArithmeticExpression(self, ctx: SolidityParser.ParenthesizedArithmeticExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#BlockAccess.
    def visitBlockAccess(self, ctx: SolidityParser.BlockAccessContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by SolidityParser#MsgAccess.
    def visitMsgAccess(self, ctx: SolidityParser.MsgAccessContext):
        return self.visitChildren(ctx)


del SolidityParser
