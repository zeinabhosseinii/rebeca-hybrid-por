import java.nio.file.*;
import java.util.*;
import com.google.gson.*;
import org.rebecalang.compiler.CompilerConfig;
import org.rebecalang.compiler.modelcompiler.RebecaModelCompiler;
import org.rebecalang.compiler.utils.*;
import org.rebecalang.rmc.*;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

public class ApplicationCertificateProbe {
 public static void main(String[] args)throws Exception{
  try(var context=new AnnotationConfigApplicationContext(CompilerConfig.class,RMCConfig.class)){
   var errors=context.getBean(ExceptionContainer.class);errors.clear();var pair=context.getBean(RebecaModelCompiler.class).compileRebecaFile(Path.of(args[0]).toFile(),Set.of(CompilerExtension.TIMED_REBECA),CoreVersion.CORE_2_3);
   if(!errors.exceptionsIsEmpty())throw new IllegalArgumentException("Model compilation failed");
   JsonObject report=CounterInvariantAudit.audit(pair.getFirst());
   report.addProperty("production_invariant_certificate",CounterInvariantCertificate.provesAllAssertions(pair.getFirst()));
   report.addProperty("structural_barrier_gate",ERDGSafetyAnalyzer.supportsFullExpansionBarriers(pair.getFirst()));
   Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(report)+"\n");
  }
 }
}
