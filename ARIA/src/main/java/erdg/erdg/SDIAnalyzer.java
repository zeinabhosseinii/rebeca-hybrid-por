package erdg.erdg;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import erdg.analysis.GuardAnalysis;
import erdg.model.ActivationNode;

/**
 * Detects Shared Destination Interference (SDI) between pairs of rebec instances.
 *
 * Two rebecs r1 and r2 exhibit SDI with respect to a common target r3 iff:
 *   (1) Both r1 and r2 send messages to r3 (shared destination), AND
 *   (2) The sending message servers are causally Independent, AND
 *   (3) The target message servers invoked at r3 exhibit SVI.
 *
 * When a GuardAnalysis is supplied, sends that can never happen (NEVER guard, or a sender
 * message server that is unreachable) are ignored in (1), and (3) uses the effective SVI.
 * The causal relation (2) is intentionally computed on the full ERDG.
 */
public class SDIAnalyzer {

    private final ERDG erdg;
    private final SVIAnalyzer svi;
    private final CausalAnalyzer causal;
    private final GuardAnalysis guard;                    // null = original behaviour
    private final Set<String> logged = new HashSet<>();

    public SDIAnalyzer(ERDG erdg, SVIAnalyzer svi, CausalAnalyzer causal) {
        this(erdg, svi, causal, null);
    }

    public SDIAnalyzer(ERDG erdg, SVIAnalyzer svi, CausalAnalyzer causal, GuardAnalysis guard) {
        this.erdg = erdg;
        this.svi = svi;
        this.causal = causal;
        this.guard = guard;
    }

    /** True if this activation (a send) can really happen. */
    private boolean effective(ActivationNode a) {
        if (guard == null) return true;
        boolean ok = guard.sendMayHappen(a.senderRebec(), a.senderMethod(), a.targetRebec(), a.messageName());
        if (!ok) {
            String key = a.senderRebec() + "." + a.senderMethod() + " -> " + a.targetRebec() + "." + a.messageName();
            if (logged.add(key)) System.out.println("  Pruned (send never happens): " + key);
        }
        return ok;
    }

    /**
     * Return true iff the messages sent by r1 and r2 to 'target' are causally independent,
     * i.e., they can genuinely arrive concurrently in target's mailbox.
     */
    public boolean arePossiblyConcurrent(String r1, String r2, String target) {
        List<String> sendingMsR1 = new ArrayList<>();
        List<String> sendingMsR2 = new ArrayList<>();

        for (ActivationNode a : erdg.activations) {
            if (!effective(a)) continue;
            if (a.senderRebec().equals(r1) && a.targetRebec().equals(target)) {
                sendingMsR1.add(a.senderRebec() + "." + a.senderMethod());
            }
            if (a.senderRebec().equals(r2) && a.targetRebec().equals(target)) {
                sendingMsR2.add(a.senderRebec() + "." + a.senderMethod());
            }
        }

        if (sendingMsR1.isEmpty() || sendingMsR2.isEmpty()) return false;

        for (String ms1 : sendingMsR1) {
            for (String ms2 : sendingMsR2) {
                if (causal.causallyTriggers(ms1, ms2)) {
                    System.out.println("  Causal: " + ms1 + " ⇒ " + ms2 + " → NOT Independent");
                    return false;
                }
                if (causal.causallyTriggers(ms2, ms1)) {
                    System.out.println("  Causal: " + ms2 + " ⇒ " + ms1 + " → NOT Independent");
                    return false;
                }
            }
        }
        return true;
    }

    /** Return true iff r1 and r2 are SDI-dependent. */
    public boolean areRebecDependent(String r1, String r2) {
        List<String[]> r1Sends = new ArrayList<>();
        List<String[]> r2Sends = new ArrayList<>();
        Set<String> r1Targets = new HashSet<>();
        Set<String> r2Targets = new HashSet<>();

        for (ActivationNode a : erdg.activations) {
            if (!effective(a)) continue;
            if (a.senderRebec().equals(r1)) {
                r1Sends.add(new String[]{a.targetRebec(), a.messageName()});
                r1Targets.add(a.targetRebec());
            }
            if (a.senderRebec().equals(r2)) {
                r2Sends.add(new String[]{a.targetRebec(), a.messageName()});
                r2Targets.add(a.targetRebec());
            }
        }

        Set<String> commonTargets = new HashSet<>(r1Targets);
        commonTargets.retainAll(r2Targets);

        for (String target : commonTargets) {
            if (!arePossiblyConcurrent(r1, r2, target)) continue;

            List<String> msgsFromR1 = new ArrayList<>();
            List<String> msgsFromR2 = new ArrayList<>();
            for (String[] s : r1Sends) if (s[0].equals(target)) msgsFromR1.add(s[1]);
            for (String[] s : r2Sends) if (s[0].equals(target)) msgsFromR2.add(s[1]);

            for (String m1 : msgsFromR1) {
                for (String m2 : msgsFromR2) {
                    String ms1Label = target + "." + m1;
                    String ms2Label = target + "." + m2;
                    if (svi.haveEffectiveSvi(ms1Label, ms2Label)) {
                        System.out.println("SDI: " + r1 + " <-> " + r2
                                + " via " + target
                                + " (SVI: " + ms1Label + " ↔ " + ms2Label + ")");
                        return true;
                    }
                }
            }
        }
        return false;
    }
}