package org.rebecalang.rmc;
import java.util.*;
import com.google.gson.*;
import org.rebecalang.compiler.modelcompiler.corerebeca.CoreRebecaLabelUtility;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.propertycompiler.generalrebeca.objectmodel.PropertyModel;


/** Restricted typed-AST footprints. Mode and reviewed-source gates are mandatory at the caller. */
public final class PropertyObservationMetadata {
 public static class ConfigurationException extends IllegalArgumentException { public ConfigurationException(String message){super(message);} }
 /** Sufficient product-model certificate: runtime handlers cannot read/write another actor or enqueue there. */
 public static boolean supportsActorLocalRuntime(RebecaModel model,PropertyModel property){
  try {
   var metadata=audit(model,property);
   if(!metadata.get("metadata_supported").getAsBoolean() || hasModelAnnotations(model))return false;
   for(var item:metadata.getAsJsonArray("actions")){
    var row=item.getAsJsonObject();String owner=row.getAsJsonArray("action").get(0).getAsString();
    for(var send:row.getAsJsonArray("sends"))if(!owner.equals(send.getAsJsonArray().get(0).getAsString()))return false;
   }
   return true;
  }catch(RuntimeException failure){return false;}
 }
 public static boolean hasModelAnnotations(RebecaModel model){
  for(var instance:model.getRebecaCode().getMainDeclaration().getMainRebecDefinition())if(!instance.getAnnotations().isEmpty())return true;
  for(var actor:model.getRebecaCode().getReactiveClassDeclaration()){
   if(!actor.getAnnotations().isEmpty())return true;
   for(var method:actor.getMsgsrvs())if(!method.getAnnotations().isEmpty())return true;
   for(var ctor:actor.getConstructors())if(!ctor.getAnnotations().isEmpty())return true;
  }
  return false;
 }
 static boolean untimed(ParentSuffixPrimary suffix){
  if(suffix.getClass()==ParentSuffixPrimary.class)return true;
  if(suffix.getClass()!=org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary.class)return false;
  var timed=(org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary)suffix;
  return timed.getAfterExpression()==null && timed.getDeadlineExpression()==null;
 }
 /** Shape metadata is not a reduction permit. Caller must enforce reviewed-source/mode gates. */
 public static List<List<Boolean>> invisibleTable(RebecaModel model,PropertyModel property,int maximumMessageId,boolean allowed){
  List<List<Boolean>> table=new ArrayList<>();
  for(var instance:model.getRebecaCode().getMainDeclaration().getMainRebecDefinition())table.add(new ArrayList<>(Collections.nCopies(maximumMessageId+1,false)));
  if(!allowed||property==null)return table;
  try{
   JsonObject metadata=audit(model,property);
   if(!metadata.get("metadata_supported").getAsBoolean())return table;
   Set<JsonElement> reads=new HashSet<>();for(var read:metadata.getAsJsonArray("property_reads"))reads.add(read);
   Map<String,JsonObject> actions=new HashMap<>();for(var row:metadata.getAsJsonArray("actions")){var r=row.getAsJsonObject();var a=r.getAsJsonArray("action");String key=a.get(0).getAsString()+"/"+a.get(1).getAsString();if(actions.put(key,r)!=null)return table;}
   Index index=new Index(model);int actorId=0;
   for(var instance:index.instances.entrySet()){
    int messageId=1;
    for(var method:instance.getValue().getMsgsrvs()){
     var row=actions.get(instance.getKey()+"/"+method.getName().toUpperCase(Locale.ROOT));
     if(row==null||messageId>maximumMessageId)return emptyLike(table);
     boolean invisible=row.get("complete").getAsBoolean();for(var write:row.getAsJsonArray("writes"))if(reads.contains(write))invisible=false;
     table.get(actorId).set(messageId++,invisible);
    }
    actorId++;
   }
   return table;
  }catch(RuntimeException failure){return emptyLike(table);}
 }
 private static List<List<Boolean>> emptyLike(List<List<Boolean>> input){List<List<Boolean>> out=new ArrayList<>();for(var row:input)out.add(new ArrayList<>(Collections.nCopies(row.size(),false)));return out;}

 static final Set<String> RESERVED=Set.of("now","sender","self","currentMessageArrival","currentMessageDeadline","currentMessageWaitingTime");
 static final Set<String> TYPES=Set.of("int","byte","short","boolean");
 static final Set<String> OPS=Set.of("==","!=","<","<=",">",">=","&&","||");
 static boolean scalar(Type type){return type!=null && !(type instanceof ArrayType) && TYPES.contains(type.getTypeName());}
 static class Reject extends RuntimeException {Reject(String s){super(s);}}
 static void need(boolean ok,String why){if(!ok)throw new Reject(why);}
 static class Index {
  Map<String,ReactiveClassDeclaration> classes=new LinkedHashMap<>();
  Map<String,ReactiveClassDeclaration> instances=new LinkedHashMap<>();
  Map<String,Map<String,String>> fields=new LinkedHashMap<>(),bindings=new LinkedHashMap<>();
  Index(RebecaModel model){
   var c=model.getRebecaCode();need(c.getGlobalVariables().isEmpty()&&c.getEnvironmentVariables().isEmpty()&&c.getFeatureVariables().isEmpty()&&c.getRecordDeclaration().isEmpty()&&c.getInterfaceDeclaration().isEmpty(),"global/environment/features/records/interfaces unsupported");
   for(var a:c.getReactiveClassDeclaration()){
    need(a.getClass()==ReactiveClassDeclaration.class&&a.getExtends()==null&&a.getImplements().isEmpty()&&a.getSynchMethods().isEmpty()&&a.getAnnotations().isEmpty(),"inheritance/synchronous/annotated classes unsupported");classes.put(a.getName(),a);
    Map<String,String> fieldsOfClass=new LinkedHashMap<>();
    for(var f:a.getStatevars())for(var v:f.getVariableDeclarators()){
     need(scalar(f.getType())&&v.getVariableInitializer()==null&&!RESERVED.contains(v.getVariableName()),"only primitive scalar fields without initializers");fieldsOfClass.put(v.getVariableName(),f.getType().getTypeName());
    }
    fields.put(a.getName(),fieldsOfClass);
   }
   for(var i:c.getMainDeclaration().getMainRebecDefinition()){
    need(!RESERVED.contains(i.getName())&&i.getAnnotations().isEmpty()&&classes.containsKey(i.getType().getTypeName()),"unknown/annotated instance");
    for(var arg:i.getArguments())need(arg.getClass()==Literal.class&&scalar(arg.getType()),"only literal primitive constructor actual arguments supported");
    need(!instances.containsKey(i.getName()),"duplicate instance");instances.put(i.getName(),classes.get(i.getType().getTypeName()));
   }
   for(var i:c.getMainDeclaration().getMainRebecDefinition()){
    List<String> names=new ArrayList<>();for(var f:instances.get(i.getName()).getKnownRebecs())for(var v:f.getVariableDeclarators()){need(!RESERVED.contains(v.getVariableName()),"reserved knownrebec name");names.add(v.getVariableName());}
    need(names.size()==i.getBindings().size(),"unresolved knownrebec bindings");Map<String,String> map=new LinkedHashMap<>();
    for(int k=0;k<names.size();k++){TermPrimary t=term(i.getBindings().get(k));need(instances.containsKey(t.getName()),"dynamic/unknown binding");map.put(names.get(k),t.getName());}
    bindings.put(i.getName(),map);
   }
  }
  String field(String instance,String name){need(instances.containsKey(instance),"unknown property instance");var cls=instances.get(instance);need(fields.get(cls.getName()).containsKey(name),"unknown scalar field");return cls.getName()+"."+name;}
 }
 static TermPrimary term(Expression e){need(e!=null&&e.getClass()==TermPrimary.class,"expected simple term");var t=(TermPrimary)e;need(t.getIndices().isEmpty()&&t.getParentSuffixPrimary()==null,"indexed/call term unsupported");return t;}
 static class Effects {
  Set<List<String>> reads=new LinkedHashSet<>(),writes=new LinkedHashSet<>(),sends=new LinkedHashSet<>();
  Set<String> params=new HashSet<>();Index index;String instance;int nodes;boolean hasAssertions;
  Effects(Index i,String name,MethodDeclaration method){index=i;instance=name;need(method.getBlock()!=null&&method.getAnnotations().isEmpty(),"missing/annotated method");for(var p:method.getFormalParameters()){need(scalar(p.getType())&&!RESERVED.contains(p.getName()),"reserved/reference/array parameters unsupported");params.add(p.getName());}}
  void budget(int depth){need(depth<100&&++nodes<100000,"AST traversal budget");}
  List<String> local(TermPrimary t){need(CoreRebecaLabelUtility.STATE_VARIABLE.equals(t.getLabel()),"assignment target must be local state");return List.of(instance,index.field(instance,t.getName()));}
  void expr(Expression e,int depth){
   budget(depth);need(e!=null&&scalar(e.getType()),"unsupported expression type");
   if(e.getClass()==Literal.class)return;
   if(e.getClass()==TermPrimary.class){var t=term(e);if(CoreRebecaLabelUtility.STATE_VARIABLE.equals(t.getLabel()))reads.add(local(t));else need(params.contains(t.getName()),"unknown/nonlocal expression term");return;}
   if(e.getClass()==BinaryExpression.class){var b=(BinaryExpression)e;need(OPS.contains(b.getOperator())||Set.of("+","-").contains(b.getOperator()),"side effect/arithmetic outside expression fragment");expr(b.getLeft(),depth+1);expr(b.getRight(),depth+1);return;}
   if(e.getClass()==UnaryExpression.class){var u=(UnaryExpression)e;need(Set.of("!","-","+").contains(u.getOperator()),"unary side effects unsupported");expr(u.getExpression(),depth+1);return;}
   throw new Reject("opaque expression "+e.getClass().getSimpleName());
  }
  void walk(Statement s,int depth){
   budget(depth);need(s!=null,"missing statement");
   if(s.getClass()==BlockStatement.class){for(var x:((BlockStatement)s).getStatements())walk(x,depth+1);return;}
   if(s.getClass()==ConditionalStatement.class){var c=(ConditionalStatement)s;expr(c.getCondition(),depth+1);walk(c.getStatement(),depth+1);if(c.getElseStatement()!=null)walk(c.getElseStatement(),depth+1);return;}
   if(s.getClass()==BinaryExpression.class){var b=(BinaryExpression)s;need("=".equals(b.getOperator()),"only direct scalar assignment statements");writes.add(local(term(b.getLeft())));expr(b.getRight(),depth+1);return;}
   if(s.getClass()==TermPrimary.class){var t=(TermPrimary)s;need("assertion".equals(t.getName())&&CoreRebecaLabelUtility.BUILT_IN_METHOD.equals(t.getLabel()),"unknown builtin/bare call");need(t.getParentSuffixPrimary()!=null&&untimed(t.getParentSuffixPrimary())&&t.getParentSuffixPrimary().getArguments().size()==1,"unsupported source assertion");hasAssertions=true;expr(t.getParentSuffixPrimary().getArguments().get(0),depth+1);return;}
   if(s.getClass()==DotPrimary.class){var d=(DotPrimary)s;var receiver=term(d.getLeft());String target;
    if("self".equals(receiver.getName()))target=instance;else {target=index.bindings.get(instance).get(receiver.getName());need(target!=null,"dynamic/unknown receiver");}
    need(d.getRight().getClass()==TermPrimary.class,"computed message target");var call=(TermPrimary)d.getRight();need(CoreRebecaLabelUtility.MSGSRV.equals(call.getLabel())&&call.getIndices().isEmpty()&&call.getParentSuffixPrimary()!=null&&untimed(call.getParentSuffixPrimary()),"unknown/timed message send");
    need(index.instances.get(target).getMsgsrvs().stream().anyMatch(m->m.getName().equals(call.getName())),"unresolved target handler");
    for(var arg:call.getParentSuffixPrimary().getArguments())expr(arg,depth+1);sends.add(List.of(target,call.getName().toUpperCase(Locale.ROOT)));return;
   }
   throw new Reject("unsupported statement "+s.getClass().getSimpleName());
  }
 }
 static JsonObject propertyExpr(Expression e,Index i,Set<List<String>> reads,int depth){
  need(e!=null&&depth<100&&scalar(e.getType()),"unsupported property expression/type");JsonObject r=new JsonObject();
  if(e.getClass()==Literal.class){String literal=((Literal)e).getLiteralValue();
   if("boolean".equals(e.getType().getTypeName()))need(Set.of("true","false").contains(literal),"unknown boolean literal");
   else {need(literal.matches("[0-9]+"),"nondecimal property literal unsupported");try{need(Long.parseLong(literal)<=Integer.MAX_VALUE,"property literal overflow");}catch(NumberFormatException failure){throw new Reject("property literal overflow");}}
   r.addProperty("kind","literal");r.addProperty("type",e.getType().getTypeName());r.addProperty("value",((Literal)e).getLiteralValue());return r;}
  if(e.getClass()==DotPrimary.class){var d=(DotPrimary)e;var actor=term(d.getLeft());var field=term(d.getRight());String qualified=i.field(actor.getName(),field.getName());var key=List.of(actor.getName(),qualified);reads.add(key);r.addProperty("kind","field");r.add("key",new Gson().toJsonTree(key));r.addProperty("type",e.getType().getTypeName());return r;}
  if(e.getClass()==BinaryExpression.class){var b=(BinaryExpression)e;need(OPS.contains(b.getOperator()),"unsupported property operator");r.addProperty("kind","binary");r.addProperty("op",b.getOperator());r.add("left",propertyExpr(b.getLeft(),i,reads,depth+1));r.add("right",propertyExpr(b.getRight(),i,reads,depth+1));return r;}
  if(e.getClass()==UnaryExpression.class){var u=(UnaryExpression)e;need("!".equals(u.getOperator()),"unsupported property unary");r.addProperty("kind","unary");r.addProperty("op","!");r.add("operand",propertyExpr(u.getExpression(),i,reads,depth+1));return r;}
  throw new Reject("definitions/calls/opaque property node unsupported");
 }
 public static JsonObject audit(RebecaModel model,PropertyModel properties){
  JsonObject out=new JsonObject();out.addProperty("metadata_only",true);out.addProperty("online_generator_changed",false);out.addProperty("metadata_supported",false);JsonArray actions=new JsonArray();out.add("actions",actions);
  try{
   Index i=new Index(model);
   need(properties.getDefinitions().isEmpty(),"property aliases/definitions unsupported");
   if(properties instanceof org.rebecalang.compiler.propertycompiler.timedrebeca.objectmodel.PropertyModel p)need(p.getTCTLDefinitions().isEmpty(),"temporal properties unsupported");
   else if(properties instanceof org.rebecalang.compiler.propertycompiler.corerebeca.objectmodel.PropertyModel p)need(p.getLTLDefinitions().isEmpty(),"temporal properties unsupported");
   else need(properties.getClass()==PropertyModel.class,"unknown property model");
   need(properties.getAssertionDefinitions().size()==1,"exactly one external state assertion required");var property=properties.getAssertionDefinitions().get(0);need("boolean".equals(property.getExpression().getType().getTypeName()),"property must be boolean");
   Set<List<String>> observed=new LinkedHashSet<>();var predicate=propertyExpr(property.getExpression(),i,observed,0);out.addProperty("property_name",property.getName());out.add("property_reads",new Gson().toJsonTree(observed));out.add("predicate",predicate);
   boolean all=true;
   for(var instance:i.instances.entrySet()){
    // Constructors must also stay within the supported closed-model fragment.
    for(var ctor:instance.getValue().getConstructors()){var f=new Effects(i,instance.getKey(),ctor);f.walk(ctor.getBlock(),0);}
    for(var method:instance.getValue().getMsgsrvs()){
     JsonObject row=new JsonObject();row.add("action",new Gson().toJsonTree(List.of(instance.getKey(),method.getName().toUpperCase(Locale.ROOT))));
     try{var f=new Effects(i,instance.getKey(),method);f.walk(method.getBlock(),0);row.addProperty("complete",true);row.add("reads",new Gson().toJsonTree(f.reads));row.add("writes",new Gson().toJsonTree(f.writes));row.add("sends",new Gson().toJsonTree(f.sends));}
     catch(Reject failure){all=false;row.addProperty("complete",false);row.addProperty("reason",failure.getMessage());}
     actions.add(row);
    }
   }
   out.addProperty("metadata_supported",all);if(!all)out.addProperty("reason","at least one action outside supported fragment; whole experiment reduction disabled");
  }catch(Reject failure){out.addProperty("reason",failure.getMessage());}
  return out;
 }
}
