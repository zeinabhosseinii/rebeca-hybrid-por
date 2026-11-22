import java.util.*;
import org.rebecalang.rmc.ERDGSafetyAnalyzer;
import org.rebecalang.compiler.modelcompiler.corerebeca.CoreRebecaLabelUtility;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;
import org.rebecalang.compiler.modelcompiler.timedrebeca.objectmodel.TimedRebecaParentSuffixPrimary;

/** Tests the compiled analyzer against the actual compiler AST classes. */
public class QuiescenceCertificateTest {
    static ReactiveClassDeclaration actor;
    static MsgsrvDeclaration initialize, work;
    static RebecaModel model() {
        RebecaModel model = new RebecaModel();
        RebecaCode code = new RebecaCode(); model.setRebecaCode(code);
        actor = new ReactiveClassDeclaration(); actor.setName("Actor");
        code.getReactiveClassDeclaration().add(actor);
        initialize = method("Initialize"); work = method("Work");
        actor.getMsgsrvs().add(initialize); actor.getMsgsrvs().add(work);
        MainDeclaration main = new MainDeclaration(); code.setMainDeclaration(main);
        MainRebecDefinition instance = new MainRebecDefinition(); instance.setName("Root");
        instance.setType(new Type() { public String getTypeName() { return "Actor"; } });
        main.getMainRebecDefinition().add(instance);
        return model;
    }
    static MsgsrvDeclaration method(String name) {
        MsgsrvDeclaration m = new MsgsrvDeclaration(); m.setName(name); m.setBlock(new BlockStatement()); return m;
    }
    static TermPrimary send(String name) {
        TermPrimary t = new TermPrimary(); t.setName(name);
        t.setLabel(CoreRebecaLabelUtility.MSGSRV); t.setParentSuffixPrimary(new ParentSuffixPrimary()); return t;
    }
    static boolean certified(RebecaModel model) {
        return ERDGSafetyAnalyzer.neverSentAgain(model).get(0).get(1);
    }
    static void check(boolean ok, String text) { if (!ok) throw new AssertionError(text); }
    public static void main(String[] args) {
        RebecaModel m = model();
        // Constructor-only sends are pending initial messages, not runtime senders.
        ConstructorDeclaration ctor = new ConstructorDeclaration(); ctor.setBlock(new BlockStatement());
        ctor.getBlock().getStatements().add(send("Initialize")); actor.getConstructors().add(ctor);
        check(certified(m), "constructor-only handler");
        work.getBlock().getStatements().add(send("Initialize"));
        check(!certified(m), "self/unqualified resend");
        m = model();
        DotPrimary dot = new DotPrimary(); TermPrimary receiver = new TermPrimary(); receiver.setName("sender");
        dot.setLeft(receiver); dot.setRight(send("Initialize")); work.getBlock().getStatements().add(dot);
        check(!certified(m), "sender/alias receiver");
        m = model();
        ConditionalStatement conditional = new ConditionalStatement(); conditional.setCondition(new Literal());
        conditional.setStatement(send("Initialize")); work.getBlock().getStatements().add(conditional);
        check(!certified(m), "conditional send");
        m = model();
        TermPrimary call = send("Work"); TimedRebecaParentSuffixPrimary suffix = new TimedRebecaParentSuffixPrimary();
        suffix.setAfterExpression(send("Initialize")); call.setParentSuffixPrimary(suffix);
        work.getBlock().getStatements().add(call);
        check(!certified(m), "timing expression traversed");
        m = model(); work.getBlock().getStatements().add(new ForStatement());
        check(!certified(m), "unsupported syntax disables certificate");
        m = model(); actor.getSynchMethods().add(new SynchMethodDeclaration());
        check(!certified(m), "synchronous methods disable certificate");
        m = model(); actor.setExtends(new Type() { public String getTypeName() { return "Parent"; } });
        check(!certified(m), "inheritance disables certificate");
        m = model(); TermPrimary unknown = new TermPrimary(); unknown.setName("external");
        unknown.setParentSuffixPrimary(new ParentSuffixPrimary()); work.getBlock().getStatements().add(unknown);
        check(!certified(m), "unknown calls disable certificate");
        m = model(); TermPrimary incomplete = send("Initialize"); incomplete.setParentSuffixPrimary(null);
        work.getBlock().getStatements().add(incomplete);
        check(!certified(m), "incomplete call fails closed");
        System.out.println("PASS: real Java AST certificate; runtime resend, conditions, aliases, timing and unsupported syntax");
    }
}
