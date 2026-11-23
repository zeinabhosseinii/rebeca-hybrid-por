import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import com.google.gson.*;
import org.rebecalang.compiler.CompilerConfig;
import org.rebecalang.compiler.modelcompiler.RebecaModelCompiler;
import org.rebecalang.compiler.propertycompiler.PropertyCompiler;
import org.rebecalang.compiler.utils.*;
import org.rebecalang.rmc.RMCConfig;
import org.rebecalang.rmc.PropertyObservationMetadata;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
/** Diagnostic adapter for the production metadata implementation; not an independent permit. */
public class PropertyEffectAstAudit {
 static class Reject extends RuntimeException {Reject(String why){super(why);}}
 static void need(boolean ok,String why){if(!ok)throw new Reject(why);}
 static String sha(Path p)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)));}
 public static void main(String[] args)throws Exception{
  if(args.length!=3)throw new IllegalArgumentException("model.rebeca property.property metadata.json");JsonObject result;
  try(var c=new AnnotationConfigApplicationContext(CompilerConfig.class,RMCConfig.class)){
   var errors=c.getBean(ExceptionContainer.class);errors.clear();var model=c.getBean(RebecaModelCompiler.class).compileRebecaFile(Path.of(args[0]).toFile(),Set.of(CompilerExtension.TIMED_REBECA),CoreVersion.CORE_2_3);need(errors.exceptionsIsEmpty(),"model compilation failed");
   var property=c.getBean(PropertyCompiler.class).compilePropertyFile(Path.of(args[1]).toFile(),model.getFirst(),Set.of(CompilerExtension.TIMED_REBECA));need(errors.exceptionsIsEmpty(),"property compilation failed");result=PropertyObservationMetadata.audit(model.getFirst(),property);result.addProperty("actor_local_runtime_certified",PropertyObservationMetadata.supportsActorLocalRuntime(model.getFirst(),property));
  }catch(Reject failure){result=new JsonObject();result.addProperty("metadata_supported",false);result.addProperty("reason",failure.getMessage());result.addProperty("diagnostic_only",true);result.addProperty("online_generator_changed",false);}
  result.addProperty("source_sha256",sha(Path.of(args[0])));result.addProperty("property_sha256",sha(Path.of(args[1])));Files.createDirectories(Path.of(args[2]).toAbsolutePath().getParent());Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n");
 }
}
