#!/usr/bin/env python3
"""Exercise the actual certificate code with a minimal typed-AST fixture.
This checks whitelist logic/Java syntax, not compatibility with the external compiler JAR.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/java/org/rebecalang/rmc/ERDGSafetyAnalyzer.java').read_text()
a=s.index('    public static final class LocalActionMetadata');b=s.index('    // ── AST traversal helpers',a)
code=s[a:b]
fixture=r'''
import java.util.*;
class LocalCertificateFixture {
 static class Statement {}
 static class Expression extends Statement {}
 static class BlockStatement extends Statement {
  List<Statement> body; BlockStatement(Statement...s){body=Arrays.asList(s);}
  List<Statement> getStatements(){return body;}
 }
 static class BinaryExpression extends Expression {
  Expression l,r;String op="="; BinaryExpression(Expression a,Expression b){l=a;r=b;}
  String getOperator(){return op;} Expression getLeft(){return l;}Expression getRight(){return r;}
 }
 static class TermPrimary extends Expression {
  String name;Object suffix;List<Expression> indices=new ArrayList<>();
  TermPrimary(String n){name=n;}String getName(){return name;}Object getParentSuffixPrimary(){return suffix;}
  List<Expression> getIndices(){return indices;}
 }
 static class Literal extends Expression {
  String value;Literal(String v){value=v;}String getLiteralValue(){return value;}
 }
 static class Send extends Statement {}
 static class Type {String name;Type(String n){name=n;}String getTypeName(){return name;}}
 static class ArrayType extends Type {ArrayType(){super("int");}}
 static class VariableDeclarator {String name;VariableDeclarator(String n){name=n;}String getVariableName(){return name;}}
 static class FieldDeclaration {
  Type t;List<VariableDeclarator> vars;FieldDeclaration(Type t,String n){this.t=t;vars=List.of(new VariableDeclarator(n));}
  Type getType(){return t;}List<VariableDeclarator> getVariableDeclarators(){return vars;}
 }
 static class MsgsrvDeclaration {
  List<Object> params=new ArrayList<>();Statement body;MsgsrvDeclaration(Statement b){body=b;}
  List<Object> getFormalParameters(){return params;}Statement getBlock(){return body;}
 }
 static class ReactiveClassDeclaration {
  Object parent;List<MsgsrvDeclaration> methods=new ArrayList<>();List<FieldDeclaration> fields=new ArrayList<>();
  Object getExtends(){return parent;}String getName(){return "C";}
  List<MsgsrvDeclaration> getMsgsrvs(){return methods;}List<FieldDeclaration> getStatevars(){return fields;}
 }
 static class RebecaModel {ReactiveClassDeclaration rc;RebecaModel(ReactiveClassDeclaration r){rc=r;}}
 static class ModelIndex {
  List<String> instanceNames=List.of("only");Map<String,String> instanceTypeName=Map.of("only","C");
  Map<String,ReactiveClassDeclaration> typeToRcd;Map<String,Integer> startMsgId=Map.of("C",1);int maxMsgId=2;
  ModelIndex(RebecaModel m){typeToRcd=Map.of("C",m.rc);}
 }
 CODE
 static BinaryExpression assign(String name,String value){return new BinaryExpression(new TermPrimary(name),new Literal(value));}
 static ReactiveClassDeclaration model(){
  ReactiveClassDeclaration c=new ReactiveClassDeclaration();
  c.fields.add(new FieldDeclaration(new Type("int"),"x"));c.fields.add(new FieldDeclaration(new Type("int"),"y"));
  c.methods.add(new MsgsrvDeclaration(new BlockStatement(assign("x","1"))));
  c.methods.add(new MsgsrvDeclaration(new BlockStatement(assign("y","2"))));return c;
 }
 static void check(boolean b){if(!b)throw new AssertionError();}
 public static void main(String[] args){
  ReactiveClassDeclaration c=model();LocalActionMetadata m=isolatedLocalActions(new RebecaModel(c));
  check(m.safe.get(0).equals(List.of(false,true,true)));
  check(m.independent.get(0).get(1).get(2));check(m.independent.get(0).get(2).get(1));
  check(!m.independent.get(0).get(1).get(1));
  c.methods.get(1).body=new BlockStatement(assign("x","2"));
  check(!isolatedLocalActions(new RebecaModel(c)).independent.get(0).get(1).get(2));
  for(Statement unsafe: List.of(new Send(),new BinaryExpression(new TermPrimary("x"),new TermPrimary("y")),
      assign("x","2147483648"),assign("x","1.25"),assign("unknown","1"))){
   c=model();c.methods.get(1).body=new BlockStatement(unsafe);
   check(!isolatedLocalActions(new RebecaModel(c)).safe.get(0).get(2));
  }
  c=model();c.methods.get(1).params.add(new Object());check(!isolatedLocalActions(new RebecaModel(c)).safe.get(0).get(2));
  c=model();c.parent=new Object();check(!isolatedLocalActions(new RebecaModel(c)).safe.get(0).get(1));
  c=model();c.fields.set(1,new FieldDeclaration(new ArrayType(),"y"));check(!isolatedLocalActions(new RebecaModel(c)).safe.get(0).get(2));
  c=model();TermPrimary indexed=new TermPrimary("y");indexed.indices.add(new Literal("0"));
  c.methods.get(1).body=new BlockStatement(new BinaryExpression(indexed,new Literal("1")));
  check(!isolatedLocalActions(new RebecaModel(c)).safe.get(0).get(2));
  System.out.println("PASS: constant-local whitelist, disjoint/shared writes, sends/reads/arrays/parameters/inheritance fallback");
 }
}
'''.replace('CODE',code)
javac=shutil.which('javac') or str(Path(os.environ.get('JAVA_HOME',''))/'bin/javac')
java=shutil.which('java') or str(Path(os.environ.get('JAVA_HOME',''))/'bin/java')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'LocalCertificateFixture.java';p.write_text(fixture)
 subprocess.run([javac,'-d',tmp,str(p)],check=True)
 subprocess.run([java,'-cp',tmp,'LocalCertificateFixture'],check=True)
