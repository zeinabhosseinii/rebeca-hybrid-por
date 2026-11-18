package erdg.ast;

import java.util.List;
import java.util.Map;
import java.util.Set;

public record AnalysisResult(
        Map<String, ReactiveClass> classes,
        List<RebecInstance> mainInstances
) {
    public record ReactiveClass(
            String name,
            Set<String> stateVars,
            Map<String, MessageServer> messageServers
    ) {}

    /** One read, write or send performed by a message server, together with its path condition. */
    public record Access(
            Kind kind,
            String target,        // READ/WRITE: variable name; SEND: receiver name ("self", a known rebec, or "?" if unresolved)
            String msgsrv,        // SEND only: invoked message server, else null
            Expr cond,            // path condition under which the access happens
            Expr rhs,             // WRITE only: right-hand side, else null
            List<Expr> args       // SEND only: arguments, else empty
    ) {
        public enum Kind { READ, WRITE, SEND }
    }

    public record MessageServer(
            String name,
            Integer priority,
            List<Send> sends,
            Set<String> reads,
            Set<String> writes,
            List<Access> accesses,
            List<String> params          // formal parameter names, in order
    ) {
        // backward-compatible constructors: existing callers keep compiling
        public MessageServer(String name, Integer priority, List<Send> sends,
                             Set<String> reads, Set<String> writes) {
            this(name, priority, sends, reads, writes, List.of(), List.of());
        }

        public MessageServer(String name, Integer priority, List<Send> sends,
                             Set<String> reads, Set<String> writes, List<Access> accesses) {
            this(name, priority, sends, reads, writes, accesses, List.of());
        }
    }

    public record Send(String target, String message) {}

    public record RebecInstance(
            String name,
            String reactiveClass,
            Map<String, String> knownRebecBindings,
            Integer priority,
            List<Expr> ctorArgs          // constructor arguments given in main, in order
    ) {
        // backward-compatible constructor
        public RebecInstance(String name, String reactiveClass,
                             Map<String, String> knownRebecBindings, Integer priority) {
            this(name, reactiveClass, knownRebecBindings, priority, List.of());
        }
    }
}