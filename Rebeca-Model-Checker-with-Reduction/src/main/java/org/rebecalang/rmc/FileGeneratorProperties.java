package org.rebecalang.rmc;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import org.rebecalang.compiler.utils.CoreVersion;

public class FileGeneratorProperties {
	protected boolean safeMode;
	protected boolean reduction;
	protected boolean ariaReduction;
	protected boolean symmetry;

	// Per-class set of msgsrv names whose bodies never read 'sender'.
	// Populated only when --aria is active; used to zero senderQueue bytes
	// during state marshaling so different-sender same-message states merge.
	private Map<String, Set<String>> senderIndepMsgsrvNames = new HashMap<>();
	public Map<String, Set<String>> getSenderIndepMsgsrvNames() { return senderIndepMsgsrvNames; }
	public void setSenderIndepMsgsrvNames(Map<String, Set<String>> m) { this.senderIndepMsgsrvNames = m; }

	// Per-class set of msgsrv names whose ALL formal parameters are transitively dead
	// (they never affect any live state variable or send argument).
	// Populated only when --aria is active; used to zero paramQueue bytes
	// during state marshaling so queue entries with different dead-param values merge.
	private Map<String, Set<String>> deadParamMsgsrvsByClass = new HashMap<>();
	public Map<String, Set<String>> getDeadParamMsgsrvsByClass() { return deadParamMsgsrvsByClass; }
	public void setDeadParamMsgsrvsByClass(Map<String, Set<String>> m) { this.deadParamMsgsrvsByClass = m; }
	
	protected String exportStateSpaceTargetFile;
	
	protected boolean debugTrace;
	protected boolean debugAll;
	
	protected boolean progressReport;
	
	protected CoreVersion coreVersion;
	
	protected boolean traceGenerator;
	
	public boolean isSafeMode() {
		return safeMode;
	}
	public void setSafeMode(boolean safeMode) {
		this.safeMode = safeMode;
	}
	
	public boolean isReduction() {
		return reduction || ariaReduction;
	}
	public void setReduction(boolean reduction) {
		this.reduction = reduction;
	}

	public boolean isAriaReduction() {
		return ariaReduction;
	}
	public void setAriaReduction(boolean ariaReduction) {
		this.ariaReduction = ariaReduction;
	}

	public boolean isSymmetry() {
		return symmetry;
	}
	public void setSymmetry(boolean symmetry) {
		this.symmetry = symmetry;
	}
	
	public boolean isDebugTrace() {
		return debugTrace;
	}
	public void setDebugTrace(boolean debugTrace) {
		this.debugTrace = debugTrace;
	}
	
	public boolean isDebugAll() {
		return debugAll;
	}
	public void setDebugAll(boolean debugAll) {
		this.debugAll = debugAll;
	}
	
	public CoreVersion getCoreVersion() {
		return coreVersion;
	}
	public void setCoreVersion(CoreVersion coreVersion) {
		this.coreVersion = coreVersion;
	}
	
	public boolean isExportStateSpace() {
		return exportStateSpaceTargetFile != null;
	}
	public void setExportStateSpaceTargetFile(String exportStateSpace) {
		this.exportStateSpaceTargetFile = exportStateSpace;
	}
	
	public boolean isProgressReport() {
		return progressReport;
	}
	public void setProgressReport(boolean progressReport) {
		this.progressReport = progressReport;
	}
	
	public boolean isTraceGenerator() {
		return traceGenerator;
	}
	public void setTraceGenerator(boolean traceGenerator) {
		this.traceGenerator = traceGenerator;
	}
}