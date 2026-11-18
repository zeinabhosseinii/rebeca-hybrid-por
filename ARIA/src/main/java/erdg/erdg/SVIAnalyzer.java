package erdg.erdg;

import java.util.HashSet;
import java.util.Set;

import erdg.analysis.GuardAnalysis;

/**
 * Detects Shared Variable Interference (SVI) between pairs of message servers.
 * haveSvi(...)          : original behaviour (used for message-server priorities).
 * haveEffectiveSvi(...) : same relation restricted to accesses that can really happen
 *                         (used only by SDI). It is always a subset of haveSvi.
 */
public class SVIAnalyzer {

    private final ERDG erdg;
    private final GuardAnalysis guard;       // null = no pruning

    public SVIAnalyzer(ERDG erdg) {
        this(erdg, null);
    }

    public SVIAnalyzer(ERDG erdg, GuardAnalysis guard) {
        this.erdg = erdg;
        this.guard = guard;
    }

    /** Return true if ms1 and ms2 (each in "instance.method" form) exhibit SVI. */
    public boolean haveSvi(String ms1, String ms2) {
        return conflict(writesOf(ms1), writesOf(ms2), readsOf(ms1), readsOf(ms2));
    }

    /** SVI restricted to accesses that are not NEVER and belong to reachable message servers. */
    public boolean haveEffectiveSvi(String ms1, String ms2) {
        if (guard == null) return haveSvi(ms1, ms2);
        return conflict(
                effective(ms1, writesOf(ms1), true),
                effective(ms2, writesOf(ms2), true),
                effective(ms1, readsOf(ms1), false),
                effective(ms2, readsOf(ms2), false));
    }

    private static boolean conflict(Set<String> w1, Set<String> w2, Set<String> r1, Set<String> r2) {
        if (intersects(w1, w2)) return true;  // W-W
        if (intersects(w1, r2)) return true;  // W-R
        if (intersects(r1, w2)) return true;  // R-W
        return false;
    }

    /** Keeps only the legacy labels whose access can really happen. Never adds a label. */
    private Set<String> effective(String msLabel, Set<String> legacy, boolean writes) {
        int dot = msLabel.indexOf('.');
        if (dot < 0) return legacy;
        String inst = msLabel.substring(0, dot);
        String ms = msLabel.substring(dot + 1);
        if (!guard.knows(inst, ms)) return legacy;
        Set<String> eff = writes ? guard.effectiveWrites(inst, ms) : guard.effectiveReads(inst, ms);
        Set<String> out = new HashSet<>();
        for (String v : eff) {
            String label = inst + "." + v;
            if (legacy.contains(label)) out.add(label);
        }
        return out;
    }

    // ---- helpers ----

    private Set<String> writesOf(String ms) {
        Set<String> result = new HashSet<>();
        for (var e : erdg.E_write)
            if (e.source().equals(ms)) result.add(e.target());
        return result;
    }

    private Set<String> readsOf(String ms) {
        Set<String> result = new HashSet<>();
        for (var e : erdg.E_read)
            if (e.target().equals(ms)) result.add(e.source());
        return result;
    }

    private static boolean intersects(Set<String> a, Set<String> b) {
        Set<String> smaller = a.size() < b.size() ? a : b;
        Set<String> larger  = a.size() < b.size() ? b : a;
        for (String s : smaller)
            if (larger.contains(s)) return true;
        return false;
    }
}