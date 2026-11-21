import org.rebecalang.rmc.AriaDependencyInput;
import java.nio.file.*;
import java.util.*;

/** Standalone importer regression; run with javac/java and gson on the classpath. */
public final class AriaDependencyInputRegression {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static List<List<List<List<Boolean>>>> matrix() {
        List<List<List<List<Boolean>>>> result = new ArrayList<>();
        for (int i=0; i<2; i++) {
            List<List<List<Boolean>>> actor = new ArrayList<>();
            for (int mi=0; mi<3; mi++) {
                List<List<Boolean>> action = new ArrayList<>();
                for (int j=0; j<2; j++) action.add(new ArrayList<>(Arrays.asList(true,true,true)));
                actor.add(action);
            }
            result.add(actor);
        }
        return result;
    }
    public static void main(String[] args) throws Exception {
        Path json=Files.createTempFile("aria-import-regression", ".json");
        String data="""
            {"version":2,"sourceSha256":"same-source",
             "instances":[{"name":"a","class":"A"},{"name":"b","class":"B"}],
             "actions":[{"id":0,"instance":"a","messageServer":"one"},
                        {"id":1,"instance":"b","messageServer":"two"}],
             "actionDependencies":[{"left":0,"right":0,"class":"ALWAYS"},
                                   {"left":0,"right":1,"class":"INDEPENDENT"},
                                   {"left":1,"right":1,"class":"ALWAYS"}]}
            """;
        Map<String,int[]> actions=new LinkedHashMap<>();
        actions.put("a.one",new int[]{0,1});
        actions.put("b.two",new int[]{1,1});
        actions.put("b.omitted",new int[]{1,2}); // real model action, absent from export
        try {
            Files.writeString(json,data);
            var m=matrix();
            AriaDependencyInput.apply(json.toString(),"same-source",Map.of("a","A","b","B"),actions,m);
            check(!m.get(0).get(1).get(1).get(1),"independent real pair");
            check(!m.get(1).get(1).get(0).get(1),"symmetric independent pair");
            check(m.get(0).get(1).get(1).get(2),"omitted real action must stay dependent");
            check(m.get(1).get(2).get(0).get(1),"omitted real action symmetry");
            check(!m.get(1).get(1).get(0).get(2),"nonexistent a message 2 must not block");
            check(!m.get(0).get(2).get(1).get(1),"nonexistent slot must clear symmetrically");
            check(m.get(0).get(1).get(0).get(1),"same actor dependency");
            Files.writeString(json,data.replace("INDEPENDENT","COND"));
            AriaDependencyInput.apply(json.toString(),"same-source",Map.of("a","A","b","B"),actions,m);
            check(m.get(0).get(1).get(1).get(1) && m.get(1).get(1).get(0).get(1),"COND must retain dependency");
            var before=m.toString();
            Files.writeString(json,data.replace("same-source","other-source"));
            boolean rejected=false;
            try { AriaDependencyInput.apply(json.toString(),"same-source",Map.of("a","A","b","B"),actions,m); }
            catch (IllegalArgumentException e) { rejected=true; }
            check(rejected && before.equals(m.toString()),"invalid source must reject before mutation");
        } finally { Files.deleteIfExists(json); }
        System.out.println("PASS: unused IDs, omitted real actions, symmetry, COND and invalid-source atomicity");
    }
}
