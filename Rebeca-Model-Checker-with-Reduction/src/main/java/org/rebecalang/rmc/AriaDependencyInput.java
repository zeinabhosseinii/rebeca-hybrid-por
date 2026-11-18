package org.rebecalang.rmc;

import com.google.gson.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Imports the static SDI relation. Conditional witnesses remain dependent. */
public final class AriaDependencyInput {
    private AriaDependencyInput() {}

    public static void apply(String path, String sourceHash, Map<String, String> instanceTypes,
                             Map<String, int[]> modelActions,
                             List<List<List<List<Boolean>>>> matrix) {
        try {
            JsonObject root = JsonParser.parseString(Files.readString(Path.of(path))).getAsJsonObject();
            require(root.get("version").getAsInt() == 2, "Expected ARIA schema version 2");
            require(sourceHash != null && root.has("sourceSha256") &&
                    sourceHash.equals(root.get("sourceSha256").getAsString()),
                    "ARIA JSON does not match model source. Regenerate JSON from the same unannotated model.");
            Set<String> instances = new HashSet<>();
            for (JsonElement element : root.getAsJsonArray("instances")) {
                JsonObject inst = element.getAsJsonObject();
                String name = inst.get("name").getAsString();
                require(instances.add(name), "Duplicate instance " + name);
                require(Objects.equals(instanceTypes.get(name), inst.get("class").getAsString()),
                        "Instance/class mismatch " + name);
            }
            require(instances.equals(instanceTypes.keySet()), "Instance inventory mismatch");
            Map<Integer, int[]> actions = new HashMap<>();
            Set<String> labels = new HashSet<>();
            for (JsonElement element : root.getAsJsonArray("actions")) {
                JsonObject action = element.getAsJsonObject();
                int id = action.get("id").getAsInt();
                String label = action.get("instance").getAsString() + "." + action.get("messageServer").getAsString();
                require(modelActions.containsKey(label), "Unknown model action " + label);
                require(labels.add(label) && actions.put(id, modelActions.get(label)) == null,
                        "Duplicate action " + label);
            }
            // Validate the complete table before mutating the caller's matrix.
            Map<String, Boolean> pairs = new HashMap<>();
            int conditional = 0;
            for (JsonElement element : root.getAsJsonArray("actionDependencies")) {
                JsonObject pair = element.getAsJsonObject();
                int left = pair.get("left").getAsInt(), right = pair.get("right").getAsInt();
                require(left <= right && actions.containsKey(left) && actions.containsKey(right), "Invalid action pair");
                String cls = pair.get("class").getAsString();
                require(Set.of("ALWAYS", "COND", "INDEPENDENT").contains(cls), "Unknown dependency class " + cls);
                boolean dependent = !cls.equals("INDEPENDENT");
                require(actions.get(left)[0] != actions.get(right)[0] || dependent,
                        "Same-instance actions must retain dependency");
                require(pairs.put(left + ":" + right, dependent) == null, "Duplicate pair");
                if (cls.equals("COND")) conditional++;
            }
            long count = actions.size();
            require(pairs.size() == count * (count + 1) / 2, "Incomplete dependency table");
            // Actions omitted as unreachable, and unused message IDs, default to dependent.
            for (var row : matrix) for (var actionRow : row) for (var targetRow : actionRow)
                Collections.fill(targetRow, true);
            for (var entry : pairs.entrySet()) {
                String[] ids = entry.getKey().split(":");
                int[] left = actions.get(Integer.parseInt(ids[0]));
                int[] right = actions.get(Integer.parseInt(ids[1]));
                matrix.get(left[0]).get(left[1]).get(right[0]).set(right[1], entry.getValue());
                matrix.get(right[0]).get(right[1]).get(left[0]).set(left[1], entry.getValue());
            }
            System.out.println("ARIA-JSON: loaded " + actions.size() + " actions, " + pairs.size()
                    + " pairs; " + conditional + " conditional pairs retained as dependent");
        } catch (Exception ex) {
            throw new IllegalArgumentException("Cannot import ARIA JSON " + path + ": " + ex.getMessage(), ex);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
