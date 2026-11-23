import java.util.*;
import erdg.model.PriorityAssignment;
import erdg.pipeline.ExternalPropertyPriorityPolicy;

public class ExternalPropertyPolicyTest {
    public static void main(String[] args) {
        var actors = new LinkedHashMap<String,Integer>(Map.of("sender",1,"target",3));
        var methods = new LinkedHashMap<String,Map<String,Integer>>();
        methods.put("Target",new LinkedHashMap<>(Map.of("store",1,"keepAlive",2)));
        var input = new PriorityAssignment(7,actors,methods);
        var output = ExternalPropertyPriorityPolicy.conservative(input);
        if (output.id()!=7 || !output.rebecPriorities().keySet().equals(actors.keySet()) ||
            output.rebecPriorities().values().stream().anyMatch(p -> p!=1) ||
            output.methodPriorities().get("Target").values().stream().anyMatch(p -> p!=1) ||
            !output.methodPriorities().get("Target").keySet().equals(methods.get("Target").keySet()) ||
            input.rebecPriorities().get("target")!=3 || input.methodPriorities().get("Target").get("keepAlive")!=2) {
            throw new AssertionError("Policy must preserve choices and not mutate original priorities");
        }
        System.out.println("PASS: all actors/methods equal; input maps unchanged");
    }
}
