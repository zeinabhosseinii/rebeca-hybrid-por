package erdg.ast;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.TerminalNode;

import erdg.ast.AnalysisResult.Access;
import erdg.ast.AnalysisResult.MessageServer;
import erdg.ast.AnalysisResult.ReactiveClass;
import erdg.ast.AnalysisResult.RebecInstance;
import erdg.ast.AnalysisResult.Send;
import erdg.grammar.RebecaBaseVisitor;
import erdg.grammar.RebecaParser;

public class RebecaASTAnalyzer extends RebecaBaseVisitor<Void> {
    private final Map<String, Set<String>> stateVarsPerClass   = new LinkedHashMap<>();
    private final Map<String, Set<String>> knownRebecsPerClass = new LinkedHashMap<>();
    private final Map<String, Map<String, MutableMessageServer>> methodsPerClass = new LinkedHashMap<>();
    private final List<RebecInstance> mainInstances = new ArrayList<>();
    private String currentClass  = null;
    private String currentMethod = null;

    // ---- path-condition tracking ----
    private Expr currentCond = Expr.TRUE;
    /** State variables already written on the current path inside the current method. */
    private final Set<String> dirty = new LinkedHashSet<>();
    /** Formal parameters of the current method or constructor. */
    private final Set<String> currentParams = new LinkedHashSet<>();

    private static final class MutableMessageServer {
        Integer priority = null;
        final List<Send>  sends  = new ArrayList<>();
        final Set<String> reads  = new LinkedHashSet<>();
        final Set<String> writes = new LinkedHashSet<>();
        final Set<Access> accesses = new LinkedHashSet<>();
        final List<String> params = new ArrayList<>();          // formal parameter names, in order
    }

    public AnalysisResult analyze(ParseTree tree) {
        visit(tree);
        Map<String, ReactiveClass> classes = new LinkedHashMap<>();
        for (String clsName : stateVarsPerClass.keySet()) {
            Map<String, MessageServer> msMap = new LinkedHashMap<>();
            Map<String, MutableMessageServer> methods = methodsPerClass.get(clsName);
            if (methods != null) {
                for (var entry : methods.entrySet()) {
                    MutableMessageServer m = entry.getValue();
                    msMap.put(entry.getKey(), new MessageServer(entry.getKey(), m.priority,
                            List.copyOf(m.sends), Set.copyOf(m.reads), Set.copyOf(m.writes),
                            List.copyOf(new ArrayList<>(m.accesses)), List.copyOf(m.params)));
                }
            }
            classes.put(clsName, new ReactiveClass(clsName,
                    Set.copyOf(stateVarsPerClass.get(clsName)), msMap));
        }
        return new AnalysisResult(classes, List.copyOf(mainInstances));
    }

    // ------------------------------------------------------------------
    // helpers: method context, access recording, expression conversion
    // ------------------------------------------------------------------

    private void enterMethod(String name, RebecaParser.FormalParamsContext params) {
        currentMethod = name;
        currentCond = Expr.TRUE;
        dirty.clear();
        currentParams.clear();
        MutableMessageServer cur = methodsPerClass.get(currentClass).get(name);
        cur.params.clear();
        if (params != null) {
            for (var p : params.formalParam()) {
                String pn = p.IDENTIFIER().getText();
                currentParams.add(pn);
                cur.params.add(pn);
            }
        }
    }

    private void exitMethod() {
        currentMethod = null;
        currentCond = Expr.TRUE;
        dirty.clear();
        currentParams.clear();
    }

    private void record(Access.Kind kind, String target, String msgsrv, Expr rhs, List<Expr> args) {
        methodsPerClass.get(currentClass).get(currentMethod).accesses
                .add(new Access(kind, target, msgsrv, currentCond, rhs, args));
    }

    /**
     * Expression as seen at method entry. If it mentions a state variable already written
     * on this path, its meaning has changed, so we give up soundly with Unknown.
     */
    private Expr safeExpr(RebecaParser.ExpressionContext ctx) {
        if (ctx == null) return new Expr.Unknown("missing expression");
        Expr e = toExpr(ctx);
        for (String v : Expr.varsOf(e))
            if (dirty.contains(v)) return new Expr.Unknown("uses modified variable " + v);
        return e;
    }

    /** Conservative conversion driven by the grammar's alternative labels. Anything else is Unknown. */
    private Expr toExpr(RebecaParser.ExpressionContext ctx) {
        if (ctx instanceof RebecaParser.LiteralExprContext lit) {
            String t = lit.getText();
            if (t.equals("true"))  return new Expr.Const(Boolean.TRUE);
            if (t.equals("false")) return new Expr.Const(Boolean.FALSE);
            if (t.matches("\\d+")) {
                try { return new Expr.Const(Long.parseLong(t)); }
                catch (NumberFormatException ex) { return new Expr.Unknown("bad number " + t); }
            }
            return new Expr.Unknown("literal " + t);
        }
        if (ctx instanceof RebecaParser.ParenExprContext p) {
            return toExpr(p.expression());
        }
        if (ctx instanceof RebecaParser.CallOrVarExprContext cv) {
            String name = cv.IDENTIFIER().getText();
            if (cv.arguments() != null) return new Expr.Unknown("call " + name);
            if (currentParams.contains(name)) return new Expr.Param(name);
            Set<String> sv = stateVarsPerClass.get(currentClass);
            if (sv != null && sv.contains(name)) return new Expr.Var(name);
            return new Expr.Unknown("unresolved identifier " + name);   // local variable or env constant
        }
        if (ctx instanceof RebecaParser.UnaryExprContext u) {
            String op = u.op.getText();
            if (op.equals("!") || op.equals("-")) return new Expr.Unary(op, toExpr(u.expression()));
            return new Expr.Unknown("unary " + op);
        }
        if (ctx instanceof RebecaParser.AndExprContext a)
            return new Expr.Binary("&&", toExpr(a.expression(0)), toExpr(a.expression(1)));
        if (ctx instanceof RebecaParser.OrExprContext o)
            return new Expr.Binary("||", toExpr(o.expression(0)), toExpr(o.expression(1)));
        if (ctx instanceof RebecaParser.EqExprContext e)
            return new Expr.Binary(e.op.getText(), toExpr(e.expression(0)), toExpr(e.expression(1)));
        if (ctx instanceof RebecaParser.CompareExprContext c)
            return new Expr.Binary(c.op.getText(), toExpr(c.expression(0)), toExpr(c.expression(1)));
        if (ctx instanceof RebecaParser.AddExprContext a)
            return new Expr.Binary(a.op.getText(), toExpr(a.expression(0)), toExpr(a.expression(1)));
        if (ctx instanceof RebecaParser.MulExprContext m)
            return new Expr.Binary(m.op.getText(), toExpr(m.expression(0)), toExpr(m.expression(1)));

        // NondetExpr ?(a, b), TernaryExpr, CastExpr, ArrayExpr, PostfixExpr, calls ...: not modelled
        return new Expr.Unknown("unsupported: " + ctx.getText());
    }

    /** Name of the state variable written by an assignment target (x or x[i]); null otherwise. */
    private String writtenStateVar(RebecaParser.ExpressionContext target) {
        RebecaParser.ExpressionContext e = target;
        while (e instanceof RebecaParser.ArrayExprContext arr) e = arr.expression(0);
        if (e instanceof RebecaParser.CallOrVarExprContext cv && cv.arguments() == null) {
            String name = cv.IDENTIFIER().getText();
            Set<String> sv = stateVarsPerClass.get(currentClass);
            if (sv != null && sv.contains(name)) return name;
        }
        return null;
    }

    // ------------------------------------------------------------------
    // declarations
    // ------------------------------------------------------------------

    @Override
    public Void visitReactiveClassDeclaration(RebecaParser.ReactiveClassDeclarationContext ctx) {
        String className = ctx.IDENTIFIER(0).getText();
        currentClass = className;
        stateVarsPerClass.put(className, new LinkedHashSet<>());
        knownRebecsPerClass.put(className, new LinkedHashSet<>());
        methodsPerClass.put(className, new LinkedHashMap<>());
        visitChildren(ctx);
        currentClass = null;
        return null;
    }

    @Override
    public Void visitKnownRebecsDeclaration(RebecaParser.KnownRebecsDeclarationContext ctx) {
        if (currentClass == null) return null;
        for (var fd : ctx.fieldDeclaration())
            knownRebecsPerClass.get(currentClass).add(fd.IDENTIFIER().getText());
        return null;
    }

    @Override
    public Void visitStateVarsDeclaration(RebecaParser.StateVarsDeclarationContext ctx) {
        if (currentClass == null) return null;
        for (var fd : ctx.fieldDeclaration())
            stateVarsPerClass.get(currentClass).add(fd.IDENTIFIER().getText());
        return null;
    }

    @Override
    public Void visitConstructorDeclaration(RebecaParser.ConstructorDeclarationContext ctx) {
        if (currentClass == null) return null;
        String methodName = ctx.IDENTIFIER().getText();
        MutableMessageServer ms = new MutableMessageServer();
        methodsPerClass.get(currentClass).put(methodName, ms);
        enterMethod(methodName, ctx.formalParams());
        visit(ctx.block());
        exitMethod();
        return null;
    }

    @Override
    public Void visitMsgsrvDeclaration(RebecaParser.MsgsrvDeclarationContext ctx) {
        if (currentClass == null) return null;
        String methodName = ctx.IDENTIFIER().getText();
        MutableMessageServer ms = new MutableMessageServer();
        methodsPerClass.get(currentClass).put(methodName, ms);

        // abstract msgsrv has no block - skip
        if (ctx.block() == null) return null;

        enterMethod(methodName, ctx.formalParams());
        visit(ctx.block());
        exitMethod();
        return null;
    }

    // ------------------------------------------------------------------
    // statements
    // ------------------------------------------------------------------

    @Override
    public Void visitExprStatement(RebecaParser.ExprStatementContext ctx) {
        if (currentClass == null || currentMethod == null) return null;
        processExpression(ctx.expression());
        return null;
    }

    @Override
    public Void visitVarDeclStatement(RebecaParser.VarDeclStatementContext ctx) {
        if (currentClass == null || currentMethod == null) return null;
        String varName = ctx.IDENTIFIER().getText();
        if (ctx.expression() != null) collectReads(ctx.expression());
        if (stateVarsPerClass.get(currentClass).contains(varName)) {
            methodsPerClass.get(currentClass).get(currentMethod).writes.add(varName);
            record(Access.Kind.WRITE, varName, null,
                    ctx.expression() != null ? safeExpr(ctx.expression()) : null, List.of());
            dirty.add(varName);
        }
        return null;
    }

    @Override
    public Void visitIfStatement(RebecaParser.IfStatementContext ctx) {
        if (currentClass == null || currentMethod == null) return null;

        // guard reads happen whenever execution reaches the if: record them under the OUTER condition
        collectReads(ctx.expression());

        Expr g = safeExpr(ctx.expression());
        Expr outer = currentCond;
        Set<String> before = new LinkedHashSet<>(dirty);
        var branches = ctx.statement();      // grammar: 'if' '(' expression ')' statement ('else' statement)?

        // then-branch
        currentCond = Expr.and(outer, g);
        visit(branches.get(0));
        Set<String> afterThen = new LinkedHashSet<>(dirty);

        // else-branch (starts from the state before the if)
        dirty.clear();
        dirty.addAll(before);
        if (branches.size() > 1) {
            currentCond = Expr.and(outer, Expr.not(g));
            visit(branches.get(1));
        }

        // after the if, either branch may have run
        dirty.addAll(afterThen);
        currentCond = outer;
        return null;
    }

    @Override
    public Void visitWhileStatement(RebecaParser.WhileStatementContext ctx) {
        if (currentClass == null || currentMethod == null) return null;
        collectReads(ctx.expression());

        // The loop guard is re-evaluated every iteration, so the body runs under an unknown condition.
        Expr outer = currentCond;
        currentCond = Expr.and(outer, new Expr.Unknown("loop guard"));
        visit(ctx.statement());
        currentCond = outer;
        return null;
    }

    @Override
    public Void visitForStatement(RebecaParser.ForStatementContext ctx) {
        if (currentClass == null || currentMethod == null) return null;
        if (ctx.expression() != null) collectReads(ctx.expression());

        Expr outer = currentCond;
        currentCond = Expr.and(outer, new Expr.Unknown("for loop"));
        visit(ctx.statement());
        currentCond = outer;
        return null;
    }

    // ------------------------------------------------------------------
    // expressions
    // ------------------------------------------------------------------

    private void processExpression(RebecaParser.ExpressionContext ctx) {
        MutableMessageServer ms = methodsPerClass.get(currentClass).get(currentMethod);

        if (ctx instanceof RebecaParser.AssignExprContext assign) {
            RebecaParser.ExpressionContext lhs = assign.expression(0);
            RebecaParser.ExpressionContext rhs = assign.expression(1);
            boolean compound = !assign.op.getText().equals("=");

            collectReads(rhs);
            String var = writtenStateVar(lhs);
            if (var != null) {
                if (lhs instanceof RebecaParser.CallOrVarExprContext) ms.writes.add(var);  // legacy behaviour kept
                if (lhs instanceof RebecaParser.ArrayExprContext) collectReads(lhs, false); // array and index reads (accesses only)
                if (compound) record(Access.Kind.READ, var, null, null, List.of());
                // the right-hand side is evaluated BEFORE the write, so compute it before marking dirty
                Expr rhsExpr = compound ? new Expr.Unknown("compound assignment") : safeExpr(rhs);
                record(Access.Kind.WRITE, var, null, rhsExpr, List.of());
                dirty.add(var);
            }

        } else if (ctx instanceof RebecaParser.UnaryExprContext u
                && (u.op.getText().equals("++") || u.op.getText().equals("--"))) {
            collectReads(ctx);
            String var = writtenStateVar(u.expression());
            if (var != null) {
                record(Access.Kind.WRITE, var, null, new Expr.Unknown("increment/decrement"), List.of());
                dirty.add(var);
            }

        } else if (ctx instanceof RebecaParser.PostfixExprContext p) {
            collectReads(ctx);
            String var = writtenStateVar(p.expression());
            if (var != null) {
                record(Access.Kind.WRITE, var, null, new Expr.Unknown("increment/decrement"), List.of());
                dirty.add(var);
            }

        } else if (ctx instanceof RebecaParser.MemberCallExprContext mc) {
            if (mc.arguments() != null) {
                String methodName = mc.IDENTIFIER().getText();
                String target = resolveReceiver(mc.expression());
                boolean resolved = target != null;
                if (!resolved) target = "?";   // unknown receiver (parameter, sender, ...): kept in 'accesses' only
                if (resolved) ms.sends.add(new Send(target, methodName));   // legacy structure unchanged

                List<Expr> argExprs = new ArrayList<>();
                for (var a : mc.arguments().expression()) {
                    collectReads(a, false);          // accesses only: legacy 'reads' set stays unchanged
                    argExprs.add(safeExpr(a));
                }
                record(Access.Kind.SEND, target, methodName, null, argExprs);
            }
            collectReads(mc.expression());

        } else {
            collectReads(ctx);
        }
    }

    private String resolveReceiver(RebecaParser.ExpressionContext expr) {
        if (expr instanceof RebecaParser.SelfExprContext) return "self";
        if (expr instanceof RebecaParser.CallOrVarExprContext cv) {
            String name = cv.IDENTIFIER().getText();
            Set<String> known = knownRebecsPerClass.getOrDefault(currentClass, Set.of());
            if (known.contains(name)) return name;
        }
        return null;
    }

    private void collectReads(RebecaParser.ExpressionContext ctx) {
        collectReads(ctx, true);
    }

    /**
     * @param legacy if true, also updates the old 'reads' set used by the existing analysis;
     *               if false, only records the READ access (new structure).
     */
    private void collectReads(RebecaParser.ExpressionContext ctx, boolean legacy) {
        if (ctx == null || currentClass == null || currentMethod == null) return;
        if (ctx instanceof RebecaParser.CallOrVarExprContext cv) {
            String name = cv.IDENTIFIER().getText();
            Set<String> stateVars = stateVarsPerClass.get(currentClass);
            if (stateVars != null && stateVars.contains(name)) {
                if (legacy) methodsPerClass.get(currentClass).get(currentMethod).reads.add(name);
                record(Access.Kind.READ, name, null, null, List.of());
            }
        }
        for (int i = 0; i < ctx.getChildCount(); i++) {
            ParseTree child = ctx.getChild(i);
            if (child instanceof RebecaParser.ExpressionContext ec) collectReads(ec, legacy);
        }
    }

    // ------------------------------------------------------------------
    // main block
    // ------------------------------------------------------------------

    @Override
    public Void visitMainRebecDefinition(RebecaParser.MainRebecDefinitionContext ctx) {
        String reactiveClass = ctx.type().getText();
        String instanceName  = ctx.IDENTIFIER().getText();
        Map<String, String> bindings = new LinkedHashMap<>();
        if (ctx.bindingList() != null) {
            List<String> boundNames = new ArrayList<>();
            for (TerminalNode id : ctx.bindingList().IDENTIFIER()) boundNames.add(id.getText());
            List<String> knownAliases = new ArrayList<>(
                    knownRebecsPerClass.getOrDefault(reactiveClass, new LinkedHashSet<>()));
            for (int i = 0; i < Math.min(knownAliases.size(), boundNames.size()); i++)
                bindings.put(knownAliases.get(i), boundNames.get(i));
        }

        // constructor arguments given in main, e.g. (1) in  Worker w(cell):(1);
        List<Expr> ctorArgs = new ArrayList<>();
        if (ctx.argList() != null)
            for (var item : ctx.argList().argItem())
                ctorArgs.add(toExpr(item.expression()));

        mainInstances.add(new RebecInstance(instanceName, reactiveClass, bindings, null, ctorArgs));
        return null;
    }

    // ------------------------------------------------------------------
    // debug output: called from Main when CONDITIONAL_DEBUG is true
    // ------------------------------------------------------------------

    public static void dumpAccesses(AnalysisResult result) {
        System.out.println("=== Access dump (path conditions) ===");
        for (var cls : result.classes().values()) {
            for (var ms : cls.messageServers().values()) {
                System.out.println(cls.name() + "." + ms.name() + ":");
                for (Access a : ms.accesses()) {
                    StringBuilder sb = new StringBuilder("  ");
                    sb.append(a.kind()).append(' ').append(a.target());
                    if (a.msgsrv() != null) {
                        sb.append('.').append(a.msgsrv()).append('(');
                        for (int i = 0; i < a.args().size(); i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(Expr.show(a.args().get(i)));
                        }
                        sb.append(')');
                    }
                    if (a.rhs() != null) sb.append("  rhs=").append(Expr.show(a.rhs()));
                    sb.append("  cond=").append(Expr.show(a.cond()));
                    System.out.println(sb);
                }
            }
        }
    }
}