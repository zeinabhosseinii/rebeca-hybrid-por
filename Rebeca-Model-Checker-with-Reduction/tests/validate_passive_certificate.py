#!/usr/bin/env python3
"""Test actual metadata implementation against typed AST fixtures, not the external JAR."""
import os,shutil,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/java/org/rebecalang/rmc/ERDGSafetyAnalyzer.java').read_text()
code=s[s.index('    public static final class LocalActionMetadata'):s.index('    // ── AST traversal helpers')]
old=(root/'tests/validate_local_certificate.py').read_text()
fixture=old.split("fixture=r'''",1)[1].split("'''.replace('CODE',code)",1)[0]
fixture=fixture.replace('class LocalCertificateFixture','class PassiveCertificateFixture')
fixture=fixture.replace('String name;Object suffix;List<Expression> indices', 'String name;ParentSuffixPrimary suffix;int label=0;List<Expression> indices')
fixture=fixture.replace('Object getParentSuffixPrimary(){return suffix;}', 'ParentSuffixPrimary getParentSuffixPrimary(){return suffix;}int getLabel(){return label;}')
fixture=fixture.replace(' static class Send extends Statement {}', ''' static class Send extends Statement {}
 static class ParentSuffixPrimary {List<Expression> args=new ArrayList<>();List<Expression> getArguments(){return args;}}
 static class TimedRebecaParentSuffixPrimary extends ParentSuffixPrimary {
  Expression after,deadline;Expression getAfterExpression(){return after;}Expression getDeadlineExpression(){return deadline;}
 }
 static class CoreRebecaLabelUtility {static final int MSGSRV=1;}
 static class DotPrimary extends Expression {
  Expression left,right;DotPrimary(Expression a,Expression b){left=a;right=b;}
  Expression getLeft(){return left;}Expression getRight(){return right;}
 }
''')
fixture=fixture.replace('List<Object> params=new ArrayList<>();Statement body;', 'String name="M";List<Object> params=new ArrayList<>();Statement body;')
fixture=fixture.replace('List<Object> getFormalParameters()', 'String getName(){return name;}List<Object> getFormalParameters()')
fixture=fixture.replace('Object parent;List<MsgsrvDeclaration>', 'String name="C";List<String> known=new ArrayList<>();Object parent;List<MsgsrvDeclaration>')
fixture=fixture.replace('String getName(){return "C";}', 'String getName(){return name;}')
a=fixture.index(' static class RebecaModel');b=fixture.index(' CODE',a)
fixture=fixture[:a]+''' static class RebecaModel {
  List<ReactiveClassDeclaration> classes=new ArrayList<>();Map<String,String> types=new LinkedHashMap<>();
  Map<String,List<String>> bindings=new HashMap<>();
 }
 static class ModelIndex {
  List<String> instanceNames;Map<String,Integer> instanceIndex=new HashMap<>();Map<String,String> instanceTypeName;
  Map<String,ReactiveClassDeclaration> typeToRcd=new HashMap<>();Map<String,Integer> startMsgId=new HashMap<>();
  Map<String,List<String>> fullKnownRebecNames=new HashMap<>(),instanceBindings;int maxMsgId=2,instanceCount;
  ModelIndex(RebecaModel m){
   instanceNames=new ArrayList<>(m.types.keySet());instanceTypeName=m.types;instanceBindings=m.bindings;instanceCount=instanceNames.size();
   for(int i=0;i<instanceNames.size();i++)instanceIndex.put(instanceNames.get(i),i);
   for(var c:m.classes){typeToRcd.put(c.name,c);startMsgId.put(c.name,1);fullKnownRebecNames.put(c.name,c.known);}
  }
 }
 static int key(int i,int m){return i*1000+m;}static int instanceOf(int k){return k/1000;}
 static String resolveTargetInstance(Expression left,String inst,List<String> names,List<String> bindings,ModelIndex idx){
  int at=names.indexOf(((TermPrimary)left).name);return at<0?null:bindings.get(at);
 }
 static Integer resolveMessageId(String name,String type,ModelIndex idx){
  var c=idx.typeToRcd.get(type);if(c==null)return null;
  for(int k=0;k<c.methods.size();k++)if(c.methods.get(k).name.equals(name))return k+1;return null;
 }
'''+fixture[b:]
a=fixture.index(' static BinaryExpression assign');fixture=fixture[:a]+r'''
 static BinaryExpression assign(String name,String value){return new BinaryExpression(new TermPrimary(name),new Literal(value));}
 static DotPrimary send(String receiver){
  TermPrimary call=new TermPrimary("Nop");call.label=CoreRebecaLabelUtility.MSGSRV;call.suffix=new TimedRebecaParentSuffixPrimary();
  return new DotPrimary(new TermPrimary(receiver),call);
 }
 static RebecaModel model(){
  RebecaModel m=new RebecaModel();ReactiveClassDeclaration c=new ReactiveClassDeclaration();c.name="C";
  c.fields.add(new FieldDeclaration(new Type("int"),"x"));c.fields.add(new FieldDeclaration(new Type("int"),"y"));
  c.known=List.of("P","Q");c.methods.add(new MsgsrvDeclaration(new BlockStatement(assign("x","1"),send("P"))));
  c.methods.add(new MsgsrvDeclaration(new BlockStatement(assign("y","2"),send("Q"))));
  c.methods.get(0).name="A";c.methods.get(1).name="B";m.classes.add(c);m.types.put("root","C");m.bindings.put("root",new ArrayList<>(List.of("one","two")));
  for(String n:List.of("one","two")){
   ReactiveClassDeclaration sink=new ReactiveClassDeclaration();sink.name=n;sink.methods.add(new MsgsrvDeclaration(new BlockStatement()));sink.methods.get(0).name="Nop";
   m.classes.add(sink);m.types.put(n,n);m.bindings.put(n,List.of());
  }
  return m;
 }
 static void check(boolean x){if(!x)throw new AssertionError();}
 static PassiveSendMetadata meta(RebecaModel m){return passiveSendActions(m);}
 public static void main(String[] args){
  RebecaModel m=model();PassiveSendMetadata c=meta(m);
  check(c.safe.get(0).get(1)&&c.safe.get(0).get(2));check(c.passive.get(1).get(1));
  check(c.independent.get(0).get(1).get(2)&&c.independent.get(0).get(2).get(1));
  check(c.targetActor.get(0).get(1)==1&&c.targetActor.get(0).get(2)==2);
  m=model();m.bindings.get("root").set(1,"one");check(!meta(m).independent.get(0).get(1).get(2));
  m=model();m.classes.get(0).methods.get(1).body=new BlockStatement(assign("x","2"),send("Q"));check(!meta(m).independent.get(0).get(1).get(2));
  m=model();m.bindings.get("root").set(0,"root");check(!meta(m).safe.get(0).get(1));
  m=model();m.classes.get(1).fields.add(new FieldDeclaration(new Type("int"),"z"));m.classes.get(1).methods.get(0).body=new BlockStatement(assign("z","1"));
  check(!meta(m).safe.get(0).get(1));
  for(int variant=0;variant<6;variant++){
   m=model();DotPrimary call=send("P");TermPrimary invocation=(TermPrimary)call.right;
   if(variant==0)((TimedRebecaParentSuffixPrimary)invocation.suffix).after=new Literal("0");
   if(variant==1)((TimedRebecaParentSuffixPrimary)invocation.suffix).deadline=new Literal("1");
   if(variant==2)invocation.suffix.args.add(new Literal("1"));
   if(variant==3)invocation.label=0;
   if(variant==4)((TermPrimary)call.left).name="unknown";
   if(variant==5)invocation.name="Unknown";
   m.classes.get(0).methods.get(0).body=new BlockStatement(assign("x","1"),call);check(!meta(m).safe.get(0).get(1));
  }
  m=model();m.classes.get(0).methods.get(0).body=new BlockStatement(send("P"),send("Q"));check(!meta(m).safe.get(0).get(1));
  System.out.println("PASS: passive destination resolution, disjoint queues/writes, feedback/active/timed/argument/unknown/multiple-send fallback");
 }
}
'''
fixture=fixture.replace(' CODE',code)
javac=shutil.which('javac') or str(Path(os.environ.get('JAVA_HOME',''))/'bin/javac')
java=shutil.which('java') or str(Path(os.environ.get('JAVA_HOME',''))/'bin/java')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'PassiveCertificateFixture.java';p.write_text(fixture)
 subprocess.run([javac,'-d',tmp,str(p)],check=True)
 subprocess.run([java,'-cp',tmp,'PassiveCertificateFixture'],check=True)
