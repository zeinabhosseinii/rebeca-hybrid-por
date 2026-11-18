package erdg.analysis;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import erdg.analysis.GuardAnalysis.Cls;
import erdg.ast.AnalysisResult.Access;
import erdg.ast.AnalysisResult.MessageServer;
import erdg.ast.AnalysisResult.ReactiveClass;
import erdg.ast.Expr;

/**
 * Writes the information the state-space generator needs (no external JSON library).
 *
 * Schema (version 2):
 * {
 *   "version": 2, "model": "...",
 *   "instances": [ {
 *       "name", "class", "stateVars": [...],
 *       "possibleValues": { var: [values] | "ANY" },
 *       "unreachable": [ms...],
 *       "messageServers": { ms: {
 *           "ctor": bool, "params": [...],
 *           "accesses": [ { "kind": READ|WRITE|SEND, "target", "msgsrv", "targetInstances": [...],
 *                           "cond": Expr, "evaluable": bool, "class": ALWAYS|COND,
 *                           "rhs": Expr|null, "args": [Expr...] } ]   // NEVER accesses are omitted
 *       } } } ],
 *   "flippers": [ { "inst", "var", "flippers": [ { "ms", "class", "direction" } ] } ]
 * }
 * Expr = {"t":"const","v":..} | {"t":"var","name"} | {"t":"param","name"}
 *      | {"t":"unary","op","e"} | {"t":"binary","op","l","r"} | {"t":"unknown","why"}
 * "evaluable" is false if cond contains "unknown": the generator must then keep the dependency.
 */
public class JsonExporter {

    public static void write(String path, String model, GuardAnalysis ga, FlipperAnalysis fa) throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n  \"version\": 2,\n  \"model\": ").append(str(model)).append(",\n");
        sb.append("  \"instances\": [\n");

        List<String> names = ga.instanceNames();
        for (int i = 0; i < names.size(); i++) {
            instance(sb, names.get(i), ga);
            sb.append(i + 1 < names.size() ? ",\n" : "\n");
        }
        sb.append("  ],\n  \"flippers\": [\n");

        var gv = fa.result();
        for (int i = 0; i < gv.size(); i++) {
            var g = gv.get(i);
            sb.append("    {\"inst\": ").append(str(g.inst())).append(", \"var\": ").append(str(g.var()))
              .append(", \"flippers\": [");
            for (int j = 0; j < g.flippers().size(); j++) {
                var f = g.flippers().get(j);
                if (j > 0) sb.append(", ");
                sb.append("{\"ms\": ").append(str(f.ms())).append(", \"class\": ").append(str(f.cls()))
                  .append(", \"direction\": ").append(str(f.direction())).append("}");
            }
            sb.append("]}").append(i + 1 < gv.size() ? ",\n" : "\n");
        }
        sb.append("  ],\n");
        actionDependencies(sb, ga);
        sb.append("\n}\n");

        Path p = Path.of(path);
        if (p.getParent() != null) Files.createDirectories(p.getParent());
        Files.writeString(p, sb.toString(), StandardCharsets.UTF_8);
        System.out.println("Exported conditional dependency table: " + path);
    }

    private static void instance(StringBuilder sb, String inst, GuardAnalysis ga) {
        ReactiveClass rc = ga.classOfInstance(inst);
        sb.append("    {\n      \"name\": ").append(str(inst));
        if (rc == null) { sb.append("\n    }"); return; }
        sb.append(",\n      \"class\": ").append(str(rc.name()));

        sb.append(",\n      \"stateVars\": [");
        boolean first = true;
        for (String v : rc.stateVars()) { if (!first) sb.append(", "); first = false; sb.append(str(v)); }
        sb.append("]");

        sb.append(",\n      \"possibleValues\": {");
        first = true;
        for (String v : rc.stateVars()) {
            if (!first) sb.append(", "); first = false;
            sb.append(str(v)).append(": ");
            List<Object> pv = ga.possibleValues(inst, v);
            if (pv == null) sb.append("\"ANY\"");
            else { sb.append("["); for (int i = 0; i < pv.size(); i++) { if (i > 0) sb.append(", "); value(sb, pv.get(i)); } sb.append("]"); }
        }
        sb.append("}");

        sb.append(",\n      \"unreachable\": [");
        first = true;
        for (String m : rc.messageServers().keySet()) {
            if (ga.isReachable(inst, m)) continue;
            if (!first) sb.append(", "); first = false; sb.append(str(m));
        }
        sb.append("]");

        sb.append(",\n      \"messageServers\": {");
        first = true;
        for (Map.Entry<String, MessageServer> e : rc.messageServers().entrySet()) {
            String m = e.getKey();
            if (!ga.isReachable(inst, m)) continue;
            sb.append(first ? "\n" : ",\n"); first = false;
            messageServer(sb, inst, m, e.getValue(), m.equals(rc.name()), ga);
        }
        sb.append("\n      }\n    }");
    }

    private static void messageServer(StringBuilder sb, String inst, String m, MessageServer ms,
                                      boolean ctor, GuardAnalysis ga) {
        sb.append("        ").append(str(m)).append(": {\"ctor\": ").append(ctor).append(", \"params\": [");
        for (int i = 0; i < ms.params().size(); i++) { if (i > 0) sb.append(", "); sb.append(str(ms.params().get(i))); }
        sb.append("], \"accesses\": [");
        boolean first = true;
        for (Access a : ms.accesses()) {
            Cls c = ga.classifyAccess(a, inst, m);
            if (c == Cls.NEVER) continue;
            sb.append(first ? "\n" : ",\n"); first = false;
            sb.append("          {\"kind\": ").append(str(a.kind().toString()))
              .append(", \"target\": ").append(str(a.target()));
            if (a.msgsrv() != null) {
                sb.append(", \"msgsrv\": ").append(str(a.msgsrv())).append(", \"targetInstances\": [");
                List<String> ts = ga.sendTargets(inst, a);
                for (int i = 0; i < ts.size(); i++) { if (i > 0) sb.append(", "); sb.append(str(ts.get(i))); }
                sb.append("]");
            }
            sb.append(", \"cond\": "); expr(sb, a.cond());
            sb.append(", \"evaluable\": ").append(!hasUnknown(a.cond()));
            sb.append(", \"class\": ").append(str(c.toString()));
            sb.append(", \"rhs\": "); if (a.rhs() == null) sb.append("null"); else expr(sb, a.rhs());
            sb.append(", \"args\": [");
            for (int i = 0; i < a.args().size(); i++) { if (i > 0) sb.append(", "); expr(sb, a.args().get(i)); }
            sb.append("]}");
        }
        sb.append(first ? "]}" : "\n        ]}");
    }


    private record Action(String instance, String method) {}

    private static List<Access> effectiveAccesses(Action action, GuardAnalysis ga) {
        return ga.messageServer(action.instance(), action.method()).accesses().stream()
                .filter(a -> ga.classifyAccess(a, action.instance(), action.method()) != Cls.NEVER)
                .toList();
    }

    /** Complete unordered pair table, including the diagonal. No causal edges are removed. */
    private static void actionDependencies(StringBuilder sb, GuardAnalysis ga) {
        List<Action> actions = new ArrayList<>();
        for (String inst : ga.instanceNames()) {
            ReactiveClass rc = ga.classOfInstance(inst);
            if (rc == null) continue;
            for (String method : rc.messageServers().keySet()) {
                if (!method.equals(rc.name()) && ga.isReachable(inst, method))
                    actions.add(new Action(inst, method));
            }
        }
        sb.append("  \"actions\": [");
        for (int i = 0; i < actions.size(); i++) {
            if (i > 0) sb.append(", ");
            sb.append("{\"id\": ").append(i).append(", \"instance\": ")
              .append(str(actions.get(i).instance())).append(", \"messageServer\": ")
              .append(str(actions.get(i).method())).append("}");
        }
        sb.append("],\n  \"actionDependencies\": [");
        boolean first = true;
        for (int i = 0; i < actions.size(); i++) {
            for (int j = i; j < actions.size(); j++) {
                Action left = actions.get(i), right = actions.get(j);
                List<String> reasons = new ArrayList<>();
                if (left.instance().equals(right.instance())) {
                    reasons.add("{\"kind\": \"SAME_INSTANCE\", \"class\": \"ALWAYS\"}");
                } else {
                    sharedDestinationReasons(reasons, left, right, ga);
                }
                String cls = reasons.isEmpty() ? "INDEPENDENT" : "COND";
                if (reasons.stream().anyMatch(r -> r.contains("\"class\": \"ALWAYS\""))) cls = "ALWAYS";
                if (!first) sb.append(",");
                first = false;
                sb.append("\n    {\"left\": ").append(i).append(", \"right\": ").append(j)
                  .append(", \"class\": ").append(str(cls)).append(", \"reasons\": [")
                  .append(String.join(", ", reasons)).append("]}");
            }
        }
        sb.append("\n  ]");
    }

    private static void sharedDestinationReasons(List<String> reasons, Action left,
                                                 Action right, GuardAnalysis ga) {
        List<Access> la = effectiveAccesses(left, ga), ra = effectiveAccesses(right, ga);
        for (int i = 0; i < la.size(); i++) {
            Access ls = la.get(i);
            if (ls.kind() != Access.Kind.SEND) continue;
            for (int j = 0; j < ra.size(); j++) {
                Access rs = ra.get(j);
                if (rs.kind() != Access.Kind.SEND) continue;
                for (String target : ga.sendTargets(left.instance(), ls)) {
                    if (!ga.sendTargets(right.instance(), rs).contains(target)) continue;
                    Action lm = new Action(target, ls.msgsrv()), rm = new Action(target, rs.msgsrv());
                    if (!ga.knows(target, ls.msgsrv()) || !ga.knows(target, rs.msgsrv())) {
                        reasons.add("{\"kind\": \"UNKNOWN_TARGET\", \"class\": \"ALWAYS\"}");
                        continue;
                    }
                    List<Access> lx = effectiveAccesses(lm, ga), rx = effectiveAccesses(rm, ga);
                    for (int x = 0; x < lx.size(); x++) {
                        for (int y = 0; y < rx.size(); y++) {
                            Access a = lx.get(x), b = rx.get(y);
                            if (a.kind() == Access.Kind.SEND || b.kind() == Access.Kind.SEND) continue;
                            if (!a.target().equals(b.target())) continue;
                            if (a.kind() != Access.Kind.WRITE && b.kind() != Access.Kind.WRITE) continue;
                            boolean always = ga.classifyAccess(ls, left.instance(), left.method()) == Cls.ALWAYS
                                    && ga.classifyAccess(rs, right.instance(), right.method()) == Cls.ALWAYS
                                    && ga.classifyAccess(a, target, lm.method()) == Cls.ALWAYS
                                    && ga.classifyAccess(b, target, rm.method()) == Cls.ALWAYS;
                            reasons.add("{\"kind\": \"SHARED_DESTINATION_SVI\", \"class\": "
                                    + str(always ? "ALWAYS" : "COND") + ", \"target\": " + str(target)
                                    + ", \"variable\": " + str(a.target())
                                    + ", \"leftSend\": " + accessRef(left, i)
                                    + ", \"rightSend\": " + accessRef(right, j)
                                    + ", \"leftAccess\": " + accessRef(lm, x)
                                    + ", \"rightAccess\": " + accessRef(rm, y) + "}");
                        }
                    }
                }
            }
        }
    }

    private static String accessRef(Action action, int index) {
        return "{\"instance\": " + str(action.instance()) + ", \"messageServer\": "
                + str(action.method()) + ", \"accessIndex\": " + index + "}";
    }

    // ---- Expr -> JSON ----

    static void expr(StringBuilder sb, Expr e) {
        if (e instanceof Expr.Const c) { sb.append("{\"t\": \"const\", \"v\": "); value(sb, c.value()); sb.append("}"); }
        else if (e instanceof Expr.Var v) sb.append("{\"t\": \"var\", \"name\": ").append(str(v.name())).append("}");
        else if (e instanceof Expr.Param p) sb.append("{\"t\": \"param\", \"name\": ").append(str(p.name())).append("}");
        else if (e instanceof Expr.Unary u) { sb.append("{\"t\": \"unary\", \"op\": ").append(str(u.op())).append(", \"e\": "); expr(sb, u.e()); sb.append("}"); }
        else if (e instanceof Expr.Binary b) {
            sb.append("{\"t\": \"binary\", \"op\": ").append(str(b.op())).append(", \"l\": "); expr(sb, b.l());
            sb.append(", \"r\": "); expr(sb, b.r()); sb.append("}");
        }
        else if (e instanceof Expr.Unknown k) sb.append("{\"t\": \"unknown\", \"why\": ").append(str(k.why())).append("}");
        else sb.append("{\"t\": \"unknown\", \"why\": \"unsupported node\"}");
    }

    static boolean hasUnknown(Expr e) {
        if (e instanceof Expr.Unknown) return true;
        if (e instanceof Expr.Unary u) return hasUnknown(u.e());
        if (e instanceof Expr.Binary b) return hasUnknown(b.l()) || hasUnknown(b.r());
        return false;
    }

    private static void value(StringBuilder sb, Object o) {
        if (o instanceof Boolean || o instanceof Number) sb.append(o);
        else sb.append(str(String.valueOf(o)));
    }

    private static String str(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char ch : s.toCharArray()) {
            switch (ch) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> { if (ch < 0x20) sb.append(String.format("\\u%04x", (int) ch)); else sb.append(ch); }
            }
        }
        return sb.append('"').toString();
    }
}