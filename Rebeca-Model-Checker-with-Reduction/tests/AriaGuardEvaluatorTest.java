import java.util.*;
import com.google.gson.*;
import org.rebecalang.rmc.AriaGuardEvaluator;
import org.rebecalang.rmc.AriaDependencyInput;

public class AriaGuardEvaluatorTest {
    static JsonElement ast(String text) { return JsonParser.parseString(text.replace('\'', '"')); }
    static JsonObject constant(Object v) {
        JsonObject n=new JsonObject();n.addProperty("t","const");
        if(v instanceof Boolean)n.addProperty("v",(Boolean)v);else n.addProperty("v",(Number)v);return n;
    }
    static JsonObject binary(String op,JsonElement l,JsonElement r) {
        JsonObject n=new JsonObject();n.addProperty("t","binary");n.addProperty("op",op);n.add("l",l);n.add("r",r);return n;
    }
    static void check(JsonElement ast,Map<String,Object> state,Map<String,Object> params,AriaGuardEvaluator.Truth expected) {
        var actual=AriaGuardEvaluator.evaluate(ast,state,params);
        if(actual.truth()!=expected)throw new AssertionError(actual.toString());
    }
    static void check(JsonElement ast,AriaGuardEvaluator.Truth expected) { check(ast,Map.of(),Map.of(),expected); }
    public static void main(String[] args) throws Exception {
        var T=AriaGuardEvaluator.Truth.TRUE;var F=AriaGuardEvaluator.Truth.FALSE;var U=AriaGuardEvaluator.Truth.UNKNOWN;
        check(constant(true),T);check(constant(false),F);check(constant(1),U);
        JsonElement expr=binary("==",ast("{'t':'var','name':'StateAlpha'}"),constant(1));
        check(expr,Map.of("StateAlpha",1),Map.of(),T);check(expr,Map.of("StateAlpha",0),Map.of(),F);
        check(expr,U);check(expr,Map.of(),Map.of("StateAlpha",1),U);
        check(expr,Map.of("StateAlpha",true),Map.of(),U);
        check(binary("<",ast("{'t':'param','name':'Window'}"),constant(3)),Map.of(),Map.of("Window",2),T);
        check(binary("==",constant(true),constant(1)),U);
        JsonElement unknown=ast("{'t':'unknown','why':'unsupported: sender'}");
        check(unknown,Map.of("sender",1),Map.of(),U);
        check(binary("&&",constant(false),unknown),U);
        check(binary("||",constant(true),unknown),U);
        check(binary("==",binary("+",constant(Integer.MAX_VALUE),constant(1)),constant(0)),U);
        check(binary("==",binary("/",constant(1),constant(0)),constant(0)),U);
        check(binary("==",binary("%",constant(Integer.MIN_VALUE),constant(-1)),constant(0)),U);
        check(ast("{'t':'const','v':1.0}"),U);check(ast("{'t':'const','v':1.5}"),U);check(ast("{'t':'const','v':'true'}"),U);
        check(ast("{'t':'call','name':'system'}"),U);check(ast("{'t':'binary','op':'=='}"),U);
        check(binary("==",binary("/",constant(-7),constant(3)),constant(-2)),T);
        JsonElement deep=constant(true);
        for(int i=0;i<70;i++)deep=binary("&&",deep,constant(true));
        check(deep,U);
        JsonElement wide=constant(true);
        for(int i=0;i<13;i++)wide=binary("&&",wide,wide);
        check(wide,U);
        // A state writer can flip a snapshot FALSE to TRUE. Evaluation alone is no proof.
        check(expr,Map.of("StateAlpha",0),Map.of(),F);check(expr,Map.of("StateAlpha",1),Map.of(),T);
        // Existing importer must retain every COND pair, even a FALSE snapshot guard.
        String json="{'version':2,'sourceSha256':'test','instances':[{'name':'A','class':'C'},{'name':'B','class':'C'}],"
          +"'actions':[{'id':0,'instance':'A','messageServer':'Run'},{'id':1,'instance':'B','messageServer':'Run'}],"
          +"'actionDependencies':[{'left':0,'right':0,'class':'ALWAYS'},{'left':0,'right':1,'class':'COND'},"
          +"{'left':1,'right':1,'class':'ALWAYS'}]}";
        var matrix=new ArrayList<List<List<List<Boolean>>>>();
        for(int i=0;i<2;i++) {var row=new ArrayList<List<List<Boolean>>>();matrix.add(row);
            for(int m=0;m<2;m++){var targets=new ArrayList<List<Boolean>>();row.add(targets);
                for(int j=0;j<2;j++)targets.add(new ArrayList<>(Collections.nCopies(2,false)));}}
        var file=java.nio.file.Files.createTempFile("aria-cond-test",".json");
        try {
            java.nio.file.Files.writeString(file,json.replace('\'', '"'));
            AriaDependencyInput.apply(file.toString(),"test",Map.of("A","C","B","C"),
                Map.of("A.Run",new int[]{0,1},"B.Run",new int[]{1,1}),matrix);
            if(!matrix.get(0).get(1).get(1).get(1))throw new AssertionError("COND was cleared");
        } finally {java.nio.file.Files.delete(file);}
        System.out.println("PASS: typed snapshot guards, unknowns, bindings, overflow, division, flippers and retained COND");
    }
}
