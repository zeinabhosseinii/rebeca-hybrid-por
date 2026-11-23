package erdg.pipeline;

import erdg.model.PriorityAssignment;
import java.util.LinkedHashMap;
import java.util.Map;

/** No static scheduling reduction without an external-property preservation proof. */
public final class ExternalPropertyPriorityPolicy {
    private ExternalPropertyPriorityPolicy() {}
    public static PriorityAssignment conservative(PriorityAssignment assignment) {
        Map<String,Integer> actors = new LinkedHashMap<>();
        assignment.rebecPriorities().forEach((name, priority) -> actors.put(name, 1));
        Map<String,Map<String,Integer>> methods = new LinkedHashMap<>();
        assignment.methodPriorities().forEach((name, priorities) -> {
            Map<String,Integer> equal = new LinkedHashMap<>();
            priorities.forEach((method, priority) -> equal.put(method, 1));
            methods.put(name, equal);
        });
        return new PriorityAssignment(assignment.id(), actors, methods);
    }
}
