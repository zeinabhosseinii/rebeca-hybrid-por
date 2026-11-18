package erdg.analysis;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import erdg.ast.AnalysisResult;
import erdg.ast.AnalysisResult.Access;
import erdg.ast.AnalysisResult.MessageServer;
import erdg.ast.AnalysisResult.ReactiveClass;
import erdg.ast.AnalysisResult.RebecInstance;
import erdg.ast.Expr;

/**
 * Instance-level guard analysis (offline, read-only: it changes no priorities).
 *
 * For every rebec instance it computes (by fixpoint):
 *   - which message servers are reachable,
 *   - an over-approximation of the values each state variable can take,
 *   - the class of every path condition: ALWAYS / NEVER / COND.
 *
 * Soundness: every approximation only ever enlarges a set of values, so a condition may be
 * classified COND although it is really ALWAYS or NEVER, but never the other way round.
 */
public class GuardAnalysis {

    public enum Cls { ALWAYS, NEVER, COND }

    private static final int CAP = 16;          // widening: a value set larger than this becomes ANY

    private record Node(String inst, String ms) {}

    /** Abstract set of values. top = "any value". */
    private static final class Vals {
        boolean top;
        final Set<Object> set = new LinkedHashSet<>();

        static Vals top() { Vals v = new Vals(); v.top = true; return v; }
        static Vals of(Object o) { Vals v = new Vals(); v.set.add(o); return v; }

        boolean isEmpty() { return !top && set.isEmpty(); }

        Vals copy() { Vals v = new Vals(); v.top = top; v.set.addAll(set); return v; }

        /** @return true if this set changed */
        boolean addAll(Vals o) {
            if (top) return false;
            if (o.top) { top = true; set.clear(); return true; }
            boolean ch = set.addAll(o.set);
            if (set.size() > CAP) { top = true; set.clear(); return true; }
            return ch;
        }
    }

    private final AnalysisResult result;
    private final Map<String, RebecInstance> insts = new LinkedHashMap<>();
    private final Map<String, Vals> vs  = new LinkedHashMap<>();   // "inst.var"        -> possible values
    private final Map<String, Vals> pvs = new LinkedHashMap<>();   // "inst.ms#index"   -> possible parameter values
    private final Set<Node> reach = new LinkedHashSet<>();

    public GuardAnalysis(AnalysisResult result) {
        this.result = result;
    }

    // ------------------------------------------------------------------
    // fixpoint
    // ------------------------------------------------------------------

    public void run() {
        init();
        boolean changed = true;
        int rounds = 0;
        while (changed && rounds++ < 1000) {
            changed = false;
            for (Node n : new ArrayList<>(reach)) changed |= step(n);
        }
    }

    private void init() {
        for (RebecInstance ri : result.mainInstances()) {
            insts.put(ri.name(), ri);
            ReactiveClass rc = result.classes().get(ri.reactiveClass());
            if (rc == null) continue;
            MessageServer ctor = rc.messageServers().get(rc.name());

            // A state variable the constructor does not assign unconditionally starts as ANY
            // (default value of unknown type); otherwise the constructor's writes define it.
            for (String v : rc.stateVars()) {
                boolean assigned = false;
                if (ctor != null)
                    for (Access a : ctor.accesses())
                        if (a.kind() == Access.Kind.WRITE && a.target().equals(v) && Expr.isTrue(a.cond()))
                            assigned = true;
                vs.put(ri.name() + "." + v, assigned ? new Vals() : Vals.top());
            }

            if (ctor != null) {
                reach.add(new Node(ri.name(), rc.name()));
                List<Expr> args = ri.ctorArgs();
                for (int i = 0; i < args.size(); i++)
                    pv(ri.name(), rc.name(), i).addAll(eval(args.get(i), null, null));
            }
        }
    }

    private boolean step(Node n) {
        RebecInstance ri = insts.get(n.inst());
        MessageServer ms = msOf(n);
        boolean changed = false;
        for (Access a : ms.accesses()) {
            if (classify(a.cond(), n.inst(), ms) == Cls.NEVER) continue;   // this access never happens
            if (a.kind() == Access.Kind.WRITE) {
                Vals v = (a.rhs() == null) ? Vals.top() : eval(a.rhs(), n.inst(), ms);
                changed |= var(n.inst(), a.target()).addAll(v);
            } else if (a.kind() == Access.Kind.SEND) {
                changed |= send(ri, ms, a);
            }
        }
        return changed;
    }

    private boolean send(RebecInstance ri, MessageServer ms, Access a) {
        boolean changed = false;
        for (String t : targets(ri, a.target(), a.msgsrv())) {
            RebecInstance tr = insts.get(t);
            ReactiveClass tc = result.classes().get(tr.reactiveClass());
            if (tc == null || !tc.messageServers().containsKey(a.msgsrv())) continue;
            changed |= reach.add(new Node(t, a.msgsrv()));
            for (int i = 0; i < a.args().size(); i++)
                changed |= pv(t, a.msgsrv(), i).addAll(eval(a.args().get(i), ri.name(), ms));
        }
        return changed;
    }

    /** Instances that may receive the message. Unresolvable receivers: every instance having such a message server. */
    private List<String> targets(RebecInstance ri, String target, String msgsrv) {
        if (target.equals("self")) return List.of(ri.name());
        if (!target.equals("?")) {
            String b = ri.knownRebecBindings().get(target);
            if (b != null && insts.containsKey(b)) return List.of(b);
        }
        List<String> out = new ArrayList<>();
        for (RebecInstance o : result.mainInstances()) {
            ReactiveClass c = result.classes().get(o.reactiveClass());
            if (c != null && c.messageServers().containsKey(msgsrv)) out.add(o.name());
        }
        return out;
    }

    // ------------------------------------------------------------------
    // classification and evaluation
    // ------------------------------------------------------------------

    /** Class of a path condition for a given instance, using the current value sets. */
    public Cls classify(Expr cond, String inst, MessageServer ms) {
        if (Expr.isTrue(cond)) return Cls.ALWAYS;
        Vals v = eval(cond, inst, ms);
        if (v.top || v.isEmpty()) return Cls.COND;
        for (Object o : v.set) if (!(o instanceof Boolean)) return Cls.COND;
        boolean t = v.set.contains(Boolean.TRUE);
        boolean f = v.set.contains(Boolean.FALSE);
        if (t && !f) return Cls.ALWAYS;
        if (!t) return Cls.NEVER;
        return Cls.COND;
    }

    private Vals eval(Expr e, String inst, MessageServer ms) {
        if (e instanceof Expr.Const c) return Vals.of(c.value());

        if (e instanceof Expr.Var var) {
            if (inst == null) return Vals.top();
            Vals x = vs.get(inst + "." + var.name());
            return (x == null || x.isEmpty()) ? Vals.top() : x.copy();
        }

        if (e instanceof Expr.Param p) {
            if (inst == null || ms == null) return Vals.top();
            int idx = ms.params().indexOf(p.name());
            if (idx < 0) return Vals.top();
            Vals x = pvs.get(pkey(inst, ms.name(), idx));
            return (x == null || x.isEmpty()) ? Vals.top() : x.copy();
        }

        if (e instanceof Expr.Unary u) {
            Vals a = eval(u.e(), inst, ms);
            if (a.top) return Vals.top();
            Vals r = new Vals();
            for (Object x : a.set) {
                Object y = unary(u.op(), x);
                if (y == null) return Vals.top();
                r.set.add(y);
            }
            return r;
        }

        if (e instanceof Expr.Binary b) {
            Vals l = eval(b.l(), inst, ms);
            Vals r = eval(b.r(), inst, ms);
            if (l.top || r.top) return Vals.top();
            Vals out = new Vals();
            for (Object x : l.set)
                for (Object y : r.set) {
                    Object z = binary(b.op(), x, y);
                    if (z == null) return Vals.top();
                    out.set.add(z);
                }
            if (out.set.size() > CAP) return Vals.top();
            return out;
        }

        return Vals.top();      // Expr.Unknown and anything else
    }

    private static Object unary(String op, Object x) {
        if (op.equals("!") && x instanceof Boolean bx) return !bx;
        if (op.equals("-") && x instanceof Long lx) return -lx;
        return null;
    }

    private static Object binary(String op, Object x, Object y) {
        if (x instanceof Boolean ba && y instanceof Boolean bb) {
            if (op.equals("&&")) return ba && bb;
            if (op.equals("||")) return ba || bb;
        }
        if (op.equals("==")) return x.equals(y);
        if (op.equals("!=")) return !x.equals(y);
        if (x instanceof Long la && y instanceof Long lb) {
            switch (op) {
                case "<":  return la < lb;
                case "<=": return la <= lb;
                case ">":  return la > lb;
                case ">=": return la >= lb;
                case "+":  return la + lb;
                case "-":  return la - lb;
                case "*":  return la * lb;
                case "/":  return lb == 0 ? null : (Object) (la / lb);
                case "%":  return lb == 0 ? null : (Object) (la % lb);
                default:   return null;
            }
        }
        return null;
    }

    // ------------------------------------------------------------------
    // small helpers
    // ------------------------------------------------------------------

    private Vals var(String inst, String name) {
        return vs.computeIfAbsent(inst + "." + name, k -> Vals.top());
    }

    private Vals pv(String inst, String ms, int idx) {
        return pvs.computeIfAbsent(pkey(inst, ms, idx), k -> new Vals());
    }

    private static String pkey(String inst, String ms, int idx) {
        return inst + "." + ms + "#" + idx;
    }

    private MessageServer msOf(Node n) {
        return result.classes().get(insts.get(n.inst()).reactiveClass()).messageServers().get(n.ms());
    }

    private static String show(Vals v) {
        return v.top ? "ANY" : v.set.toString();
    }

    private static String describe(Access a) {
        StringBuilder sb = new StringBuilder(a.kind().toString()).append(' ').append(a.target());
        if (a.msgsrv() != null) {
            sb.append('.').append(a.msgsrv()).append('(');
            for (int i = 0; i < a.args().size(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(Expr.show(a.args().get(i)));
            }
            sb.append(')');
        }
        return sb.toString();
    }

        // ------------------------------------------------------------------
    // queries used by SDIAnalyzer / SVIAnalyzer when pruning is enabled
    // ------------------------------------------------------------------

    public boolean knows(String inst, String ms) {
        RebecInstance ri = insts.get(inst);
        if (ri == null) return false;
        ReactiveClass rc = result.classes().get(ri.reactiveClass());
        return rc != null && rc.messageServers().containsKey(ms);
    }

    public boolean isReachable(String inst, String ms) {
        return reach.contains(new Node(inst, ms));
    }

    /** Can this send (sender instance and message server, to a target instance and message) really happen? */
    public boolean sendMayHappen(String senderInst, String senderMs, String targetInst, String message) {
        if (!knows(senderInst, senderMs)) return true;          // no information: keep the dependency
        if (!isReachable(senderInst, senderMs)) return false;
        RebecInstance ri = insts.get(senderInst);
        MessageServer ms = msOf(new Node(senderInst, senderMs));
        for (Access a : ms.accesses()) {
            if (a.kind() != Access.Kind.SEND || !message.equals(a.msgsrv())) continue;
            if (classify(a.cond(), senderInst, ms) == Cls.NEVER) continue;
            if (targets(ri, a.target(), a.msgsrv()).contains(targetInst)) return true;
        }
        return false;
    }

    /** State variables this message server can really write in this instance. */
    public Set<String> effectiveWrites(String inst, String ms) {
        return effectiveVars(inst, ms, Access.Kind.WRITE);
    }

    /** State variables this message server can really read in this instance. */
    public Set<String> effectiveReads(String inst, String ms) {
        return effectiveVars(inst, ms, Access.Kind.READ);
    }

    private Set<String> effectiveVars(String inst, String ms, Access.Kind kind) {
        Set<String> out = new LinkedHashSet<>();
        if (!isReachable(inst, ms)) return out;
        MessageServer m = msOf(new Node(inst, ms));
        for (Access a : m.accesses())
            if (a.kind() == kind && classify(a.cond(), inst, m) != Cls.NEVER) out.add(a.target());
        return out;
    }

    // ------------------------------------------------------------------
    // export API (used by FlipperAnalysis and JsonExporter). Read-only.
    // PASTE this block inside class GuardAnalysis, e.g. right before the "// report" section.
    // No new imports are needed (List, ArrayList, Access, MessageServer, ReactiveClass, Expr already imported).
    // ------------------------------------------------------------------

    public List<String> instanceNames() {
        return new ArrayList<>(insts.keySet());
    }

    public ReactiveClass classOfInstance(String inst) {
        RebecInstance ri = insts.get(inst);
        return ri == null ? null : result.classes().get(ri.reactiveClass());
    }

    public MessageServer messageServer(String inst, String ms) {
        ReactiveClass rc = classOfInstance(inst);
        return rc == null ? null : rc.messageServers().get(ms);
    }

    /** Class of an access of message server 'ms' in instance 'inst'. */
    public Cls classifyAccess(Access a, String inst, String ms) {
        return classify(a.cond(), inst, messageServer(inst, ms));
    }

    /** Possible values of a state variable, or null if ANY. */
    public List<Object> possibleValues(String inst, String var) {
        Vals v = vs.get(inst + "." + var);
        if (v == null || v.top) return null;
        return new ArrayList<>(v.set);
    }

    /** Possible values of an expression evaluated in (inst, ms), or null if ANY. */
    public List<Object> valuesOf(Expr e, String inst, String ms) {
        Vals v = eval(e, inst, messageServer(inst, ms));
        if (v.top || v.isEmpty()) return null;
        return new ArrayList<>(v.set);
    }

    /** Instances that may receive this SEND access. */
    public List<String> sendTargets(String inst, Access a) {
        return targets(insts.get(inst), a.target(), a.msgsrv());
    }

    // ------------------------------------------------------------------
    // report
    // ------------------------------------------------------------------

    public void print() {
        System.out.println("\n=== Guard analysis (instance level) ===");

        List<String> unreachable = new ArrayList<>();
        for (RebecInstance ri : result.mainInstances()) {
            ReactiveClass rc = result.classes().get(ri.reactiveClass());
            if (rc == null) continue;
            for (String m : rc.messageServers().keySet())
                if (!reach.contains(new Node(ri.name(), m))) unreachable.add(ri.name() + "." + m);
        }
        System.out.println("Unreachable message servers: " + (unreachable.isEmpty() ? "none" : unreachable));

        System.out.println("--- Conditional accesses (reachable message servers only) ---");
        for (Node n : reach) {
            MessageServer ms = msOf(n);
            for (Access a : ms.accesses()) {
                if (Expr.isTrue(a.cond())) continue;
                System.out.println("  " + n.inst() + "." + n.ms() + ": " + describe(a)
                        + "  cond=" + Expr.show(a.cond()) + "  -> " + classify(a.cond(), n.inst(), ms));
            }
        }

        System.out.println("--- Possible values of state variables ---");
        for (var e : vs.entrySet())
            System.out.println("  " + e.getKey() + " in " + show(e.getValue()));

        System.out.println("--- Writers (writes that can actually happen) ---");
        Map<String, List<String>> writers = new LinkedHashMap<>();
        for (Node n : reach) {
            MessageServer ms = msOf(n);
            for (Access a : ms.accesses()) {
                if (a.kind() != Access.Kind.WRITE) continue;
                Cls c = classify(a.cond(), n.inst(), ms);
                if (c == Cls.NEVER) continue;
                String rhs = (a.rhs() == null) ? "default" : show(eval(a.rhs(), n.inst(), ms));
                writers.computeIfAbsent(n.inst() + "." + a.target(), k -> new ArrayList<>())
                        .add(n.ms() + " [" + c + "] value=" + rhs);
            }
        }
        for (var e : writers.entrySet())
            System.out.println("  " + e.getKey() + " <- " + e.getValue());
    }
}