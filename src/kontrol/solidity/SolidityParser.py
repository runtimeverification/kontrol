# Generated from src/kontrol/solidity/Solidity.g4 by ANTLR 4.13.1
# encoding: utf-8
import sys

from antlr4 import (
    ATN,
    DFA,
    ATNDeserializer,
    NoViableAltException,
    Parser,
    ParserATNSimulator,
    ParserRuleContext,
    ParseTreeListener,
    ParseTreeVisitor,
    PredictionContextCache,
    RecognitionException,
    RuleContext,
    Token,
    TokenStream,
)

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


def serializedATN():
    return [
        4,
        1,
        21,
        70,
        2,
        0,
        7,
        0,
        2,
        1,
        7,
        1,
        2,
        2,
        7,
        2,
        2,
        3,
        7,
        3,
        1,
        0,
        1,
        0,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        3,
        1,
        23,
        8,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        5,
        1,
        31,
        8,
        1,
        10,
        1,
        12,
        1,
        34,
        9,
        1,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        2,
        5,
        2,
        51,
        8,
        2,
        10,
        2,
        12,
        2,
        54,
        9,
        2,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
        3,
        3,
        3,
        68,
        8,
        3,
        1,
        3,
        0,
        2,
        2,
        4,
        4,
        0,
        2,
        4,
        6,
        0,
        0,
        82,
        0,
        8,
        1,
        0,
        0,
        0,
        2,
        22,
        1,
        0,
        0,
        0,
        4,
        35,
        1,
        0,
        0,
        0,
        6,
        67,
        1,
        0,
        0,
        0,
        8,
        9,
        3,
        2,
        1,
        0,
        9,
        1,
        1,
        0,
        0,
        0,
        10,
        11,
        6,
        1,
        -1,
        0,
        11,
        12,
        5,
        3,
        0,
        0,
        12,
        23,
        3,
        2,
        1,
        4,
        13,
        14,
        3,
        4,
        2,
        0,
        14,
        15,
        5,
        20,
        0,
        0,
        15,
        16,
        3,
        4,
        2,
        0,
        16,
        23,
        1,
        0,
        0,
        0,
        17,
        23,
        5,
        10,
        0,
        0,
        18,
        19,
        5,
        4,
        0,
        0,
        19,
        20,
        3,
        2,
        1,
        0,
        20,
        21,
        5,
        5,
        0,
        0,
        21,
        23,
        1,
        0,
        0,
        0,
        22,
        10,
        1,
        0,
        0,
        0,
        22,
        13,
        1,
        0,
        0,
        0,
        22,
        17,
        1,
        0,
        0,
        0,
        22,
        18,
        1,
        0,
        0,
        0,
        23,
        32,
        1,
        0,
        0,
        0,
        24,
        25,
        10,
        6,
        0,
        0,
        25,
        26,
        5,
        1,
        0,
        0,
        26,
        31,
        3,
        2,
        1,
        7,
        27,
        28,
        10,
        5,
        0,
        0,
        28,
        29,
        5,
        2,
        0,
        0,
        29,
        31,
        3,
        2,
        1,
        6,
        30,
        24,
        1,
        0,
        0,
        0,
        30,
        27,
        1,
        0,
        0,
        0,
        31,
        34,
        1,
        0,
        0,
        0,
        32,
        30,
        1,
        0,
        0,
        0,
        32,
        33,
        1,
        0,
        0,
        0,
        33,
        3,
        1,
        0,
        0,
        0,
        34,
        32,
        1,
        0,
        0,
        0,
        35,
        36,
        6,
        2,
        -1,
        0,
        36,
        37,
        3,
        6,
        3,
        0,
        37,
        52,
        1,
        0,
        0,
        0,
        38,
        39,
        10,
        5,
        0,
        0,
        39,
        40,
        5,
        6,
        0,
        0,
        40,
        51,
        3,
        4,
        2,
        6,
        41,
        42,
        10,
        4,
        0,
        0,
        42,
        43,
        5,
        7,
        0,
        0,
        43,
        51,
        3,
        4,
        2,
        5,
        44,
        45,
        10,
        3,
        0,
        0,
        45,
        46,
        5,
        8,
        0,
        0,
        46,
        51,
        3,
        4,
        2,
        4,
        47,
        48,
        10,
        2,
        0,
        0,
        48,
        49,
        5,
        9,
        0,
        0,
        49,
        51,
        3,
        4,
        2,
        3,
        50,
        38,
        1,
        0,
        0,
        0,
        50,
        41,
        1,
        0,
        0,
        0,
        50,
        44,
        1,
        0,
        0,
        0,
        50,
        47,
        1,
        0,
        0,
        0,
        51,
        54,
        1,
        0,
        0,
        0,
        52,
        50,
        1,
        0,
        0,
        0,
        52,
        53,
        1,
        0,
        0,
        0,
        53,
        5,
        1,
        0,
        0,
        0,
        54,
        52,
        1,
        0,
        0,
        0,
        55,
        68,
        5,
        13,
        0,
        0,
        56,
        68,
        5,
        14,
        0,
        0,
        57,
        68,
        5,
        15,
        0,
        0,
        58,
        68,
        5,
        16,
        0,
        0,
        59,
        68,
        5,
        17,
        0,
        0,
        60,
        68,
        5,
        11,
        0,
        0,
        61,
        62,
        5,
        4,
        0,
        0,
        62,
        63,
        3,
        4,
        2,
        0,
        63,
        64,
        5,
        5,
        0,
        0,
        64,
        68,
        1,
        0,
        0,
        0,
        65,
        68,
        5,
        18,
        0,
        0,
        66,
        68,
        5,
        19,
        0,
        0,
        67,
        55,
        1,
        0,
        0,
        0,
        67,
        56,
        1,
        0,
        0,
        0,
        67,
        57,
        1,
        0,
        0,
        0,
        67,
        58,
        1,
        0,
        0,
        0,
        67,
        59,
        1,
        0,
        0,
        0,
        67,
        60,
        1,
        0,
        0,
        0,
        67,
        61,
        1,
        0,
        0,
        0,
        67,
        65,
        1,
        0,
        0,
        0,
        67,
        66,
        1,
        0,
        0,
        0,
        68,
        7,
        1,
        0,
        0,
        0,
        6,
        22,
        30,
        32,
        50,
        52,
        67,
    ]


class SolidityParser(Parser):

    grammarFileName = "Solidity.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = ["<INVALID>", "'&&'", "'||'", "'!'", "'('", "')'", "'+'", "'-'", "'*'", "'/'"]

    symbolicNames = [
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "BOOLEAN_LITERAL",
        "INTEGER",
        "ADDRESS",
        "VariableName",
        "LengthAccess",
        "ArrayElement",
        "MappingElement",
        "AddressLiteral",
        "BlockAccess",
        "MsgAccess",
        "RelOp",
        "WS",
    ]

    RULE_expression = 0
    RULE_booleanExpression = 1
    RULE_arithmeticExpression = 2
    RULE_atom = 3

    ruleNames = ["expression", "booleanExpression", "arithmeticExpression", "atom"]

    EOF = Token.EOF
    T__0 = 1
    T__1 = 2
    T__2 = 3
    T__3 = 4
    T__4 = 5
    T__5 = 6
    T__6 = 7
    T__7 = 8
    T__8 = 9
    BOOLEAN_LITERAL = 10
    INTEGER = 11
    ADDRESS = 12
    VariableName = 13
    LengthAccess = 14
    ArrayElement = 15
    MappingElement = 16
    AddressLiteral = 17
    BlockAccess = 18
    MsgAccess = 19
    RelOp = 20
    WS = 21

    def __init__(self, input: TokenStream, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None

    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent: ParserRuleContext = None, invokingState: int = -1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext, 0)

        def getRuleIndex(self):
            return SolidityParser.RULE_expression

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExpression"):
                listener.enterExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExpression"):
                listener.exitExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitExpression"):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)

    def expression(self):

        localctx = SolidityParser.ExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 8
            self.booleanExpression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class BooleanExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent: ParserRuleContext = None, invokingState: int = -1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return SolidityParser.RULE_booleanExpression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class RelationalExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, i)

        def RelOp(self):
            return self.getToken(SolidityParser.RelOp, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterRelationalExpression"):
                listener.enterRelationalExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitRelationalExpression"):
                listener.exitRelationalExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitRelationalExpression"):
                return visitor.visitRelationalExpression(self)
            else:
                return visitor.visitChildren(self)

    class AndExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.BooleanExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAndExpression"):
                listener.enterAndExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAndExpression"):
                listener.exitAndExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitAndExpression"):
                return visitor.visitAndExpression(self)
            else:
                return visitor.visitChildren(self)

    class BooleanLiteralContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BOOLEAN_LITERAL(self):
            return self.getToken(SolidityParser.BOOLEAN_LITERAL, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBooleanLiteral"):
                listener.enterBooleanLiteral(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBooleanLiteral"):
                listener.exitBooleanLiteral(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitBooleanLiteral"):
                return visitor.visitBooleanLiteral(self)
            else:
                return visitor.visitChildren(self)

    class NotExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNotExpression"):
                listener.enterNotExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNotExpression"):
                listener.exitNotExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitNotExpression"):
                return visitor.visitNotExpression(self)
            else:
                return visitor.visitChildren(self)

    class OrExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.BooleanExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOrExpression"):
                listener.enterOrExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOrExpression"):
                listener.exitOrExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitOrExpression"):
                return visitor.visitOrExpression(self)
            else:
                return visitor.visitChildren(self)

    class ParenthesizedBooleanExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenthesizedBooleanExpression"):
                listener.enterParenthesizedBooleanExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenthesizedBooleanExpression"):
                listener.exitParenthesizedBooleanExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitParenthesizedBooleanExpression"):
                return visitor.visitParenthesizedBooleanExpression(self)
            else:
                return visitor.visitChildren(self)

    def booleanExpression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SolidityParser.BooleanExpressionContext(self, self._ctx, _parentState)
        _startState = 2
        self.enterRecursionRule(localctx, 2, self.RULE_booleanExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 22
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 0, self._ctx)
            if la_ == 1:
                localctx = SolidityParser.NotExpressionContext(self, localctx)
                self._ctx = localctx

                self.state = 11
                self.match(SolidityParser.T__2)
                self.state = 12
                self.booleanExpression(4)

            elif la_ == 2:
                localctx = SolidityParser.RelationalExpressionContext(self, localctx)
                self._ctx = localctx
                self.state = 13
                self.arithmeticExpression(0)
                self.state = 14
                self.match(SolidityParser.RelOp)
                self.state = 15
                self.arithmeticExpression(0)

            elif la_ == 3:
                localctx = SolidityParser.BooleanLiteralContext(self, localctx)
                self._ctx = localctx
                self.state = 17
                self.match(SolidityParser.BOOLEAN_LITERAL)

            elif la_ == 4:
                localctx = SolidityParser.ParenthesizedBooleanExpressionContext(self, localctx)
                self._ctx = localctx
                self.state = 18
                self.match(SolidityParser.T__3)
                self.state = 19
                self.booleanExpression(0)
                self.state = 20
                self.match(SolidityParser.T__4)

            self._ctx.stop = self._input.LT(-1)
            self.state = 32
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 2, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    self.state = 30
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 1, self._ctx)
                    if la_ == 1:
                        localctx = SolidityParser.AndExpressionContext(
                            self, SolidityParser.BooleanExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_booleanExpression)
                        self.state = 24
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 25
                        self.match(SolidityParser.T__0)
                        self.state = 26
                        self.booleanExpression(7)

                    elif la_ == 2:
                        localctx = SolidityParser.OrExpressionContext(
                            self, SolidityParser.BooleanExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_booleanExpression)
                        self.state = 27
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 28
                        self.match(SolidityParser.T__1)
                        self.state = 29
                        self.booleanExpression(6)

                self.state = 34
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 2, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class ArithmeticExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent: ParserRuleContext = None, invokingState: int = -1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return SolidityParser.RULE_arithmeticExpression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class SubtractExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterSubtractExpression"):
                listener.enterSubtractExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitSubtractExpression"):
                listener.exitSubtractExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitSubtractExpression"):
                return visitor.visitSubtractExpression(self)
            else:
                return visitor.visitChildren(self)

    class DivideExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDivideExpression"):
                listener.enterDivideExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDivideExpression"):
                listener.exitDivideExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitDivideExpression"):
                return visitor.visitDivideExpression(self)
            else:
                return visitor.visitChildren(self)

    class AddExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAddExpression"):
                listener.enterAddExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAddExpression"):
                listener.exitAddExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitAddExpression"):
                return visitor.visitAddExpression(self)
            else:
                return visitor.visitChildren(self)

    class MultiplyExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMultiplyExpression"):
                listener.enterMultiplyExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMultiplyExpression"):
                listener.exitMultiplyExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitMultiplyExpression"):
                return visitor.visitMultiplyExpression(self)
            else:
                return visitor.visitChildren(self)

    class AtomExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(SolidityParser.AtomContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAtomExpression"):
                listener.enterAtomExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAtomExpression"):
                listener.exitAtomExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitAtomExpression"):
                return visitor.visitAtomExpression(self)
            else:
                return visitor.visitChildren(self)

    def arithmeticExpression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SolidityParser.ArithmeticExpressionContext(self, self._ctx, _parentState)
        _startState = 4
        self.enterRecursionRule(localctx, 4, self.RULE_arithmeticExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            localctx = SolidityParser.AtomExpressionContext(self, localctx)
            self._ctx = localctx

            self.state = 36
            self.atom()
            self._ctx.stop = self._input.LT(-1)
            self.state = 52
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 4, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    self.state = 50
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 3, self._ctx)
                    if la_ == 1:
                        localctx = SolidityParser.AddExpressionContext(
                            self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 38
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 39
                        self.match(SolidityParser.T__5)
                        self.state = 40
                        self.arithmeticExpression(6)

                    elif la_ == 2:
                        localctx = SolidityParser.SubtractExpressionContext(
                            self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 41
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 42
                        self.match(SolidityParser.T__6)
                        self.state = 43
                        self.arithmeticExpression(5)

                    elif la_ == 3:
                        localctx = SolidityParser.MultiplyExpressionContext(
                            self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 44
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 45
                        self.match(SolidityParser.T__7)
                        self.state = 46
                        self.arithmeticExpression(4)

                    elif la_ == 4:
                        localctx = SolidityParser.DivideExpressionContext(
                            self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 47
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 48
                        self.match(SolidityParser.T__8)
                        self.state = 49
                        self.arithmeticExpression(3)

                self.state = 54
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 4, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent: ParserRuleContext = None, invokingState: int = -1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return SolidityParser.RULE_atom

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ParenthesizedArithmeticExpressionContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self):
            return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenthesizedArithmeticExpression"):
                listener.enterParenthesizedArithmeticExpression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenthesizedArithmeticExpression"):
                listener.exitParenthesizedArithmeticExpression(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitParenthesizedArithmeticExpression"):
                return visitor.visitParenthesizedArithmeticExpression(self)
            else:
                return visitor.visitChildren(self)

    class LengthAccessContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LengthAccess(self):
            return self.getToken(SolidityParser.LengthAccess, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLengthAccess"):
                listener.enterLengthAccess(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLengthAccess"):
                listener.exitLengthAccess(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitLengthAccess"):
                return visitor.visitLengthAccess(self)
            else:
                return visitor.visitChildren(self)

    class VariableContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VariableName(self):
            return self.getToken(SolidityParser.VariableName, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterVariable"):
                listener.enterVariable(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitVariable"):
                listener.exitVariable(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitVariable"):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)

    class MappingElementContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MappingElement(self):
            return self.getToken(SolidityParser.MappingElement, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMappingElement"):
                listener.enterMappingElement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMappingElement"):
                listener.exitMappingElement(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitMappingElement"):
                return visitor.visitMappingElement(self)
            else:
                return visitor.visitChildren(self)

    class BlockAccessContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BlockAccess(self):
            return self.getToken(SolidityParser.BlockAccess, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBlockAccess"):
                listener.enterBlockAccess(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBlockAccess"):
                listener.exitBlockAccess(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitBlockAccess"):
                return visitor.visitBlockAccess(self)
            else:
                return visitor.visitChildren(self)

    class AddressLiteralContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def AddressLiteral(self):
            return self.getToken(SolidityParser.AddressLiteral, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAddressLiteral"):
                listener.enterAddressLiteral(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAddressLiteral"):
                listener.exitAddressLiteral(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitAddressLiteral"):
                return visitor.visitAddressLiteral(self)
            else:
                return visitor.visitChildren(self)

    class ArrayElementContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ArrayElement(self):
            return self.getToken(SolidityParser.ArrayElement, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterArrayElement"):
                listener.enterArrayElement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitArrayElement"):
                listener.exitArrayElement(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitArrayElement"):
                return visitor.visitArrayElement(self)
            else:
                return visitor.visitChildren(self)

    class IntegerLiteralContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INTEGER(self):
            return self.getToken(SolidityParser.INTEGER, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIntegerLiteral"):
                listener.enterIntegerLiteral(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIntegerLiteral"):
                listener.exitIntegerLiteral(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitIntegerLiteral"):
                return visitor.visitIntegerLiteral(self)
            else:
                return visitor.visitChildren(self)

    class MsgAccessContext(AtomContext):

        def __init__(self, parser, ctx: ParserRuleContext):  # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MsgAccess(self):
            return self.getToken(SolidityParser.MsgAccess, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMsgAccess"):
                listener.enterMsgAccess(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMsgAccess"):
                listener.exitMsgAccess(self)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitMsgAccess"):
                return visitor.visitMsgAccess(self)
            else:
                return visitor.visitChildren(self)

    def atom(self):

        localctx = SolidityParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_atom)
        try:
            self.state = 67
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [13]:
                localctx = SolidityParser.VariableContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 55
                self.match(SolidityParser.VariableName)
            elif token in [14]:
                localctx = SolidityParser.LengthAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 56
                self.match(SolidityParser.LengthAccess)
            elif token in [15]:
                localctx = SolidityParser.ArrayElementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 57
                self.match(SolidityParser.ArrayElement)
            elif token in [16]:
                localctx = SolidityParser.MappingElementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 58
                self.match(SolidityParser.MappingElement)
            elif token in [17]:
                localctx = SolidityParser.AddressLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 59
                self.match(SolidityParser.AddressLiteral)
            elif token in [11]:
                localctx = SolidityParser.IntegerLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 60
                self.match(SolidityParser.INTEGER)
            elif token in [4]:
                localctx = SolidityParser.ParenthesizedArithmeticExpressionContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 61
                self.match(SolidityParser.T__3)
                self.state = 62
                self.arithmeticExpression(0)
                self.state = 63
                self.match(SolidityParser.T__4)
            elif token in [18]:
                localctx = SolidityParser.BlockAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 65
                self.match(SolidityParser.BlockAccess)
            elif token in [19]:
                localctx = SolidityParser.MsgAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 66
                self.match(SolidityParser.MsgAccess)
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    def sempred(self, localctx: RuleContext, ruleIndex: int, predIndex: int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[1] = self.booleanExpression_sempred
        self._predicates[2] = self.arithmeticExpression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def booleanExpression_sempred(self, localctx: BooleanExpressionContext, predIndex: int):
        if predIndex == 0:
            return self.precpred(self._ctx, 6)

        if predIndex == 1:
            return self.precpred(self._ctx, 5)

    def arithmeticExpression_sempred(self, localctx: ArithmeticExpressionContext, predIndex: int):
        if predIndex == 2:
            return self.precpred(self._ctx, 5)

        if predIndex == 3:
            return self.precpred(self._ctx, 4)

        if predIndex == 4:
            return self.precpred(self._ctx, 3)

        if predIndex == 5:
            return self.precpred(self._ctx, 2)
