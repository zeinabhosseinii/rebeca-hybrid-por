package org.rebecalang.rmc;

import java.util.*;
import org.rebecalang.compiler.modelcompiler.corerebeca.CoreRebecaLabelUtility;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary;

/** Per-analysis inductive int32 proof. Unsupported input fails closed.
 * Certifies source assertion truth only; does not itself authorize reduction.
 */
public final class CounterInvariantCertificate {
 private CounterInvariantCertificate() {}
 public static boolean provesAllAssertions(RebecaModel model) {
  try { return new CounterInvariantCertificate().verify(model); }
  catch (RuntimeException unsupported) { return false; }
 }
 private boolean untimed(ParentSuffixPrimary suffix) {
  if(suffix.getClass()==ParentSuffixPrimary.class)return true;
  if(suffix.getClass()!=TimedRebecaParentSuffixPrimary.class)return false;
  var timed=(TimedRebecaParentSuffixPrimary)suffix;
  return timed.getAfterExpression()==null && timed.getDeadlineExpression()==null;
 }
 static class Reject extends RuntimeException {Reject(String s){super(s);}}
 record Range(long lo,long hi){Range{if(lo>hi || lo<Integer.MIN_VALUE || hi>Integer.MAX_VALUE)throw new Reject("empty interval or int32 overflow");}}
 record Test(String field,String op,long value){}
 private Set<String> fields; private Map<String,Range> invariant; private int assertions,steps;
 private void require(boolean yes,String why){if(!yes)throw new Reject(why);}
 private String field(Expression e){
  require(e!=null && e.getClass()==TermPrimary.class,"expected local scalar state field");TermPrimary t=(TermPrimary)e;
  require(CoreRebecaLabelUtility.STATE_VARIABLE.equals(t.getLabel()) && fields.contains(t.getName()) && t.getIndices().isEmpty() && t.getParentSuffixPrimary()==null,"nonlocal, indexed or unresolved field");return t.getName();
 }
 private long constant(Expression e){return constant(e,0);}
 private long constant(Expression e,int depth){
  require(depth<=128,"constant depth budget");
  if(e!=null && e.getClass()==UnaryExpression.class && "-".equals(((UnaryExpression)e).getOperator())){long k=-constant(((UnaryExpression)e).getExpression(),depth+1);return new Range(k,k).lo();}
  require(e!=null && e.getClass()==Literal.class && e.getType()!=null && Set.of("byte","short","int").contains(e.getType().getTypeName()),"expected int32 constant");
  try{long value=Long.parseLong(((Literal)e).getLiteralValue());return new Range(value,value).lo();}catch(NumberFormatException ex){throw new Reject("invalid integer literal");}
 }
 private Test test(Expression e){
  require(e!=null && e.getClass()==BinaryExpression.class,"unsupported branch/predicate shape");BinaryExpression b=(BinaryExpression)e;
  require(Set.of("<","<=",">",">=","==","!=").contains(b.getOperator()),"unsupported comparison");return new Test(field(b.getLeft()),b.getOperator(),constant(b.getRight()));
 }
 private Range constraint(Test t,Range old){
  long lo=old.lo(),hi=old.hi(),k=t.value();
  switch(t.op()){case ">="->lo=Math.max(lo,k);case ">"->lo=Math.max(lo,k+1);case "<="->hi=Math.min(hi,k);case "<"->hi=Math.min(hi,k-1);case "=="->{lo=Math.max(lo,k);hi=Math.min(hi,k);}default->throw new Reject("unsupported assertion comparison: "+t.op());}
  return new Range(lo,hi);
 }
 private void bounds(Expression e){bounds(e,0);}
 private void bounds(Expression e,int depth){
  require(depth<=128 && ++steps<=100000,"predicate budget");
  if(e!=null && e.getClass()==BinaryExpression.class && "&&".equals(((BinaryExpression)e).getOperator())){bounds(((BinaryExpression)e).getLeft(),depth+1);bounds(((BinaryExpression)e).getRight(),depth+1);return;}
  Test t=test(e);invariant.put(t.field(),constraint(t,invariant.getOrDefault(t.field(),new Range(Integer.MIN_VALUE,Integer.MAX_VALUE))));
 }
 private TermPrimary call(Statement s){require(s.getClass()==TermPrimary.class,"unsupported call shape");TermPrimary t=(TermPrimary)s;require(t.getParentSuffixPrimary()!=null && untimed(t.getParentSuffixPrimary()),"timed/opaque/missing call suffix");return t;}
 private boolean assertion(TermPrimary t){return "assertion".equals(t.getName()) && CoreRebecaLabelUtility.BUILT_IN_METHOD.equals(t.getLabel());}
 private Expression argument(TermPrimary t){require(t.getParentSuffixPrimary().getArguments().size()==1,"assertion arity outside fragment");return t.getParentSuffixPrimary().getArguments().get(0);}
 private void expressionShape(Expression e){expressionShape(e,0);}
 private void expressionShape(Expression e,int depth){
  require(depth<=128 && ++steps<=100000,"expression budget");
  if(e!=null && e.getClass()==Literal.class){constant(e);return;}
  if(e!=null && e.getClass()==TermPrimary.class){field(e);return;}
  if(e!=null && e.getClass()==UnaryExpression.class && "-".equals(((UnaryExpression)e).getOperator())){expressionShape(((UnaryExpression)e).getExpression(),depth+1);return;}
  if(e!=null && e.getClass()==BinaryExpression.class){BinaryExpression b=(BinaryExpression)e;require(Set.of("+","-").contains(b.getOperator()),"unsupported arithmetic");expressionShape(b.getLeft(),depth+1);expressionShape(b.getRight(),depth+1);return;}
  throw new Reject("unsupported expression/side effect");
 }
 private void send(Statement s){
  TermPrimary t;
  if(s.getClass()==DotPrimary.class){DotPrimary d=(DotPrimary)s;require(d.getLeft()!=null && d.getLeft().getClass()==TermPrimary.class,"computed receiver");TermPrimary receiver=(TermPrimary)d.getLeft();
   require(receiver.getIndices().isEmpty() && receiver.getParentSuffixPrimary()==null && (CoreRebecaLabelUtility.KNOWNREBEC_VARIABLE.equals(receiver.getLabel()) || "self".equals(receiver.getName())),"nonlocal/computed receiver");t=call(d.getRight());
  }else t=call(s);
  require(CoreRebecaLabelUtility.MSGSRV.equals(t.getLabel()) && t.getParentSuffixPrimary().getArguments().isEmpty(),"only nullary untimed message sends supported");
 }
 private void validate(Statement s,int depth){
  require(depth<=128 && ++steps<=100000,"structural budget");if(s==null)return;
  if(s.getClass()==BlockStatement.class){for(Statement child:((BlockStatement)s).getStatements())validate(child,depth+1);return;}
  if(s.getClass()==ConditionalStatement.class){ConditionalStatement c=(ConditionalStatement)s;test(c.getCondition());validate(c.getStatement(),depth+1);validate(c.getElseStatement(),depth+1);return;}
  if(s.getClass()==BinaryExpression.class){BinaryExpression b=(BinaryExpression)s;require("=".equals(b.getOperator()),"only plain state assignments supported");field(b.getLeft());expressionShape(b.getRight());return;}
  if(s.getClass()==TermPrimary.class && assertion(call(s))){assertions++;bounds(argument((TermPrimary)s));return;}
  if(s.getClass()==DotPrimary.class || s.getClass()==TermPrimary.class){send(s);return;}
  throw new Reject("unsupported statement: "+s.getClass().getSimpleName());
 }
 private Range eval(Expression e,Map<String,Range> env){
  if(e.getClass()==Literal.class){long k=constant(e);return new Range(k,k);}
  if(e.getClass()==TermPrimary.class){Range r=env.get(field(e));require(r!=null,"read before explicit initialization");return r;}
  if(e.getClass()==UnaryExpression.class){Range r=eval(((UnaryExpression)e).getExpression(),env);return new Range(-r.hi(),-r.lo());}
  BinaryExpression b=(BinaryExpression)e;Range l=eval(b.getLeft(),env),r=eval(b.getRight(),env);
  return "+".equals(b.getOperator())?new Range(l.lo()+r.lo(),l.hi()+r.hi()):new Range(l.lo()-r.hi(),l.hi()-r.lo());
 }
 private Map<String,Range> refine(Map<String,Range> env,Test t,boolean yes){
  Range old=env.get(t.field());require(old!=null,"condition before initialization");String op=t.op();long k=t.value();
  if(!yes)op=switch(op){case "<"->">=";case "<="->">";case ">"->"<=";case ">="->"<";case "=="->"!=";case "!="->"==";default->throw new Reject("bad comparator");};
  long lo=old.lo(),hi=old.hi();
  switch(op){case "<"->hi=Math.min(hi,k-1);case "<="->hi=Math.min(hi,k);case ">"->lo=Math.max(lo,k+1);case ">="->lo=Math.max(lo,k);case "=="->{lo=Math.max(lo,k);hi=Math.min(hi,k);}case "!="->{if(lo==k)lo++;if(hi==k)hi--;}}
  if(lo>hi)return null;Map<String,Range> next=new HashMap<>(env);next.put(t.field(),new Range(lo,hi));return next;
 }
 private boolean holds(Expression e,Map<String,Range> env){
  if(e.getClass()==BinaryExpression.class && "&&".equals(((BinaryExpression)e).getOperator()))return holds(((BinaryExpression)e).getLeft(),env)&&holds(((BinaryExpression)e).getRight(),env);
  Test t=test(e);Range r=env.get(t.field());require(r!=null,"assertion before initialization");long k=t.value();
  return switch(t.op()){case "<"->r.hi()<k;case "<="->r.hi()<=k;case ">"->r.lo()>k;case ">="->r.lo()>=k;case "=="->r.lo()==k&&r.hi()==k;default->false;};
 }
 private List<Map<String,Range>> execute(Statement s,List<Map<String,Range>> paths,int depth){
  require(depth<=128 && paths.size()<=256 && ++steps<=200000,"abstract execution budget");if(s==null)return paths;
  if(s.getClass()==BlockStatement.class){for(Statement child:((BlockStatement)s).getStatements())paths=execute(child,paths,depth+1);return paths;}
  List<Map<String,Range>> result=new ArrayList<>();
  for(Map<String,Range> env:paths){
   if(s.getClass()==ConditionalStatement.class){ConditionalStatement c=(ConditionalStatement)s;Test t=test(c.getCondition());
    Map<String,Range> yes=refine(env,t,true),no=refine(env,t,false);
    if(yes!=null)result.addAll(execute(c.getStatement(),List.of(yes),depth+1));if(no!=null)result.addAll(execute(c.getElseStatement(),List.of(no),depth+1));
   }else if(s.getClass()==BinaryExpression.class){BinaryExpression b=(BinaryExpression)s;Map<String,Range> next=new HashMap<>(env);next.put(field(b.getLeft()),eval(b.getRight(),env));result.add(next);
   }else if(s.getClass()==TermPrimary.class && assertion((TermPrimary)s)){require(holds(argument((TermPrimary)s),env),"assertion not established at its program point");result.add(env);
   }else result.add(env); // prevalidated nullary asynchronous send, no local effect
   require(result.size()<=256,"path budget");
  }
  return result;
 }
 private void preserved(Map<String,Range> env){for(String name:fields){Range actual=env.get(name),claim=invariant.get(name);require(actual!=null && actual.lo()>=claim.lo() && actual.hi()<=claim.hi(),"invariant not preserved for "+name);}}
 private boolean verify(RebecaModel model) {
   RebecaCode code=model.getRebecaCode();require(code.getGlobalVariables().isEmpty()&&code.getEnvironmentVariables().isEmpty()&&code.getFeatureVariables().isEmpty()&&code.getRecordDeclaration().isEmpty()&&code.getInterfaceDeclaration().isEmpty(),"unsupported global/model declarations");
   Set<String> instances=new HashSet<>();for(MainRebecDefinition instance:code.getMainDeclaration().getMainRebecDefinition())require(instances.add(instance.getName()),"duplicate instance");
   for(MainRebecDefinition instance:code.getMainDeclaration().getMainRebecDefinition()){require(instance.getAnnotations().isEmpty(),"annotated main instance outside fragment");for(Expression binding:instance.getBindings())require(binding.getClass()==TermPrimary.class && instances.contains(((TermPrimary)binding).getName()),"only resolved static instance bindings supported");}
   for(ReactiveClassDeclaration actor:code.getReactiveClassDeclaration()){
    require(actor.getClass()==ReactiveClassDeclaration.class && actor.getExtends()==null && actor.getImplements().isEmpty() && actor.getSynchMethods().isEmpty() && actor.getAnnotations().isEmpty(),"unsupported actor shape");
    fields=new TreeSet<>();invariant=new TreeMap<>();
    for(FieldDeclaration declaration:actor.getStatevars()){
     require(declaration.getType()!=null && "int".equals(declaration.getType().getTypeName()),"only int state fields supported");
     for(VariableDeclarator variable:declaration.getVariableDeclarators()){require(variable.getVariableInitializer()==null,"field initializer outside fragment");require(fields.add(variable.getVariableName()),"duplicate field");}
    }
    List<MethodDeclaration> methods=new ArrayList<>();require(actor.getConstructors().size()==1,"exactly one explicit constructor required");methods.addAll(actor.getConstructors());methods.addAll(actor.getMsgsrvs());
    for(MethodDeclaration method:methods){require((method.getClass()==ConstructorDeclaration.class||method.getClass()==MsgsrvDeclaration.class) && method.getFormalParameters().isEmpty() && method.getAnnotations().isEmpty() && method.getBlock()!=null,"unsupported method shape/parameters");validate(method.getBlock(),0);}
    for(String name:fields){require(invariant.containsKey(name),"no candidate bounds for "+name);Range r=invariant.get(name);require(r.lo()>Integer.MIN_VALUE && r.hi()<Integer.MAX_VALUE,"both finite explicit bounds required");}
    for(MethodDeclaration method:methods){Map<String,Range> entry=method instanceof ConstructorDeclaration?new HashMap<>():new HashMap<>(invariant);List<Map<String,Range>> exits=execute(method.getBlock(),List.of(entry),0);require(!exits.isEmpty(),"empty abstract method domain");for(var exit:exits)preserved(exit);}
   }
   require(assertions>0,"no assertions to certify"); return true;
 }
}
