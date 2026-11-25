package org.rebecalang.rmc;

import java.util.*;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;

import static org.rebecalang.rmc.PropertyObservationMetadata.need;
import static org.rebecalang.rmc.PropertyObservationMetadata.term;

/** Certifies closed, nullary worker epochs with a counted restart barrier. */
public final class EpochWorkerCertificate {
    private EpochWorkerCertificate() {}

    public static List<Boolean> analyze(RebecaModel model) {
        try {
            var index = new PropertyObservationMetadata.Index(model);
            if (index.instances.size() < 3) return List.of();
            int workers = index.instances.size() - 1;
            for (var hub : index.instances.entrySet()) {
                if (hub.getValue().getMsgsrvs().size() != workers) continue;
                if (matchesEpoch(index, hub.getKey(), workers)) {
                    List<Boolean> result = new ArrayList<>();
                    for (String actor : index.instances.keySet()) result.add(!actor.equals(hub.getKey()));
                    return result;
                }
            }
        } catch (PropertyObservationMetadata.Reject unsupported) {
            return List.of();
        }
        return List.of();
    }

    private record Send(String actor, String method) {}

    private static boolean matchesEpoch(PropertyObservationMetadata.Index index, String hub, int count) {
        var hubClass = index.instances.get(hub);
        need(hubClass.getQueueSize() != null && hubClass.getQueueSize() > count, "hub capacity");
        Set<Send> restart = new HashSet<>();
        Set<String> finishes = new HashSet<>();
        for (var worker : index.instances.entrySet()) {
            String actor = worker.getKey();
            if (actor.equals(hub)) continue;
            var type = worker.getValue();
            need(type.getQueueSize() != null && type.getQueueSize() >= 2, "worker capacity");
            need(type.getMsgsrvs().size() == 1, "exactly one worker handler");
            var tick = type.getMsgsrvs().get(0);
            var code = body(index, actor, tick);
            need(code.size() == 2 && code.get(1) instanceof ConditionalStatement, "worker protocol");
            String counter = increment(code.get(0));
            requireInt(index, actor, counter);
            var branch = (ConditionalStatement) code.get(1);
            var guard = binary(branch.getCondition(), "<");
            need(counter.equals(term(guard.getLeft()).getName()) && literal(guard.getRight()) >= 2, "worker period");
            var again = statements(branch.getStatement());
            var done = statements(branch.getElseStatement());
            Send tickSend = new Send(actor, tick.getName());
            need(again.size() == 1 && send(index, actor, again.get(0)).equals(tickSend), "worker loop");
            need(done.size() == 2 && zero(done.get(0)).equals(counter), "worker reset");
            Send finish = send(index, actor, done.get(1));
            need(finish.actor().equals(hub) && finishes.add(finish.method()), "unique finish handler");
            var init = constructor(index, actor);
            need(init.size() == 2 && zero(init.get(0)).equals(counter)
                    && send(index, actor, init.get(1)).equals(tickSend), "single initial worker tick");
            restart.add(tickSend);
        }

        Set<String> initialized = new HashSet<>();
        for (Statement statement : constructor(index, hub)) {
            String field = zero(statement);
            requireInt(index, hub, field);
            need(initialized.add(field), "duplicate hub initialization");
        }
        String doneCounter = null;
        for (var finish : hubClass.getMsgsrvs()) {
            need(finishes.contains(finish.getName()), "unknown hub handler");
            var code = body(index, hub, finish);
            need(code.size() == 2 && code.get(1) instanceof ConditionalStatement, "hub protocol");
            String field = increment(code.get(0));
            need(initialized.contains(field) && (doneCounter == null || doneCounter.equals(field)), "shared completion counter");
            doneCounter = field;
            var branch = (ConditionalStatement) code.get(1);
            var guard = binary(branch.getCondition(), "==");
            need(field.equals(term(guard.getLeft()).getName()) && literal(guard.getRight()) == count
                    && branch.getElseStatement() == null, "restart threshold");
            var next = statements(branch.getStatement());
            need(next.size() == count + 1 && zero(next.get(0)).equals(field), "restart reset");
            Set<Send> targets = new HashSet<>();
            for (int i = 1; i < next.size(); i++) targets.add(send(index, hub, next.get(i)));
            need(targets.equals(restart), "restart every worker exactly once");
        }
        return true;
    }

    private static void requireInt(PropertyObservationMetadata.Index index, String actor, String field) {
        var type = index.instances.get(actor);
        need("int".equals(index.fields.get(type.getName()).get(field)), "integer counter required");
    }

    private static List<Statement> constructor(PropertyObservationMetadata.Index index, String actor) {
        var ctors = index.instances.get(actor).getConstructors();
        need(ctors.size() == 1, "one constructor required");
        return body(index, actor, ctors.get(0));
    }

    private static List<Statement> body(PropertyObservationMetadata.Index index, String actor, MethodDeclaration method) {
        need(method.getFormalParameters().isEmpty(), "nullary protocol required");
        new PropertyObservationMetadata.Effects(index, actor, method).walk(method.getBlock(), 0);
        return statements(method.getBlock());
    }

    private static List<Statement> statements(Statement statement) {
        need(statement != null, "missing protocol branch");
        return statement instanceof BlockStatement block ? block.getStatements() : List.of(statement);
    }

    private static BinaryExpression binary(Statement statement, String operator) {
        need(statement instanceof BinaryExpression b && operator.equals(b.getOperator()), "unexpected protocol expression");
        return (BinaryExpression) statement;
    }

    private static int literal(Expression expression) {
        need(expression instanceof Literal && Set.of("byte", "short", "int").contains(expression.getType().getTypeName()), "integer literal required");
        try {
            return Integer.parseInt(((Literal) expression).getLiteralValue());
        } catch (NumberFormatException invalid) {
            throw new PropertyObservationMetadata.Reject("invalid integer literal");
        }
    }

    private static String increment(Statement statement) {
        var assignment = binary(statement, "=");
        String field = term(assignment.getLeft()).getName();
        var add = binary(assignment.getRight(), "+");
        need(field.equals(term(add.getLeft()).getName()) && literal(add.getRight()) == 1, "counter increment");
        return field;
    }

    private static String zero(Statement statement) {
        var assignment = binary(statement, "=");
        need(literal(assignment.getRight()) == 0, "zero initialization/reset");
        return term(assignment.getLeft()).getName();
    }

    private static Send send(PropertyObservationMetadata.Index index, String actor, Statement statement) {
        need(statement instanceof DotPrimary, "expected message send");
        var dot = (DotPrimary) statement;
        String receiver = term(dot.getLeft()).getName();
        String target = "self".equals(receiver) ? actor : index.bindings.get(actor).get(receiver);
        var call = (TermPrimary) dot.getRight();
        need(target != null && call.getParentSuffixPrimary().getArguments().isEmpty(), "nullary send required");
        return new Send(target, call.getName());
    }
}
