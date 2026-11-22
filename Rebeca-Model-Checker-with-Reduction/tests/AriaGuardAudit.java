import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import com.google.gson.*;
import org.rebecalang.rmc.AriaGuardEvaluator;

/** Diagnostic only: validate access provenance and probe guards without bindings. */
public class AriaGuardAudit {
    static void require(boolean ok,String why) {if(!ok)throw new IllegalArgumentException(why);}
    static JsonObject resolve(JsonObject root,JsonObject ref) {
        String instance=ref.get("instance").getAsString(),method=ref.get("messageServer").getAsString();
        int index=ref.get("accessIndex").getAsBigDecimal().intValueExact();
        JsonObject found=null;
        for(JsonElement e:root.getAsJsonArray("instances")) {
            JsonObject i=e.getAsJsonObject();
            if(instance.equals(i.get("name").getAsString())) {
                require(found==null,"duplicate instance reference");found=i;
            }
        }
        require(found!=null,"unknown instance "+instance);
        JsonObject methods=found.getAsJsonObject("messageServers");
        require(methods.has(method),"unknown method "+instance+"."+method);
        JsonArray accesses=methods.getAsJsonObject(method).getAsJsonArray("accesses");
        require(index>=0 && index<accesses.size(),"invalid accessIndex for "+instance+"."+method);
        return accesses.get(index).getAsJsonObject();
    }
    static void unknowns(JsonElement node,Set<String> out,int depth) {
        require(depth<128,"diagnostic expression depth limit");
        if(node==null || !node.isJsonObject())return;
        JsonObject n=node.getAsJsonObject();
        if(n.has("t") && n.get("t").getAsString().equals("unknown"))
            out.add(n.has("why")?n.get("why").getAsString():"unspecified");
        for(String key:List.of("l","r","e"))if(n.has(key))unknowns(n.get(key),out,depth+1);
    }
    public static void main(String[] args) throws Exception {
        require(args.length==3,"Usage: AriaGuardAudit dependencies.json source.rebeca report.json");
        JsonObject root=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(Path.of(args[1]))));
        require(root.get("version").getAsInt()==2,"schema version 2 required");
        require(hash.equals(root.get("sourceSha256").getAsString()),"source hash mismatch");
        Map<Integer,JsonObject> actions=new HashMap<>();
        for(JsonElement e:root.getAsJsonArray("actions")) {
            JsonObject a=e.getAsJsonObject();
            require(actions.put(a.get("id").getAsInt(),a)==null,"duplicate action id");
        }
        JsonArray pairs=new JsonArray();int referenceCount=0,unknownGuards=0;
        for(JsonElement e:root.getAsJsonArray("actionDependencies")) {
            JsonObject pair=e.getAsJsonObject();
            if(!pair.get("class").getAsString().equals("COND"))continue;
            int left=pair.get("left").getAsInt(),right=pair.get("right").getAsInt();
            require(actions.containsKey(left)&&actions.containsKey(right),"unknown action pair");
            JsonObject record=new JsonObject();record.addProperty("left",left);record.addProperty("right",right);
            JsonArray probes=new JsonArray();Set<String> blockers=new TreeSet<>();Set<String> seen=new HashSet<>();
            for(JsonElement reasonElement:pair.getAsJsonArray("reasons")) {
                JsonObject reason=reasonElement.getAsJsonObject();
                require(reason.get("kind").getAsString().equals("SHARED_DESTINATION_SVI"),"unsupported conditional reason");
                JsonObject leftSend=resolve(root,reason.getAsJsonObject("leftSend"));
                JsonObject rightSend=resolve(root,reason.getAsJsonObject("rightSend"));
                for(String side:List.of("left","right")) {
                    JsonObject send=side.equals("left")?leftSend:rightSend;
                    JsonObject accessRef=reason.getAsJsonObject(side+"Access");
                    require(accessRef.get("messageServer").equals(send.get("msgsrv")),"destination handler mismatch");
                    require(send.getAsJsonArray("targetInstances").contains(reason.get("target")),"destination binding mismatch");
                }
                for(String field:List.of("leftSend","rightSend","leftAccess","rightAccess")) {
                    JsonObject ref=reason.getAsJsonObject(field);
                    JsonObject access=resolve(root,ref);
                    if(field.endsWith("Send")) {
                        JsonObject action=actions.get(field.equals("leftSend")?left:right);
                        require(ref.get("instance").equals(action.get("instance")) &&
                                ref.get("messageServer").equals(action.get("messageServer")),"send reference/action mismatch");
                        require(access.get("kind").getAsString().equals("SEND"),"send reference is not SEND");
                        unknownsInArguments(access,blockers);
                    } else {
                        require(ref.get("instance").equals(reason.get("target")),"access target mismatch");
                        require(access.get("target").equals(reason.get("variable")),"access variable mismatch");
                        require(!access.get("kind").getAsString().equals("SEND"),"destination access is SEND");
                    }
                    String key=ref.toString();if(!seen.add(key))continue;
                    referenceCount++;
                    var result=AriaGuardEvaluator.evaluate(access.get("cond"),Map.of(),Map.of());
                    if(result.truth()==AriaGuardEvaluator.Truth.UNKNOWN)unknownGuards++;
                    unknowns(access.get("cond"),blockers,0);
                    JsonObject probe=new JsonObject();probe.add("reference",ref);probe.addProperty("truth",result.truth().name());
                    probe.addProperty("reason",result.reason());probes.add(probe);
                }
            }
            record.add("unboundGuardProbes",probes);
            JsonArray sources=new JsonArray();blockers.forEach(sources::add);record.add("exporterUnknowns",sources);
            record.addProperty("dependencyRetained",true);record.addProperty("stabilityProven",false);pairs.add(record);
        }
        JsonObject report=new JsonObject();report.addProperty("diagnosticOnly",true);report.addProperty("onlineReductionChanged",false);
        report.addProperty("sourceSha256",hash);report.addProperty("conditionalPairs",pairs.size());
        report.addProperty("uniqueReferencesPerPairTotal",referenceCount);report.addProperty("unknownUnboundGuardProbes",unknownGuards);
        report.add("pairs",pairs);report.add("flipperMetadata",root.get("flippers"));
        Path output=Path.of(args[2]);if(output.getParent()!=null)Files.createDirectories(output.getParent());
        Files.writeString(output,new GsonBuilder().setPrettyPrinting().create().toJson(report)+"\n");
        System.out.println("COND diagnostic: pairs="+pairs.size()+", guard references="+referenceCount+", UNKNOWN="+unknownGuards+"; all dependencies retained");
    }
    static void unknownsInArguments(JsonObject access,Set<String> blockers) {
        for(JsonElement arg:access.getAsJsonArray("args"))unknowns(arg,blockers,0);
    }
}
