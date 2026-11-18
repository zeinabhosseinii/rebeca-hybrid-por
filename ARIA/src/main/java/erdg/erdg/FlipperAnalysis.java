package erdg.analysis;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import erdg.analysis.GuardAnalysis.Cls;
import erdg.ast.AnalysisResult.Access;
import erdg.ast.AnalysisResult.MessageServer;
import erdg.ast.AnalysisResult.ReactiveClass;
import erdg.ast.Expr;

/**
 * For every rebec instance and every state variable used in a COND guard, computes the
 * "flippers": reachable message servers of the SAME instance that can write that variable
 * (writes whose condition is not NEVER). The constructor is not a flipper (it runs once, at start).
 *
 * direction (over-approximation, from the possible values of the right-hand side):
 *   TO_TRUE / TO_FALSE / BOTH   boolean variables
 *   CHANGE                      non-boolean values
 *   UNKNOWN                     right-hand side not modelled (treat as "can flip in both directions")
 *
 * The generator uses this only for FUTURE actions: a COND access of a not-yet-enabled action may be
 * dropped only if no flipper can still be processed (pending in a queue, or triggered by a pending message).
 */
public class FlipperAnalysis {

    public record Flipper(String ms, String cls, String direction) {}

    public record GuardVar(String inst, String var, List<Flipper> flippers) {}

    private final GuardAnalysis ga;
    private final List<GuardVar> result = new ArrayList<>();

    public FlipperAnalysis(GuardAnalysis ga) {
        this.ga = ga;
    }

    public List<GuardVar> result() {
        return result;
    }

    public void run() {
        result.clear();
        for (String inst : ga.instanceNames()) {
            ReactiveClass rc = ga.classOfInstance(inst);
            if (rc == null) continue;

            // 1. state variables that occur in some COND path condition of a reachable message server
            Set<String> guardVars = new LinkedHashSet<>();
            for (var e : rc.messageServers().entrySet()) {
                String m = e.getKey();
                if (!ga.isReachable(inst, m)) continue;
                for (Access a : e.getValue().accesses())
                    if (ga.classifyAccess(a, inst, m) == Cls.COND)
                        guardVars.addAll(Expr.varsOf(a.cond()));
            }

            // 2. for each such variable: writers that can really happen (not the constructor)
            for (String v : guardVars) {
                Set<Flipper> flippers = new LinkedHashSet<>();
                for (var e : rc.messageServers().entrySet()) {
                    String m = e.getKey();
                    if (m.equals(rc.name())) continue;                 // constructor
                    if (!ga.isReachable(inst, m)) continue;
                    MessageServer ms = e.getValue();
                    for (Access a : ms.accesses()) {
                        if (a.kind() != Access.Kind.WRITE || !a.target().equals(v)) continue;
                        Cls c = ga.classifyAccess(a, inst, m);
                        if (c == Cls.NEVER) continue;
                        flippers.add(new Flipper(m, c.toString(), direction(a, inst, m)));
                    }
                }
                result.add(new GuardVar(inst, v, new ArrayList<>(flippers)));
            }
        }
    }

    private String direction(Access a, String inst, String ms) {
        List<Object> vals = (a.rhs() == null) ? null : ga.valuesOf(a.rhs(), inst, ms);
        if (vals == null) return "UNKNOWN";
        boolean t = false, f = false, other = false;
        for (Object o : vals) {
            if (Boolean.TRUE.equals(o)) t = true;
            else if (Boolean.FALSE.equals(o)) f = true;
            else other = true;
        }
        if (other) return "CHANGE";
        if (t && f) return "BOTH";
        if (t) return "TO_TRUE";
        if (f) return "TO_FALSE";
        return "UNKNOWN";
    }

    public void print() {
        System.out.println("\n=== Flipper analysis ===");
        for (GuardVar g : result) {
            System.out.println("  " + g.inst() + "." + g.var() + " <- "
                    + (g.flippers().isEmpty() ? "none (stable)" : g.flippers()));
        }
    }
}