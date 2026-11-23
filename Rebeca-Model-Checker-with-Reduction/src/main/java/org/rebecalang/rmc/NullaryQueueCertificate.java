package org.rebecalang.rmc;

import java.util.*;
import com.google.gson.*;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.propertycompiler.generalrebeca.objectmodel.PropertyModel;

/** Sufficient zero-time/nullary queue-bag certificate. Never used without runtime avoidance closure and proviso. */
public final class NullaryQueueCertificate {
 public static final class Result {
  public final List<List<List<List<Boolean>>>> sends=new ArrayList<>(), conflicts=new ArrayList<>();
  public final List<List<Boolean>> known=new ArrayList<>();
  public long tokenBound;
  public int commutingScalarPairs;
 }
 private static Object scalarExpression(Expression e){
  if(e instanceof Literal literal)return List.of("literal",e.getType().getTypeName(),literal.getLiteralValue());
  if(e instanceof TermPrimary term)return List.of("field",term.getName());
  if(e instanceof BinaryExpression binary)return List.of("binary",binary.getOperator(),scalarExpression(binary.getLeft()),scalarExpression(binary.getRight()));
  if(e instanceof UnaryExpression unary)return List.of("unary",unary.getOperator(),scalarExpression(unary.getExpression()));
  throw new PropertyObservationMetadata.Reject("opaque scalar fingerprint");
 }
 private static Object scalarProgram(Statement s){
  if(s instanceof BlockStatement block){List<Object> program=new ArrayList<>();for(var child:block.getStatements()){var node=scalarProgram(child);if(node!=null)program.add(node);}return program;}
  if(s instanceof DotPrimary)return null; // Fixed nullary sends are separate queue-vector additions, proved nonthrowing by the token bound.
  if(s instanceof BinaryExpression assignment)return List.of("assign",PropertyObservationMetadata.term(assignment.getLeft()).getName(),scalarExpression(assignment.getRight()));
  if(s instanceof ConditionalStatement branch)return Arrays.asList("if",scalarExpression(branch.getCondition()),scalarProgram(branch.getStatement()),branch.getElseStatement()==null?null:scalarProgram(branch.getElseStatement()));
  if(s instanceof TermPrimary)return "assertion_present"; // Such methods are explicitly excluded from scalar-equivalence relaxation.
  throw new PropertyObservationMetadata.Reject("opaque scalar program");
 }
 private static List<List<String>> sends(Statement statement,PropertyObservationMetadata.Effects context,boolean inBranch,boolean constructor){
  List<List<String>> out=new ArrayList<>();
  if(statement instanceof BlockStatement block){for(var child:block.getStatements())out.addAll(sends(child,context,inBranch,constructor));}
  else if(statement instanceof ConditionalStatement branch){out.addAll(sends(branch.getStatement(),context,true,constructor));if(branch.getElseStatement()!=null)out.addAll(sends(branch.getElseStatement(),context,true,constructor));}
  else if(statement instanceof DotPrimary dot){
   PropertyObservationMetadata.need(constructor||!inBranch,"conditional runtime send");
   var receiver=PropertyObservationMetadata.term(dot.getLeft());var call=(TermPrimary)dot.getRight();
   PropertyObservationMetadata.need(call.getParentSuffixPrimary().getArguments().isEmpty(),"message arguments");
   String target="self".equals(receiver.getName())?context.instance:context.index.bindings.get(context.instance).get(receiver.getName());
   PropertyObservationMetadata.need(target!=null,"unresolved send");out.add(List.of(target,call.getName().toUpperCase(Locale.ROOT)));
  }
  return out;
 }
 public record Assessment(Result certificate,String reason) {}
 public static Result analyze(RebecaModel model,PropertyModel property,int width){return assess(model,property,width).certificate();}
 public static Assessment assess(RebecaModel model,PropertyModel property,int width){
  try{return new Assessment(analyzeChecked(model,property,width),null);}
  catch(RuntimeException failure){return new Assessment(null,failure.getMessage()==null?failure.getClass().getSimpleName():failure.getMessage());}
 }
 private static Result analyzeChecked(RebecaModel model,PropertyModel property,int width){
   JsonObject metadata=PropertyObservationMetadata.audit(model,property);
   PropertyObservationMetadata.need(metadata.get("metadata_supported").getAsBoolean()&&!PropertyObservationMetadata.hasModelAnnotations(model),"unsupported_model_or_property_metadata");
   var index=new PropertyObservationMetadata.Index(model);List<String> names=new ArrayList<>(index.instances.keySet());int n=names.size();
   Map<List<String>,Integer> ids=new HashMap<>();Map<Integer,PropertyObservationMetadata.Effects> effects=new HashMap<>();Map<Integer,List<List<String>>> outgoing=new HashMap<>();Map<Integer,Integer> seeds=new HashMap<>();Map<Integer,Object> scalarPrograms=new HashMap<>();
   for(int r=0;r<n;r++){int m=1;for(var method:index.instances.get(names.get(r)).getMsgsrvs()){
    PropertyObservationMetadata.need(method.getFormalParameters().isEmpty()&&m<width,"non_nullary_or_unmapped_method");
    PropertyObservationMetadata.need(ids.put(List.of(names.get(r),method.getName().toUpperCase(Locale.ROOT)),r*width+m++)==null,"ambiguous_method_identity");
   }}
   long tokens=0;
   for(int r=0;r<n;r++){
    String name=names.get(r);var actor=index.instances.get(name);int m=1;
    for(var method:actor.getMsgsrvs()){
     var f=new PropertyObservationMetadata.Effects(index,name,method);f.walk(method.getBlock(),0);int key=r*width+m++;effects.put(key,f);scalarPrograms.put(key,scalarProgram(method.getBlock()));outgoing.put(key,sends(method.getBlock(),f,false,false));
    }
    for(var ctor:actor.getConstructors()){
     var f=new PropertyObservationMetadata.Effects(index,name,ctor);f.walk(ctor.getBlock(),0);
     for(var target:sends(ctor.getBlock(),f,false,true)){Integer key=ids.get(target);PropertyObservationMetadata.need(key!=null,"unmapped_constructor_message");seeds.merge(key,1,Integer::sum);tokens++;}
    }
   }
   Set<Integer> runtimeTargets=new HashSet<>();
   for(var targets:outgoing.values())for(var target:targets){Integer key=ids.get(target);PropertyObservationMetadata.need(key!=null,"unmapped_runtime_message");runtimeTargets.add(key);}
   for(var entry:outgoing.entrySet())if(entry.getValue().size()>1){
    // Fan-out is admissible only when no runtime handler can activate it.
    PropertyObservationMetadata.need(!runtimeTargets.contains(entry.getKey()),"repeatable_runtime_fanout");
    tokens+=(long)seeds.getOrDefault(entry.getKey(),0)*(entry.getValue().size()-1);
   }
   // Bound every queue under every interleaving, including the intermediate enqueue-before-dequeue phase.
   // Execution dequeues after handler completion, so reserve one extra message per atomic handler.
   long transientBound=tokens+1;
   for(var actor:index.instances.values())PropertyObservationMetadata.need(actor.getQueueSize()!=null&&actor.getQueueSize()>transientBound,"insufficient_queue_margin");
   Result result=new Result();result.tokenBound=tokens;
   for(int r=0;r<n;r++){
    List<Boolean> knownRow=new ArrayList<>();List<List<List<Boolean>>> sendRow=new ArrayList<>(), conflictRow=new ArrayList<>();
    for(int m=0;m<width;m++){
     int a=r*width+m;knownRow.add(effects.containsKey(a));List<List<Boolean>> sendActor=new ArrayList<>(),conflictActor=new ArrayList<>();
     for(int j=0;j<n;j++){
      List<Boolean> sendMethod=new ArrayList<>(),conflictMethod=new ArrayList<>();
      for(int k=0;k<width;k++){
       int b=j*width+k;boolean send=false;
       for(var target:outgoing.getOrDefault(a,List.of()))if(ids.get(target)==b)send=true;
       boolean conflict=false;
       if(effects.containsKey(a)&&effects.containsKey(b)&&r==j){
        var x=effects.get(a);var y=effects.get(b);
        conflict=!Collections.disjoint(x.writes,y.writes)||!Collections.disjoint(x.writes,y.reads)||!Collections.disjoint(y.writes,x.reads);
        // Identical total scalar functions commute with themselves, even with overlapping writes.
        // Source-assertion bodies remain conservative; no assertion is assumed or removed.
        if(conflict && a!=b && !x.hasAssertions && !y.hasAssertions && Objects.equals(scalarPrograms.get(a),scalarPrograms.get(b))){
         conflict=false;if(a<b)result.commutingScalarPairs++;
        }
       }
       sendMethod.add(send);conflictMethod.add(conflict);
      }
      sendActor.add(sendMethod);conflictActor.add(conflictMethod);
     }
     sendRow.add(sendActor);conflictRow.add(conflictActor);
    }
    result.known.add(knownRow);result.sends.add(sendRow);result.conflicts.add(conflictRow);
   }
   return result;
 }
}
