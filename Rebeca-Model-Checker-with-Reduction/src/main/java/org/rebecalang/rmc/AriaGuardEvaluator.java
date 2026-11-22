package org.rebecalang.rmc;

import com.google.gson.*;
import java.math.BigDecimal;
import java.util.*;

/** Typed snapshot evaluation only. A FALSE guard is NOT a persistence certificate.
 * Unknown bindings/syntax, arithmetic errors and type mismatches fail closed.
 * No expression text is executed and no dependency matrix is modified.
 */
public final class AriaGuardEvaluator {
    public enum Truth { TRUE, FALSE, UNKNOWN }
    public record Result(Truth truth, String reason, Set<String> bindingsRead) {}
    private record Value(Object value, String reason) {}
    private static final int MAX_DEPTH = 64, MAX_NODES = 4096;
    private AriaGuardEvaluator() {}

    public static Result evaluate(JsonElement expression, Map<String, Object> state,
                                  Map<String, Object> parameters) {
        Set<String> reads = new LinkedHashSet<>();
        Value value = eval(expression, state, parameters, reads, new int[]{0}, 0);
        Truth truth = value.value instanceof Boolean
                ? ((Boolean)value.value ? Truth.TRUE : Truth.FALSE) : Truth.UNKNOWN;
        String reason = truth != Truth.UNKNOWN ? "snapshot_only_not_a_reduction_certificate"
                : value.reason != null ? value.reason : "guard_is_not_boolean";
        return new Result(truth, reason, Collections.unmodifiableSet(reads));
    }

    private static Value unknown(String reason) { return new Value(null, reason); }
    private static Value value(Object value) { return new Value(value, null); }
    private static String string(JsonObject node, String field) {
        JsonElement e = node.get(field);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isString())
            throw new IllegalArgumentException("missing/string field " + field);
        return e.getAsString();
    }

    private static Value eval(JsonElement expression, Map<String, Object> state,
                              Map<String, Object> parameters, Set<String> reads,
                              int[] nodes, int depth) {
        if (depth > MAX_DEPTH || ++nodes[0] > MAX_NODES) return unknown("expression_limit");
        try {
            if (expression == null || !expression.isJsonObject()) return unknown("missing_object_expression");
            JsonObject n = expression.getAsJsonObject();
            String type = string(n, "t");
            switch (type) {
                case "unknown": return unknown("exporter_unknown:" + (n.has("why") ? n.get("why").toString() : "unspecified"));
                case "const": {
                    JsonElement e = n.get("v");
                    if (e == null || !e.isJsonPrimitive()) return unknown("invalid_constant");
                    JsonPrimitive p = e.getAsJsonPrimitive();
                    if (p.isBoolean()) return value(p.getAsBoolean());
                    if (p.isNumber() && p.getAsString().matches("-?(0|[1-9][0-9]*)"))
                        return value(new BigDecimal(p.getAsString()).intValueExact());
                    return unknown("unsupported_constant_type");
                }
                case "var":
                case "param": {
                    String name = string(n, "name");
                    boolean variable = type.equals("var");
                    reads.add((variable ? "state:" : "parameter:") + name);
                    Map<String,Object> bindings = variable ? state : parameters;
                    Object bound = bindings == null ? null : bindings.get(name);
                    if (!(bound instanceof Integer) && !(bound instanceof Boolean))
                        return unknown("missing_or_untyped_binding:" + type + ":" + name);
                    return value(bound);
                }
                case "unary": {
                    String op = string(n, "op");
                    Value e = eval(n.get("e"),state,parameters,reads,nodes,depth+1);
                    if (e.value == null) return e;
                    if (op.equals("!") && e.value instanceof Boolean) return value(!(Boolean)e.value);
                    if (e.value instanceof Integer) {
                        if (op.equals("-")) return value(Math.negateExact((Integer)e.value));
                        if (op.equals("+")) return e;
                    }
                    return unknown("unsupported_unary_or_type:" + op);
                }
                case "binary": {
                    String op = string(n, "op");
                    // Strict UNKNOWN propagation is conservative even where short-circuit
                    // execution could determine a value. Unsupported side effects are never guessed.
                    Value l = eval(n.get("l"),state,parameters,reads,nodes,depth+1);
                    Value r = eval(n.get("r"),state,parameters,reads,nodes,depth+1);
                    if (l.value == null) return l;
                    if (r.value == null) return r;
                    if (op.equals("==") || op.equals("!=")) {
                        if (l.value.getClass() != r.value.getClass()) return unknown("equality_type_mismatch");
                        boolean equal = l.value.equals(r.value);
                        return value(op.equals("==") ? equal : !equal);
                    }
                    if (l.value instanceof Boolean && r.value instanceof Boolean) {
                        if (op.equals("&&")) return value((Boolean)l.value && (Boolean)r.value);
                        if (op.equals("||")) return value((Boolean)l.value || (Boolean)r.value);
                    }
                    if (!(l.value instanceof Integer) || !(r.value instanceof Integer)) return unknown("binary_type_mismatch");
                    int a=(Integer)l.value, b=(Integer)r.value;
                    switch (op) {
                        case "+": return value(Math.addExact(a,b));
                        case "-": return value(Math.subtractExact(a,b));
                        case "*": return value(Math.multiplyExact(a,b));
                        case "/":
                        case "%":
                            if (b==0 || (a==Integer.MIN_VALUE && b==-1)) return unknown("invalid_division");
                            return value(op.equals("/") ? a/b : a%b);
                        case "<": return value(a<b);
                        case "<=": return value(a<=b);
                        case ">": return value(a>b);
                        case ">=": return value(a>=b);
                        default: return unknown("unsupported_binary:" + op);
                    }
                }
                default: return unknown("unsupported_node:" + type);
            }
        } catch (RuntimeException ex) {
            return unknown("malformed_or_arithmetic:" + ex.getClass().getSimpleName());
        }
    }
}
