import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import com.google.gson.*;
import org.rebecalang.compiler.CompilerConfig;
import org.rebecalang.compiler.modelcompiler.RebecaModelCompiler;
import org.rebecalang.compiler.modelcompiler.corerebeca.CoreRebecaLabelUtility;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.utils.*;
import org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary;
import org.rebecalang.rmc.ERDGSafetyAnalyzer;
import org.rebecalang.rmc.RMCConfig;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/** Offline typed-AST footprint audit. Never authorizes a runtime candidate. */
public class AssertionObservationAudit {
 static final Set<String> TYPES=Set.of("int","short","byte","boolean");
 static final Set<String> OPS=Set.of("==","!=","<","<=",">",">=","&&","||");
 static final Set<String> FORBIDDEN=Set.of("now","sender","self","currentMessageArrival","currentMessageDeadline","currentMessageWaitingTime");
 static boolean untimed(ParentSuffixPrimary suffix){
  if(suffix.getClass()==ParentSuffixPrimary.class)return true;
  if(suffix.getClass()!=TimedRebecaParentSuffixPrimary.class)return false;
  var timed=(TimedRebecaParentSuffixPrimary)suffix;
  return timed.getAfterExpression()==null && timed.getDeadlineExpression()==null;
 }
 static boolean primitive(Expression e){return e.getType()!=null && TYPES.contains(e.getType().getTypeName());}
 static boolean predicate(Expression e,Set<String> fields,Set<String> reads,int depth){
  if(e==null || depth>128 || !primitive(e))return false;
  if(e.getClass()==Literal.class)return true;
  if(e.getClass()==TermPrimary.class){
   TermPrimary t=(TermPrimary)e;
   if(t.getParentSuffixPrimary()!=null || !t.getIndices().isEmpty() || FORBIDDEN.contains(t.getName()) ||
      !fields.contains(t.getName()) || !CoreRebecaLabelUtility.STATE_VARIABLE.equals(t.getLabel()))return false;
   reads.add(t.getName());return true;
  }
  if(e.getClass()==BinaryExpression.class){BinaryExpression b=(BinaryExpression)e;
   return OPS.contains(b.getOperator()) && predicate(b.getLeft(),fields,reads,depth+1) && predicate(b.getRight(),fields,reads,depth+1);
  }
  if(e.getClass()==UnaryExpression.class){UnaryExpression u=(UnaryExpression)e;
   return "!".equals(u.getOperator()) && predicate(u.getExpression(),fields,reads,depth+1);
  }
  return false;
 }
 static class Footprint {
  Set<String> writes=new TreeSet<>();List<TermPrimary> assertions=new ArrayList<>();boolean complete=true;int nodes=0;
 }
 static void walk(Statement node,Footprint f,Set<String> fields,int depth){
  if(node==null)return;
  if(depth>128 || ++f.nodes>100000){f.complete=false;return;}
  if(node.getClass()==BlockStatement.class){for(Statement s:((BlockStatement)node).getStatements())walk(s,f,fields,depth+1);return;}
  if(node.getClass()==ConditionalStatement.class){ConditionalStatement c=(ConditionalStatement)node;walk(c.getCondition(),f,fields,depth+1);walk(c.getStatement(),f,fields,depth+1);walk(c.getElseStatement(),f,fields,depth+1);return;}
  if(node.getClass()==WhileStatement.class){WhileStatement w=(WhileStatement)node;walk(w.getCondition(),f,fields,depth+1);walk(w.getStatement(),f,fields,depth+1);return;}
  if(node.getClass()==BinaryExpression.class){BinaryExpression b=(BinaryExpression)node;
   if(!Set.of("=","+=","-=","*=","/=","%=","&=","|=","^=","<<=",">>=",">>>=","+","-","*","/","%","&","|","^","<<",">>",">>>","==","!=","<","<=",">",">=","&&","||").contains(b.getOperator()))f.complete=false;
   if(Set.of("=","+=","-=","*=","/=","%=","&=","|=","^=","<<=",">>=",">>>=").contains(b.getOperator())){
    if(b.getLeft() instanceof TermPrimary && CoreRebecaLabelUtility.STATE_VARIABLE.equals(((TermPrimary)b.getLeft()).getLabel()))f.writes.add(((TermPrimary)b.getLeft()).getName());
    else f.complete=false;
   }
   walk(b.getLeft(),f,fields,depth+1);walk(b.getRight(),f,fields,depth+1);return;
  }
  if(node.getClass()==UnaryExpression.class){UnaryExpression u=(UnaryExpression)node;
   if(!Set.of("++","--","+","-","!","~").contains(u.getOperator()))f.complete=false;
   if(Set.of("++","--").contains(u.getOperator())){
    if(u.getExpression() instanceof TermPrimary && CoreRebecaLabelUtility.STATE_VARIABLE.equals(((TermPrimary)u.getExpression()).getLabel()))f.writes.add(((TermPrimary)u.getExpression()).getName());else f.complete=false;
   }
   walk(u.getExpression(),f,fields,depth+1);return;
  }
  if(node.getClass()==DotPrimary.class){DotPrimary d=(DotPrimary)node;walk(d.getLeft(),f,fields,depth+1);walk(d.getRight(),f,fields,depth+1);return;}
  if(node.getClass()==TermPrimary.class){TermPrimary t=(TermPrimary)node;
   for(Expression e:t.getIndices())walk(e,f,fields,depth+1);
   ParentSuffixPrimary s=t.getParentSuffixPrimary();if(s==null)return;
   if("assertion".equals(t.getName()) && CoreRebecaLabelUtility.BUILT_IN_METHOD.equals(t.getLabel()))f.assertions.add(t);
   else if(!CoreRebecaLabelUtility.MSGSRV.equals(t.getLabel()))f.complete=false;
   for(Expression e:s.getArguments())walk(e,f,fields,depth+1);
   // Explicit timing or an opaque suffix class makes this offline audit incomplete.
   if(!untimed(s))f.complete=false;
   return;
  }
  if(node.getClass()!=Literal.class)f.complete=false;
 }
 static JsonObject audit(RebecaModel model){
  JsonObject root=new JsonObject();root.addProperty("diagnostic_only",true);root.addProperty("runtime_gate_changed",false);
  root.addProperty("runtime_independence_certified",false);root.addProperty("current_full_barrier_gate",ERDGSafetyAnalyzer.supportsFullExpansionBarriers(model));
  JsonArray rows=new JsonArray();boolean complete=true;
  RebecaCode code=model.getRebecaCode();
  if(!code.getGlobalVariables().isEmpty() || !code.getEnvironmentVariables().isEmpty() || !code.getFeatureVariables().isEmpty() || !code.getRecordDeclaration().isEmpty() || !code.getInterfaceDeclaration().isEmpty())complete=false;
  for(ReactiveClassDeclaration actor:code.getReactiveClassDeclaration()){
   if(actor.getExtends()!=null || !actor.getImplements().isEmpty() || !actor.getSynchMethods().isEmpty() || actor.getClass()!=ReactiveClassDeclaration.class)complete=false;
   if(!actor.getAnnotations().isEmpty())complete=false;
   Set<String> fields=new TreeSet<>();for(FieldDeclaration field:actor.getStatevars())for(VariableDeclarator v:field.getVariableDeclarators())fields.add(v.getVariableName());
   Map<MethodDeclaration,Footprint> methods=new LinkedHashMap<>();
   for(ConstructorDeclaration ctor:actor.getConstructors()){Footprint f=new Footprint();if(ctor.getBlock()==null)f.complete=false;else walk(ctor.getBlock(),f,fields,0);methods.put(ctor,f);}
   for(MsgsrvDeclaration method:actor.getMsgsrvs()){Footprint f=new Footprint();if(method.getBlock()==null)f.complete=false;else walk(method.getBlock(),f,fields,0);methods.put(method,f);}
   for(var entry:methods.entrySet()){
    Footprint f=entry.getValue();if(!entry.getKey().getAnnotations().isEmpty())f.complete=false;complete &= f.complete;
    for(TermPrimary call:f.assertions){
     Set<String> reads=new TreeSet<>();ParentSuffixPrimary suffix=call.getParentSuffixPrimary();
     boolean pure=untimed(suffix) && suffix.getArguments().size()==1 && predicate(suffix.getArguments().get(0),fields,reads,0) && "boolean".equals(suffix.getArguments().get(0).getType().getTypeName());
     JsonObject row=new JsonObject();row.addProperty("suffix_class",suffix.getClass().getSimpleName());row.addProperty("argument_count",suffix.getArguments().size());row.addProperty("predicate_class",suffix.getArguments().isEmpty()?"missing":suffix.getArguments().get(0).getClass().getSimpleName());row.addProperty("predicate_type",suffix.getArguments().isEmpty()||suffix.getArguments().get(0).getType()==null?"missing":suffix.getArguments().get(0).getType().getTypeName());row.addProperty("actor_class",actor.getName());row.addProperty("method",entry.getKey().getName());
     row.addProperty("syntax_supported",pure);row.addProperty("read_footprint_complete",pure);row.addProperty("classification",pure?"local_side_effect_free_shape_only":"outside_supported_predicate_syntax");row.add("local_read_fields",new Gson().toJsonTree(reads));
     JsonArray writers=new JsonArray();
     for(var other:methods.entrySet()){
      if(!(other.getKey() instanceof MsgsrvDeclaration))continue;
      Set<String> overlap=new TreeSet<>(other.getValue().writes);overlap.retainAll(reads);
      if(!other.getValue().complete || !overlap.isEmpty()){
       JsonObject writer=new JsonObject();writer.addProperty("method",other.getKey().getName());writer.add("overlap",new Gson().toJsonTree(overlap));writer.addProperty("unknown_effects",!other.getValue().complete);writers.add(writer);
      }
     }
     row.add("potential_runtime_writers",writers);row.addProperty("obligation","preserve error reachability over all deferred continuations; predicate purity alone is insufficient");rows.add(row);
    }
   }
  }
  root.addProperty("traversal_complete",complete);root.add("assertions",rows);return root;
 }
 public static void main(String[] args)throws Exception{
  if(args.length!=2)throw new IllegalArgumentException("source.rebeca output.json");
  try(var context=new AnnotationConfigApplicationContext(CompilerConfig.class,RMCConfig.class)){
   var errors=context.getBean(ExceptionContainer.class);errors.clear();
   var pair=context.getBean(RebecaModelCompiler.class).compileRebecaFile(Path.of(args[0]).toFile(),Set.of(CompilerExtension.TIMED_REBECA),CoreVersion.CORE_2_3);
   if(!errors.exceptionsIsEmpty())throw new IllegalArgumentException("Compiler rejected source: "+errors);
   JsonObject r=audit(pair.getFirst());r.addProperty("source_sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(Path.of(args[0])))));
   Path output=Path.of(args[1]);Files.createDirectories(output.toAbsolutePath().getParent());Files.writeString(output,new GsonBuilder().setPrettyPrinting().create().toJson(r)+"\n");
   System.out.println("Assertion footprints="+r.getAsJsonArray("assertions").size()+"; runtime certificate=false; report="+output);
  }
 }
}
