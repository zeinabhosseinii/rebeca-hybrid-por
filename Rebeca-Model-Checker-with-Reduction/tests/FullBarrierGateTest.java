import org.rebecalang.rmc.ERDGSafetyAnalyzer;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary;

public class FullBarrierGateTest {
 static void check(boolean b){if(!b)throw new AssertionError();}
 public static void main(String[] args){
  RebecaModel m=QuiescenceCertificateTest.model();check(ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  ConstructorDeclaration ctor=new ConstructorDeclaration();ctor.setBlock(new BlockStatement());
  TermPrimary send=QuiescenceCertificateTest.send("Initialize");
  TimedRebecaParentSuffixPrimary timed=new TimedRebecaParentSuffixPrimary();timed.setAfterExpression(new Literal());
  send.setParentSuffixPrimary(timed);ctor.getBlock().getStatements().add(send);
  QuiescenceCertificateTest.actor.getConstructors().add(ctor);
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  check(ERDGSafetyAnalyzer.neverSentAgain(m).get(0).get(1)); // constructor exclusion still valid for separate certificate
  m=QuiescenceCertificateTest.model();TermPrimary now=new TermPrimary();now.setName("now");
  QuiescenceCertificateTest.work.getBlock().getStatements().add(now);
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  m=QuiescenceCertificateTest.model();QuiescenceCertificateTest.work.getBlock().getStatements().add(new ForStatement());
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  m=QuiescenceCertificateTest.model();send=QuiescenceCertificateTest.send("Work");
  timed=new TimedRebecaParentSuffixPrimary();timed.setDeadlineExpression(new Literal());send.setParentSuffixPrimary(timed);
  QuiescenceCertificateTest.work.getBlock().getStatements().add(send);
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  m=QuiescenceCertificateTest.model();QuiescenceCertificateTest.actor.getAnnotations().add(new Annotation());
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  m=QuiescenceCertificateTest.model();m.getRebecaCode().getEnvironmentVariables().add(new FieldDeclaration());
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  m=QuiescenceCertificateTest.model();ConstructorDeclaration extension=new ConstructorDeclaration() {};
  extension.setBlock(new BlockStatement());QuiescenceCertificateTest.actor.getConstructors().add(extension);
  check(!ERDGSafetyAnalyzer.supportsFullExpansionBarriers(m));
  System.out.println("PASS: real AST barrier gate includes constructors; timing/now/deadlines/unknown syntax reject");
 }
}
