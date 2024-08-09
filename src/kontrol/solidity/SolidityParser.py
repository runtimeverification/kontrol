# Generated from src/kontrol/solidity/Solidity.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,25,90,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,1,0,1,
        0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,1,27,8,1,1,1,
        1,1,1,1,1,1,1,1,1,1,5,1,35,8,1,10,1,12,1,38,9,1,1,2,1,2,1,2,1,2,
        1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,5,2,58,8,
        2,10,2,12,2,61,9,2,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,
        3,1,3,1,3,3,3,77,8,3,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,1,5,1,5,
        1,5,0,2,2,4,6,0,2,4,6,8,10,0,1,1,0,15,17,103,0,12,1,0,0,0,2,26,1,
        0,0,0,4,39,1,0,0,0,6,76,1,0,0,0,8,78,1,0,0,0,10,82,1,0,0,0,12,13,
        3,2,1,0,13,1,1,0,0,0,14,15,6,1,-1,0,15,16,5,3,0,0,16,27,3,2,1,4,
        17,18,3,4,2,0,18,19,5,24,0,0,19,20,3,4,2,0,20,27,1,0,0,0,21,27,5,
        14,0,0,22,23,5,4,0,0,23,24,3,2,1,0,24,25,5,5,0,0,25,27,1,0,0,0,26,
        14,1,0,0,0,26,17,1,0,0,0,26,21,1,0,0,0,26,22,1,0,0,0,27,36,1,0,0,
        0,28,29,10,6,0,0,29,30,5,1,0,0,30,35,3,2,1,7,31,32,10,5,0,0,32,33,
        5,2,0,0,33,35,3,2,1,6,34,28,1,0,0,0,34,31,1,0,0,0,35,38,1,0,0,0,
        36,34,1,0,0,0,36,37,1,0,0,0,37,3,1,0,0,0,38,36,1,0,0,0,39,40,6,2,
        -1,0,40,41,3,6,3,0,41,59,1,0,0,0,42,43,10,6,0,0,43,44,5,6,0,0,44,
        58,3,4,2,7,45,46,10,5,0,0,46,47,5,7,0,0,47,58,3,4,2,6,48,49,10,4,
        0,0,49,50,5,8,0,0,50,58,3,4,2,5,51,52,10,3,0,0,52,53,5,9,0,0,53,
        58,3,4,2,4,54,55,10,2,0,0,55,56,5,10,0,0,56,58,3,4,2,3,57,42,1,0,
        0,0,57,45,1,0,0,0,57,48,1,0,0,0,57,51,1,0,0,0,57,54,1,0,0,0,58,61,
        1,0,0,0,59,57,1,0,0,0,59,60,1,0,0,0,60,5,1,0,0,0,61,59,1,0,0,0,62,
        77,5,17,0,0,63,77,5,18,0,0,64,77,5,19,0,0,65,77,5,20,0,0,66,77,5,
        21,0,0,67,77,5,15,0,0,68,69,5,4,0,0,69,70,3,4,2,0,70,71,5,5,0,0,
        71,77,1,0,0,0,72,77,5,22,0,0,73,77,5,23,0,0,74,77,3,8,4,0,75,77,
        3,10,5,0,76,62,1,0,0,0,76,63,1,0,0,0,76,64,1,0,0,0,76,65,1,0,0,0,
        76,66,1,0,0,0,76,67,1,0,0,0,76,68,1,0,0,0,76,72,1,0,0,0,76,73,1,
        0,0,0,76,74,1,0,0,0,76,75,1,0,0,0,77,7,1,0,0,0,78,79,5,17,0,0,79,
        80,5,11,0,0,80,81,5,17,0,0,81,9,1,0,0,0,82,83,5,17,0,0,83,84,5,11,
        0,0,84,85,5,17,0,0,85,86,5,12,0,0,86,87,7,0,0,0,87,88,5,13,0,0,88,
        11,1,0,0,0,6,26,34,36,57,59,76
    ]

class SolidityParser ( Parser ):

    grammarFileName = "Solidity.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'&&'", "'||'", "'!'", "'('", "')'", "'+'", 
                     "'-'", "'*'", "'/'", "'**'", "'.'", "'['", "']'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "BOOLEAN_LITERAL", "INTEGER", 
                      "ADDRESS", "VariableName", "LengthAccess", "ArrayElement", 
                      "MappingElement", "AddressLiteral", "BlockAccess", 
                      "MsgAccess", "RelOp", "WS" ]

    RULE_expression = 0
    RULE_booleanExpression = 1
    RULE_arithmeticExpression = 2
    RULE_atom = 3
    RULE_contractVariableAccessExpr = 4
    RULE_contractVariableArrayElemExpr = 5

    ruleNames =  [ "expression", "booleanExpression", "arithmeticExpression", 
                   "atom", "contractVariableAccessExpr", "contractVariableArrayElemExpr" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    BOOLEAN_LITERAL=14
    INTEGER=15
    ADDRESS=16
    VariableName=17
    LengthAccess=18
    ArrayElement=19
    MappingElement=20
    AddressLiteral=21
    BlockAccess=22
    MsgAccess=23
    RelOp=24
    WS=25

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext,0)


        def getRuleIndex(self):
            return SolidityParser.RULE_expression

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpression" ):
                listener.enterExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpression" ):
                listener.exitExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpression" ):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)




    def expression(self):

        localctx = SolidityParser.ExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 12
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

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SolidityParser.RULE_booleanExpression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class RelationalExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)

        def RelOp(self):
            return self.getToken(SolidityParser.RelOp, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelationalExpression" ):
                listener.enterRelationalExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelationalExpression" ):
                listener.exitRelationalExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelationalExpression" ):
                return visitor.visitRelationalExpression(self)
            else:
                return visitor.visitChildren(self)


    class AndExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.BooleanExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAndExpression" ):
                listener.enterAndExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAndExpression" ):
                listener.exitAndExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExpression" ):
                return visitor.visitAndExpression(self)
            else:
                return visitor.visitChildren(self)


    class BooleanLiteralContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BOOLEAN_LITERAL(self):
            return self.getToken(SolidityParser.BOOLEAN_LITERAL, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanLiteral" ):
                listener.enterBooleanLiteral(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanLiteral" ):
                listener.exitBooleanLiteral(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanLiteral" ):
                return visitor.visitBooleanLiteral(self)
            else:
                return visitor.visitChildren(self)


    class NotExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNotExpression" ):
                listener.enterNotExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNotExpression" ):
                listener.exitNotExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotExpression" ):
                return visitor.visitNotExpression(self)
            else:
                return visitor.visitChildren(self)


    class OrExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.BooleanExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOrExpression" ):
                listener.enterOrExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOrExpression" ):
                listener.exitOrExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExpression" ):
                return visitor.visitOrExpression(self)
            else:
                return visitor.visitChildren(self)


    class ParenthesizedBooleanExpressionContext(BooleanExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.BooleanExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpression(self):
            return self.getTypedRuleContext(SolidityParser.BooleanExpressionContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParenthesizedBooleanExpression" ):
                listener.enterParenthesizedBooleanExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParenthesizedBooleanExpression" ):
                listener.exitParenthesizedBooleanExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenthesizedBooleanExpression" ):
                return visitor.visitParenthesizedBooleanExpression(self)
            else:
                return visitor.visitChildren(self)



    def booleanExpression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SolidityParser.BooleanExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 2
        self.enterRecursionRule(localctx, 2, self.RULE_booleanExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 26
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,0,self._ctx)
            if la_ == 1:
                localctx = SolidityParser.NotExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 15
                self.match(SolidityParser.T__2)
                self.state = 16
                self.booleanExpression(4)
                pass

            elif la_ == 2:
                localctx = SolidityParser.RelationalExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 17
                self.arithmeticExpression(0)
                self.state = 18
                self.match(SolidityParser.RelOp)
                self.state = 19
                self.arithmeticExpression(0)
                pass

            elif la_ == 3:
                localctx = SolidityParser.BooleanLiteralContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 21
                self.match(SolidityParser.BOOLEAN_LITERAL)
                pass

            elif la_ == 4:
                localctx = SolidityParser.ParenthesizedBooleanExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 22
                self.match(SolidityParser.T__3)
                self.state = 23
                self.booleanExpression(0)
                self.state = 24
                self.match(SolidityParser.T__4)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 36
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 34
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
                    if la_ == 1:
                        localctx = SolidityParser.AndExpressionContext(self, SolidityParser.BooleanExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_booleanExpression)
                        self.state = 28
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 29
                        self.match(SolidityParser.T__0)
                        self.state = 30
                        self.booleanExpression(7)
                        pass

                    elif la_ == 2:
                        localctx = SolidityParser.OrExpressionContext(self, SolidityParser.BooleanExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_booleanExpression)
                        self.state = 31
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 32
                        self.match(SolidityParser.T__1)
                        self.state = 33
                        self.booleanExpression(6)
                        pass

             
                self.state = 38
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ArithmeticExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SolidityParser.RULE_arithmeticExpression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class SubtractExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSubtractExpression" ):
                listener.enterSubtractExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSubtractExpression" ):
                listener.exitSubtractExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubtractExpression" ):
                return visitor.visitSubtractExpression(self)
            else:
                return visitor.visitChildren(self)


    class DivideExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDivideExpression" ):
                listener.enterDivideExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDivideExpression" ):
                listener.exitDivideExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDivideExpression" ):
                return visitor.visitDivideExpression(self)
            else:
                return visitor.visitChildren(self)


    class AddExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAddExpression" ):
                listener.enterAddExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAddExpression" ):
                listener.exitAddExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddExpression" ):
                return visitor.visitAddExpression(self)
            else:
                return visitor.visitChildren(self)


    class PowExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPowExpression" ):
                listener.enterPowExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPowExpression" ):
                listener.exitPowExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPowExpression" ):
                return visitor.visitPowExpression(self)
            else:
                return visitor.visitChildren(self)


    class MultiplyExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SolidityParser.ArithmeticExpressionContext)
            else:
                return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,i)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMultiplyExpression" ):
                listener.enterMultiplyExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMultiplyExpression" ):
                listener.exitMultiplyExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplyExpression" ):
                return visitor.visitMultiplyExpression(self)
            else:
                return visitor.visitChildren(self)


    class AtomExpressionContext(ArithmeticExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.ArithmeticExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(SolidityParser.AtomContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAtomExpression" ):
                listener.enterAtomExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAtomExpression" ):
                listener.exitAtomExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtomExpression" ):
                return visitor.visitAtomExpression(self)
            else:
                return visitor.visitChildren(self)



    def arithmeticExpression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SolidityParser.ArithmeticExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 4
        self.enterRecursionRule(localctx, 4, self.RULE_arithmeticExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            localctx = SolidityParser.AtomExpressionContext(self, localctx)
            self._ctx = localctx
            _prevctx = localctx

            self.state = 40
            self.atom()
            self._ctx.stop = self._input.LT(-1)
            self.state = 59
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 57
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                    if la_ == 1:
                        localctx = SolidityParser.AddExpressionContext(self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 42
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 43
                        self.match(SolidityParser.T__5)
                        self.state = 44
                        self.arithmeticExpression(7)
                        pass

                    elif la_ == 2:
                        localctx = SolidityParser.SubtractExpressionContext(self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 45
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 46
                        self.match(SolidityParser.T__6)
                        self.state = 47
                        self.arithmeticExpression(6)
                        pass

                    elif la_ == 3:
                        localctx = SolidityParser.MultiplyExpressionContext(self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 48
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 49
                        self.match(SolidityParser.T__7)
                        self.state = 50
                        self.arithmeticExpression(5)
                        pass

                    elif la_ == 4:
                        localctx = SolidityParser.DivideExpressionContext(self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 51
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 52
                        self.match(SolidityParser.T__8)
                        self.state = 53
                        self.arithmeticExpression(4)
                        pass

                    elif la_ == 5:
                        localctx = SolidityParser.PowExpressionContext(self, SolidityParser.ArithmeticExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmeticExpression)
                        self.state = 54
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 55
                        self.match(SolidityParser.T__9)
                        self.state = 56
                        self.arithmeticExpression(3)
                        pass

             
                self.state = 61
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SolidityParser.RULE_atom

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class ParenthesizedArithmeticExpressionContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def arithmeticExpression(self):
            return self.getTypedRuleContext(SolidityParser.ArithmeticExpressionContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParenthesizedArithmeticExpression" ):
                listener.enterParenthesizedArithmeticExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParenthesizedArithmeticExpression" ):
                listener.exitParenthesizedArithmeticExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenthesizedArithmeticExpression" ):
                return visitor.visitParenthesizedArithmeticExpression(self)
            else:
                return visitor.visitChildren(self)


    class LengthAccessContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LengthAccess(self):
            return self.getToken(SolidityParser.LengthAccess, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLengthAccess" ):
                listener.enterLengthAccess(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLengthAccess" ):
                listener.exitLengthAccess(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLengthAccess" ):
                return visitor.visitLengthAccess(self)
            else:
                return visitor.visitChildren(self)


    class ContractVariableAccessContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def contractVariableAccessExpr(self):
            return self.getTypedRuleContext(SolidityParser.ContractVariableAccessExprContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterContractVariableAccess" ):
                listener.enterContractVariableAccess(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitContractVariableAccess" ):
                listener.exitContractVariableAccess(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitContractVariableAccess" ):
                return visitor.visitContractVariableAccess(self)
            else:
                return visitor.visitChildren(self)


    class VariableContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VariableName(self):
            return self.getToken(SolidityParser.VariableName, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVariable" ):
                listener.enterVariable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVariable" ):
                listener.exitVariable(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariable" ):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)


    class MappingElementContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MappingElement(self):
            return self.getToken(SolidityParser.MappingElement, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMappingElement" ):
                listener.enterMappingElement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMappingElement" ):
                listener.exitMappingElement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMappingElement" ):
                return visitor.visitMappingElement(self)
            else:
                return visitor.visitChildren(self)


    class BlockAccessContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BlockAccess(self):
            return self.getToken(SolidityParser.BlockAccess, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBlockAccess" ):
                listener.enterBlockAccess(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBlockAccess" ):
                listener.exitBlockAccess(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlockAccess" ):
                return visitor.visitBlockAccess(self)
            else:
                return visitor.visitChildren(self)


    class AddressLiteralContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def AddressLiteral(self):
            return self.getToken(SolidityParser.AddressLiteral, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAddressLiteral" ):
                listener.enterAddressLiteral(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAddressLiteral" ):
                listener.exitAddressLiteral(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddressLiteral" ):
                return visitor.visitAddressLiteral(self)
            else:
                return visitor.visitChildren(self)


    class ContractVariableArrayElementContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def contractVariableArrayElemExpr(self):
            return self.getTypedRuleContext(SolidityParser.ContractVariableArrayElemExprContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterContractVariableArrayElement" ):
                listener.enterContractVariableArrayElement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitContractVariableArrayElement" ):
                listener.exitContractVariableArrayElement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitContractVariableArrayElement" ):
                return visitor.visitContractVariableArrayElement(self)
            else:
                return visitor.visitChildren(self)


    class ArrayElementContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ArrayElement(self):
            return self.getToken(SolidityParser.ArrayElement, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArrayElement" ):
                listener.enterArrayElement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArrayElement" ):
                listener.exitArrayElement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayElement" ):
                return visitor.visitArrayElement(self)
            else:
                return visitor.visitChildren(self)


    class IntegerLiteralContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INTEGER(self):
            return self.getToken(SolidityParser.INTEGER, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIntegerLiteral" ):
                listener.enterIntegerLiteral(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIntegerLiteral" ):
                listener.exitIntegerLiteral(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerLiteral" ):
                return visitor.visitIntegerLiteral(self)
            else:
                return visitor.visitChildren(self)


    class MsgAccessContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SolidityParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MsgAccess(self):
            return self.getToken(SolidityParser.MsgAccess, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMsgAccess" ):
                listener.enterMsgAccess(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMsgAccess" ):
                listener.exitMsgAccess(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMsgAccess" ):
                return visitor.visitMsgAccess(self)
            else:
                return visitor.visitChildren(self)



    def atom(self):

        localctx = SolidityParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_atom)
        try:
            self.state = 76
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                localctx = SolidityParser.VariableContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 62
                self.match(SolidityParser.VariableName)
                pass

            elif la_ == 2:
                localctx = SolidityParser.LengthAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 63
                self.match(SolidityParser.LengthAccess)
                pass

            elif la_ == 3:
                localctx = SolidityParser.ArrayElementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 64
                self.match(SolidityParser.ArrayElement)
                pass

            elif la_ == 4:
                localctx = SolidityParser.MappingElementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 65
                self.match(SolidityParser.MappingElement)
                pass

            elif la_ == 5:
                localctx = SolidityParser.AddressLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 66
                self.match(SolidityParser.AddressLiteral)
                pass

            elif la_ == 6:
                localctx = SolidityParser.IntegerLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 67
                self.match(SolidityParser.INTEGER)
                pass

            elif la_ == 7:
                localctx = SolidityParser.ParenthesizedArithmeticExpressionContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 68
                self.match(SolidityParser.T__3)
                self.state = 69
                self.arithmeticExpression(0)
                self.state = 70
                self.match(SolidityParser.T__4)
                pass

            elif la_ == 8:
                localctx = SolidityParser.BlockAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 72
                self.match(SolidityParser.BlockAccess)
                pass

            elif la_ == 9:
                localctx = SolidityParser.MsgAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 73
                self.match(SolidityParser.MsgAccess)
                pass

            elif la_ == 10:
                localctx = SolidityParser.ContractVariableAccessContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 74
                self.contractVariableAccessExpr()
                pass

            elif la_ == 11:
                localctx = SolidityParser.ContractVariableArrayElementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 75
                self.contractVariableArrayElemExpr()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ContractVariableAccessExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def VariableName(self, i:int=None):
            if i is None:
                return self.getTokens(SolidityParser.VariableName)
            else:
                return self.getToken(SolidityParser.VariableName, i)

        def getRuleIndex(self):
            return SolidityParser.RULE_contractVariableAccessExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterContractVariableAccessExpr" ):
                listener.enterContractVariableAccessExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitContractVariableAccessExpr" ):
                listener.exitContractVariableAccessExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitContractVariableAccessExpr" ):
                return visitor.visitContractVariableAccessExpr(self)
            else:
                return visitor.visitChildren(self)




    def contractVariableAccessExpr(self):

        localctx = SolidityParser.ContractVariableAccessExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_contractVariableAccessExpr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 78
            self.match(SolidityParser.VariableName)
            self.state = 79
            self.match(SolidityParser.T__10)
            self.state = 80
            self.match(SolidityParser.VariableName)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ContractVariableArrayElemExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def VariableName(self, i:int=None):
            if i is None:
                return self.getTokens(SolidityParser.VariableName)
            else:
                return self.getToken(SolidityParser.VariableName, i)

        def INTEGER(self):
            return self.getToken(SolidityParser.INTEGER, 0)

        def ADDRESS(self):
            return self.getToken(SolidityParser.ADDRESS, 0)

        def getRuleIndex(self):
            return SolidityParser.RULE_contractVariableArrayElemExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterContractVariableArrayElemExpr" ):
                listener.enterContractVariableArrayElemExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitContractVariableArrayElemExpr" ):
                listener.exitContractVariableArrayElemExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitContractVariableArrayElemExpr" ):
                return visitor.visitContractVariableArrayElemExpr(self)
            else:
                return visitor.visitChildren(self)




    def contractVariableArrayElemExpr(self):

        localctx = SolidityParser.ContractVariableArrayElemExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_contractVariableArrayElemExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 82
            self.match(SolidityParser.VariableName)
            self.state = 83
            self.match(SolidityParser.T__10)
            self.state = 84
            self.match(SolidityParser.VariableName)
            self.state = 85
            self.match(SolidityParser.T__11)
            self.state = 86
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 229376) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 87
            self.match(SolidityParser.T__12)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[1] = self.booleanExpression_sempred
        self._predicates[2] = self.arithmeticExpression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def booleanExpression_sempred(self, localctx:BooleanExpressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 5)
         

    def arithmeticExpression_sempred(self, localctx:ArithmeticExpressionContext, predIndex:int):
            if predIndex == 2:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 5)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 2)
         




