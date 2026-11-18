package erdg.ast;

import java.util.LinkedHashSet;
import java.util.Set;

public interface Expr {

    record Const(Object value) implements Expr {}
    record Var(String name) implements Expr {}                 // state variable of the owning rebec
    record Param(String name) implements Expr {}               // message parameter (reserved for later)
    record Unary(String op, Expr e) implements Expr {}
    record Binary(String op, Expr l, Expr r) implements Expr {}
    record Unknown(String why) implements Expr {}              // not modelled: "may be true or false"

    Expr TRUE = new Const(Boolean.TRUE);

    static boolean isTrue(Expr e) {
        return e instanceof Const c && Boolean.TRUE.equals(c.value());
    }

    static Expr and(Expr a, Expr b) {
        if (isTrue(a)) return b;
        if (isTrue(b)) return a;
        return new Binary("&&", a, b);
    }

    static Expr not(Expr e) {
        return new Unary("!", e);
    }

    static Set<String> varsOf(Expr e) {
        Set<String> out = new LinkedHashSet<>();
        collect(e, out);
        return out;
    }

    private static void collect(Expr e, Set<String> out) {
        if (e instanceof Var v) out.add(v.name());
        else if (e instanceof Unary u) collect(u.e(), out);
        else if (e instanceof Binary b) { collect(b.l(), out); collect(b.r(), out); }
    }

    /** Human-readable form, used for debugging output. */
    static String show(Expr e) {
        if (e instanceof Const c) return String.valueOf(c.value());
        if (e instanceof Var v) return v.name();
        if (e instanceof Param p) return "param:" + p.name();
        if (e instanceof Unary u) return u.op() + show(u.e());
        if (e instanceof Binary b) return "(" + show(b.l()) + " " + b.op() + " " + show(b.r()) + ")";
        if (e instanceof Unknown k) return "?(" + k.why() + ")";
        return String.valueOf(e);
    }
}