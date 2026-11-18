package org.rebecalang.rmc;

import java.util.*;

import org.rebecalang.compiler.modelcompiler.corerebeca.CoreRebecaTypeSystem;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.*;

/**
 * ERDG-based safety analysis for Aria's partial order reduction (--aria).
 *
 * An msgsrv M is safe iff it has no Shared Destination Interference with any
 * other msgsrv M' in the model.  Three conditions must ALL hold for interference:
 *   1. Shared destination: both M and M' send to some common target r_k.
 *   2. Causal independence: neither M causally triggers M' nor M' triggers M.
 *   3. Shared Variable Interference at r_k: the msgsrvs they invoke at r_k
 *      access a common state variable with at least one write.
 *
 * Causal triggering (M => M'): M is the sole activator of M', i.e. no msgsrv
 * other than M ever sends to M'. Transitively closed.
 *
 * Output uses PORSafetyAnalyzer.Result so the same Velocity context keys
 * ($safeActionsTable, $maxMsgIdPlusOne) work unchanged in the C++ templates.
 */
public class ERDGSafetyAnalyzer {

    // ── flat key encoding ─────────────────────────────────────────────────────
    // We represent (instanceIdx, msgId) as a single int to use in maps/sets.
    // msgId fits in three digits for any realistic model.
    private static final int SLOT = 1000;

    private static int key(int instanceIdx, int msgId) {
        return instanceIdx * SLOT + msgId;
    }

    private static int instanceOf(int k) { return k / SLOT; }
    private static int msgIdOf(int k)    { return k % SLOT; }

    // ── model-level index structures ──────────────────────────────────────────

    private static class ModelIndex {
        final List<String>                       instanceNames;
        final Map<String, Integer>               instanceIndex;
        final Map<String, String>                instanceTypeName;
        final Map<String, ReactiveClassDeclaration> typeToRcd;
        final Map<String, List<String>>          fullKnownRebecNames;
        final Map<String, List<String>>          instanceBindings;
        final Map<String, Integer>               startMsgId;
        final int                                maxMsgId;
        final int                                instanceCount;

        ModelIndex(RebecaModel model) {
            List<MainRebecDefinition>    mainDefs = model.getRebecaCode().getMainDeclaration().getMainRebecDefinition();
            List<ReactiveClassDeclaration> rcds   = model.getRebecaCode().getReactiveClassDeclaration();

            instanceNames    = new ArrayList<>();
            instanceIndex    = new HashMap<>();
            instanceTypeName = new HashMap<>();
            int idx = 0;
            for (MainRebecDefinition mrd : mainDefs) {
                instanceNames.add(mrd.getName());
                instanceIndex.put(mrd.getName(), idx++);
                instanceTypeName.put(mrd.getName(), mrd.getType().getTypeName());
            }
            instanceCount = instanceNames.size();

            typeToRcd = new HashMap<>();
            for (ReactiveClassDeclaration rcd : rcds)
                typeToRcd.put(rcd.getName(), rcd);

            fullKnownRebecNames = new HashMap<>();
            for (ReactiveClassDeclaration rcd : rcds)
                fullKnownRebecNames.put(rcd.getName(), collectFullKnownRebecNames(rcd, typeToRcd));

            instanceBindings = new HashMap<>();
            for (MainRebecDefinition mrd : mainDefs) {
                List<String> bindings = new ArrayList<>();
                for (Expression e : mrd.getBindings())
                    bindings.add(e instanceof TermPrimary ? ((TermPrimary) e).getName() : null);
                instanceBindings.put(mrd.getName(), bindings);
            }

            startMsgId = new HashMap<>();
            for (ReactiveClassDeclaration rcd : rcds)
                startMsgId.put(rcd.getName(), computeMsgIdBase(rcd, typeToRcd));

            int max = 0;
            for (ReactiveClassDeclaration rcd : rcds) {
                int last = startMsgId.get(rcd.getName()) + rcd.getMsgsrvs().size() - 1;
                if (last > max) max = last;
            }
            maxMsgId = max;
        }
    }

    // ── ERDG send graph ───────────────────────────────────────────────────────

    private static class SendGraph {
        // targets.get(srcKey) = list of dstKeys that src sends to
        final Map<Integer, List<Integer>> targets  = new HashMap<>();
        // senders.get(dstKey) = set of srcKeys that send to dst
        final Map<Integer, Set<Integer>>  senders  = new HashMap<>();
        // keys where the target could not be fully resolved
        final Set<Integer>                unknown  = new HashSet<>();
    }

    private static SendGraph buildSendGraph(ModelIndex idx) {
        SendGraph g = new SendGraph();

        for (String instName : idx.instanceNames) {
            int instIdx     = idx.instanceIndex.get(instName);
            String typeName = idx.instanceTypeName.get(instName);
            ReactiveClassDeclaration rcd = idx.typeToRcd.get(typeName);
            if (rcd == null) continue;
            List<String> krNames  = idx.fullKnownRebecNames.get(typeName);
            List<String> bindings = idx.instanceBindings.get(instName);

            for (ReactiveClassDeclaration ancestor : inheritanceChain(rcd, idx.typeToRcd)) {
                int base = idx.startMsgId.get(ancestor.getName());
                List<MsgsrvDeclaration> msgsrvs = ancestor.getMsgsrvs();
                for (int mi = 0; mi < msgsrvs.size(); mi++) {
                    int srcKey = key(instIdx, base + mi);
                    g.targets.put(srcKey, new ArrayList<>());

                    List<DotPrimary> sends = new ArrayList<>();
                    if (msgsrvs.get(mi).getBlock() != null)
                        collectSends(msgsrvs.get(mi).getBlock(), sends);

                    for (DotPrimary send : sends)
                        resolveSend(send, srcKey, instName, krNames, bindings, idx, g);
                }
            }
        }
        return g;
    }

    private static void resolveSend(DotPrimary send, int srcKey,
            String senderInst, List<String> krNames, List<String> bindings,
            ModelIndex idx, SendGraph g) {

        String targetInst = resolveTargetInstance(send.getLeft(), senderInst, krNames, bindings);
        String targetMsg  = send.getRight() instanceof TermPrimary
                ? ((TermPrimary) send.getRight()).getName() : null;

        if (targetMsg == null) {
            markUnknown(srcKey, idx, g);
            return;
        }

        if (targetInst == null) {
            // Instance unknown but message name is known. Try to restrict by target type.
            String targetTypeName = getReactiveClassName(
                    send.getLeft() != null ? send.getLeft().getType() : null, idx);
            if (targetTypeName != null) {
                markUnknownTyped(srcKey, targetTypeName, targetMsg, idx, g);
            } else {
                markUnknown(srcKey, idx, g);
            }
            return;
        }
        Integer targetInstIdx = idx.instanceIndex.get(targetInst);
        if (targetInstIdx == null) {
            markUnknown(srcKey, idx, g);
            return;
        }
        String targetType = idx.instanceTypeName.get(targetInst);
        Integer dstMsgId  = resolveMessageId(targetMsg, targetType, idx);
        if (dstMsgId == null) {
            markUnknown(srcKey, idx, g);
            return;
        }

        int dstKey = key(targetInstIdx, dstMsgId);
        g.targets.get(srcKey).add(dstKey);
        g.senders.computeIfAbsent(dstKey, k -> new HashSet<>()).add(srcKey);
    }

    private static void markUnknown(int srcKey, ModelIndex idx, SendGraph g) {
        g.unknown.add(srcKey);
        // conservative: treat this key as sending to every possible destination
        for (int i = 0; i < idx.instanceCount; i++)
            for (int dMsgId = 1; dMsgId <= idx.maxMsgId; dMsgId++)
                g.senders.computeIfAbsent(key(i, dMsgId), k -> new HashSet<>()).add(srcKey);
    }

    /**
     * Returns the reactive-class type name from a Type object, or null if the type
     * is not a reactive class or is not recognised in the model.
     */
    private static String getReactiveClassName(Type t, ModelIndex idx) {
        if (t == null) return null;
        Type base = (t instanceof ArrayType) ? ((ArrayType) t).getOrdinaryPrimitiveType() : t;
        if (!(base instanceof OrdinaryPrimitiveType)) return null;
        String name = ((OrdinaryPrimitiveType) base).getName();
        return idx.typeToRcd.containsKey(name) ? name : null;
    }

    /**
     * Like markUnknown, but restricted to instances of a known target type sending
     * a known target message.  Adds specific edges without marking srcKey as fully
     * unknown, so causal-triggering and condition-1 checks remain precise.
     * Falls back to markUnknown if no matching (instance, msgId) pair is found.
     */
    private static void markUnknownTyped(int srcKey, String targetTypeName,
            String targetMsg, ModelIndex idx, SendGraph g) {
        boolean anyFound = false;
        for (String instName : idx.instanceNames) {
            if (!targetTypeName.equals(idx.instanceTypeName.get(instName))) continue;
            Integer msgId = resolveMessageId(targetMsg, targetTypeName, idx);
            if (msgId == null) continue;
            int dstKey = key(idx.instanceIndex.get(instName), msgId);
            g.targets.get(srcKey).add(dstKey);
            g.senders.computeIfAbsent(dstKey, k -> new HashSet<>()).add(srcKey);
            anyFound = true;
        }
        if (!anyFound) {
            // Type known but no matching instances/message found — be conservative.
            markUnknown(srcKey, idx, g);
        }
        // srcKey is NOT added to g.unknown: we have resolved it to specific targets.
    }

    // ── causal triggering ─────────────────────────────────────────────────────

    /**
     * Computes the transitive causal-triggering relation per Definition 6 (ERDG traversal).
     *
     * m_i causally triggers m_j (m_i => m_j) iff every send statement targeting m_j
     * appears within m_i's body or within the body of a message server that is itself
     * causally triggered by m_i — i.e., ALL senders of m_j lie within m_i's causal
     * closure ({m_i} union {all keys m_i transitively triggers}).
     *
     * Algorithm: for each non-unknown srcKey, grow its "dominated" set starting from
     * {srcKey} by fixpoint: repeatedly add any dstKey whose complete set of explicit
     * senders is already in dominated.  This correctly captures transitivity without a
     * separate closure step, because intermediate keys enter dominated before any key
     * they alone enable.
     *
     * A dstKey with ANY unknown-source sender is excluded from the fixpoint: we cannot
     * verify that the unknown source lies within any causal chain, so we conservatively
     * treat it as undominated by anyone.
     */
    private static Map<Integer, Set<Integer>> computeCausalTriggering(SendGraph g) {
        // Precompute: explicit sender set per dstKey, excluding any dstKey that has
        // at least one unknown sender (those can never be causally dominated).
        Map<Integer, Set<Integer>> explicitSenders = new HashMap<>();
        for (Map.Entry<Integer, Set<Integer>> e : g.senders.entrySet()) {
            int dstKey = e.getKey();
            Set<Integer> expl = new HashSet<>();
            boolean hasUnknown = false;
            for (int s : e.getValue()) {
                if (g.unknown.contains(s)) hasUnknown = true;
                else expl.add(s);
            }
            if (!hasUnknown && !expl.isEmpty())
                explicitSenders.put(dstKey, expl);
        }

        // For each non-unknown srcKey, compute causal closure by fixpoint.
        Map<Integer, Set<Integer>> triggers = new HashMap<>();
        for (int srcKey : g.targets.keySet()) {
            if (g.unknown.contains(srcKey)) continue;

            Set<Integer> dominated = new HashSet<>();
            dominated.add(srcKey);

            boolean changed = true;
            while (changed) {
                changed = false;
                for (Map.Entry<Integer, Set<Integer>> e : explicitSenders.entrySet()) {
                    int dstKey = e.getKey();
                    if (dominated.contains(dstKey)) continue;
                    if (dominated.containsAll(e.getValue())) {
                        dominated.add(dstKey);
                        changed = true;
                    }
                }
            }

            dominated.remove(srcKey);
            if (!dominated.isEmpty())
                triggers.put(srcKey, dominated);
        }
        return triggers;
    }

    // ── shared variable interference ──────────────────────────────────────────

    /**
     * Returns svi.get(typeName).get(msgId) = set of msgIds that conflict with it
     * within the same reactive class (shared state variable, at least one write).
     * Implements Definition 3/7 literally: any pair (m_i, m_j), including m_i == m_j.
     * A prior version skipped m_i == m_j on a commutativity argument; removed per
     * cross-benchmark evidence (TS2/TS3/GradientSync/ImageProcessor) that the
     * reference Aria implementation does not have this exemption — see
     * project_aria_ref_comparison memory.
     */
    private static Map<String, Map<Integer, Set<Integer>>> computeSharedVariableInterference(ModelIndex idx) {
        Map<String, Map<Integer, Set<Integer>>> result = new HashMap<>();

        for (ReactiveClassDeclaration rcd : idx.typeToRcd.values()) {
            String typeName = rcd.getName();
            Set<String> stateVars = collectAllStateVarNames(rcd, idx.typeToRcd);

            Map<Integer, Set<String>> writesByMsgId = new HashMap<>();
            Map<Integer, Set<String>> readsByMsgId  = new HashMap<>();
            for (ReactiveClassDeclaration ancestor : inheritanceChain(rcd, idx.typeToRcd)) {
                int base = idx.startMsgId.get(ancestor.getName());
                List<MsgsrvDeclaration> ms = ancestor.getMsgsrvs();
                for (int i = 0; i < ms.size(); i++) {
                    int msgId = base + i;
                    Set<String> w = new HashSet<>(), r = new HashSet<>();
                    if (ms.get(i).getBlock() != null)
                        collectVarAccesses(ms.get(i).getBlock(), stateVars, w, r);
                    writesByMsgId.put(msgId, w);
                    readsByMsgId.put(msgId, r);
                }
            }

            Map<Integer, Set<Integer>> conflicts = new HashMap<>();
            List<Integer> msgIds = new ArrayList<>(writesByMsgId.keySet());
            for (int i = 0; i < msgIds.size(); i++) {
                for (int j = 0; j < msgIds.size(); j++) {
                    int mi = msgIds.get(i), mj = msgIds.get(j);
                    if (haveSharedVariableInterference(
                            writesByMsgId.get(mi), readsByMsgId.get(mi),
                            writesByMsgId.get(mj), readsByMsgId.get(mj)))
                        conflicts.computeIfAbsent(mi, k -> new HashSet<>()).add(mj);
                }
            }
            result.put(typeName, conflicts);
        }
        return result;
    }

    private static boolean haveSharedVariableInterference(
            Set<String> wi, Set<String> ri, Set<String> wj, Set<String> rj) {
        return intersects(wi, wj) || intersects(wi, rj) || intersects(wj, ri);
    }

    private static boolean intersects(Set<String> a, Set<String> b) {
        if (a == null || b == null || a.isEmpty() || b.isEmpty()) return false;
        for (String v : a) if (b.contains(v)) return true;
        return false;
    }

    // ── shared destination interference & safety ──────────────────────────────

    /**
     * Checks whether (srcKeyI, srcKeyJ) are in Shared Destination Interference.
     * Three conditions must ALL hold:
     *   1. Shared destination INSTANCE: both send a message to the same rebec instance
     *      (regardless of which message — condition 1 is about the target instance, not
     *      the specific (instance, message) key).
     *   2. Causal independence: neither action causally triggers the other.
     *   3. SVI at that shared instance: the two msgsrvs they invoke there share a state
     *      variable with at least one write.
     *
     * When srcKeyJ has unknown targets we cannot enumerate them, so we conservatively
     * assume it shares every target instance that srcKeyI sends to (condition 1 passes)
     * and that SVI exists there (condition 3 passes).
     */
    private static boolean inSharedDestinationInterference(
            int srcKeyI, int srcKeyJ,
            SendGraph g,
            Map<Integer, Set<Integer>> causal,
            Map<String, Map<Integer, Set<Integer>>> svi,
            ModelIndex idx) {

        List<Integer> targetsI = g.targets.getOrDefault(srcKeyI, Collections.emptyList());
        if (targetsI.isEmpty()) return false;

        boolean jIsUnknown = g.unknown.contains(srcKeyJ);
        List<Integer> targetsJ = jIsUnknown ? null
                : g.targets.getOrDefault(srcKeyJ, Collections.emptyList());

        // Condition 2: checked once per pair (causal relation is action-level, not dest-specific)
        if (causallDependent(srcKeyI, srcKeyJ, causal)) return false;

        // For every (targetI, targetJ) pair that share the same destination INSTANCE,
        // check condition 3 (SVI at that instance).
        for (int tI : targetsI) {
            int dstInst = instanceOf(tI);
            int msgI    = msgIdOf(tI);
            String dstType = idx.instanceTypeName.get(idx.instanceNames.get(dstInst));
            Map<Integer, Set<Integer>> sviForDst = svi.getOrDefault(dstType, Collections.emptyMap());

            if (jIsUnknown) {
                // Conservative: assume J sends to this instance with any message → SVI assumed.
                return true;
            }

            for (int tJ : targetsJ) {
                if (instanceOf(tJ) != dstInst) continue; // condition 1: shared instance
                int msgJ = msgIdOf(tJ);
                if (haveSVIAtDst(msgI, msgJ, sviForDst)) return true;
            }
        }
        return false;
    }

    /** True if the two msgsrvs (by id) at the same reactive class have SVI (Def 3/7, any pair). */
    private static boolean haveSVIAtDst(int msgI, int msgJ,
            Map<Integer, Set<Integer>> sviForDst) {
        Set<Integer> conflicts = sviForDst.get(msgI);
        return conflicts != null && conflicts.contains(msgJ);
    }

    private static boolean causallDependent(int a, int b, Map<Integer, Set<Integer>> causal) {
        Set<Integer> fromA = causal.getOrDefault(a, Collections.emptySet());
        Set<Integer> fromB = causal.getOrDefault(b, Collections.emptySet());
        return fromA.contains(b) || fromB.contains(a);
    }

    /**
     * Computes the safety table: safe[instIdx][msgId] = true iff that msgsrv
     * is globally independent (no Shared Destination Interference with any other).
     */
    private static boolean[][] computeSafetyTable(
            SendGraph g,
            Map<Integer, Set<Integer>> causal,
            Map<String, Map<Integer, Set<Integer>>> svi,
            ModelIndex idx) {

        boolean[][] safe = new boolean[idx.instanceCount][idx.maxMsgId + 1];
        for (int i = 0; i < idx.instanceCount; i++)
            safe[i][0] = true; // msgId 0 = empty queue

        for (String instI : idx.instanceNames) {
            int iIdx = idx.instanceIndex.get(instI);
            ReactiveClassDeclaration rcdI = idx.typeToRcd.get(idx.instanceTypeName.get(instI));
            if (rcdI == null) continue;

            for (ReactiveClassDeclaration ancestor : inheritanceChain(rcdI, idx.typeToRcd)) {
                int base = idx.startMsgId.get(ancestor.getName());
                List<MsgsrvDeclaration> msgsrvs = ancestor.getMsgsrvs();
                for (int mi = 0; mi < msgsrvs.size(); mi++) {
                    int msgIdI  = base + mi;
                    int srcKeyI = key(iIdx, msgIdI);

                    if (g.unknown.contains(srcKeyI)) {
                        safe[iIdx][msgIdI] = false;
                        continue;
                    }

                    safe[iIdx][msgIdI] = !hasAnyInterference(srcKeyI, instI, g, causal, svi, idx);
                }
            }
        }
        return safe;
    }

    private static boolean hasAnyInterference(int srcKeyI, String instI,
            SendGraph g, Map<Integer, Set<Integer>> causal,
            Map<String, Map<Integer, Set<Integer>>> svi, ModelIndex idx) {

        for (String instJ : idx.instanceNames) {
            if (instJ.equals(instI)) continue;
            int jIdx = idx.instanceIndex.get(instJ);
            ReactiveClassDeclaration rcdJ = idx.typeToRcd.get(idx.instanceTypeName.get(instJ));
            if (rcdJ == null) continue;

            for (ReactiveClassDeclaration ancestor : inheritanceChain(rcdJ, idx.typeToRcd)) {
                int base = idx.startMsgId.get(ancestor.getName());
                List<MsgsrvDeclaration> msgsrvs = ancestor.getMsgsrvs();
                for (int mj = 0; mj < msgsrvs.size(); mj++) {
                    int srcKeyJ = key(jIdx, base + mj);
                    if (inSharedDestinationInterference(srcKeyI, srcKeyJ, g, causal, svi, idx))
                        return true;
                }
            }
        }
        return false;
    }

    /**
     * Computes the full pairwise SDI matrix for dynamic checking.
     * sdiMatrix[instI][msgIdI][instJ][msgIdJ] = true iff those two (instance, msgId)
     * pairs have Shared Destination Interference with each other.
     */
    private static boolean[][][][] computeSdiMatrix(
            SendGraph g, Map<Integer, Set<Integer>> causal,
            Map<String, Map<Integer, Set<Integer>>> svi, ModelIndex idx) {

        boolean[][][][] mat = new boolean[idx.instanceCount][idx.maxMsgId + 1]
                                          [idx.instanceCount][idx.maxMsgId + 1];
        for (int i = 0; i < idx.instanceCount; i++) {
            String instI = idx.instanceNames.get(i);
            ReactiveClassDeclaration rcdI = idx.typeToRcd.get(idx.instanceTypeName.get(instI));
            if (rcdI == null) continue;
            for (ReactiveClassDeclaration ancI : inheritanceChain(rcdI, idx.typeToRcd)) {
                int baseI = idx.startMsgId.get(ancI.getName());
                List<MsgsrvDeclaration> msgsrvsI = ancI.getMsgsrvs();
                for (int mi = 0; mi < msgsrvsI.size(); mi++) {
                    int msgIdI  = baseI + mi;
                    int srcKeyI = key(i, msgIdI);
                    for (int j = 0; j < idx.instanceCount; j++) {
                        if (j == i) continue;
                        String instJ = idx.instanceNames.get(j);
                        ReactiveClassDeclaration rcdJ =
                                idx.typeToRcd.get(idx.instanceTypeName.get(instJ));
                        if (rcdJ == null) continue;
                        for (ReactiveClassDeclaration ancJ : inheritanceChain(rcdJ, idx.typeToRcd)) {
                            int baseJ = idx.startMsgId.get(ancJ.getName());
                            List<MsgsrvDeclaration> msgsrvsJ = ancJ.getMsgsrvs();
                            for (int mj = 0; mj < msgsrvsJ.size(); mj++) {
                                int msgIdJ  = baseJ + mj;
                                int srcKeyJ = key(j, msgIdJ);
                                if (inSharedDestinationInterference(
                                        srcKeyI, srcKeyJ, g, causal, svi, idx)) {
                                    mat[i][msgIdI][j][msgIdJ] = true;
                                }
                            }
                        }
                    }
                }
            }
        }
        return mat;
    }

    // ── sender-independence detection ────────────────────────────────────────────

    /**
     * Returns a map from reactive-class name to the set of msgsrv names whose
     * bodies never reference the implicit 'sender' variable.
     * For these msgsrvs the sender ID has no semantic effect; we can zero the
     * senderQueue byte during state marshaling to merge otherwise-identical states.
     */
    public static Map<String, Set<String>> findSenderIndepMsgsrvNames(RebecaModel rebecaModel) {
        Map<String, Set<String>> result = new HashMap<>();
        for (ReactiveClassDeclaration rcd : rebecaModel.getRebecaCode().getReactiveClassDeclaration()) {
            Set<String> indep = new LinkedHashSet<>();
            for (MsgsrvDeclaration ms : rcd.getMsgsrvs()) {
                if (!stmtUsesSender(ms.getBlock()))
                    indep.add(ms.getName());
            }
            if (!indep.isEmpty())
                result.put(rcd.getName(), indep);
        }
        return result;
    }

    private static boolean stmtUsesSender(Statement stmt) {
        if (stmt == null) return false;
        if (stmt instanceof BlockStatement) {
            for (Statement s : ((BlockStatement) stmt).getStatements())
                if (stmtUsesSender(s)) return true;
        } else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            return exprUsesSender(cs.getCondition()) || stmtUsesSender(cs.getStatement())
                    || stmtUsesSender(cs.getElseStatement());
        } else if (stmt instanceof WhileStatement) {
            return exprUsesSender(((WhileStatement) stmt).getCondition())
                    || stmtUsesSender(((WhileStatement) stmt).getStatement());
        } else if (stmt instanceof ForStatement) {
            ForStatement fs = (ForStatement) stmt;
            if (fs.getForInitializer() != null) {
                for (Expression e : fs.getForInitializer().getExpressions())
                    if (exprUsesSender(e)) return true;
                if (fs.getForInitializer().getFieldDeclaration() != null)
                    if (stmtUsesSender(fs.getForInitializer().getFieldDeclaration())) return true;
            }
            if (exprUsesSender(fs.getCondition())) return true;
            for (Expression e : fs.getForIncrement())
                if (exprUsesSender(e)) return true;
            return stmtUsesSender(fs.getStatement());
        } else if (stmt instanceof ReturnStatement) {
            return exprUsesSender(((ReturnStatement) stmt).getExpression());
        } else if (stmt instanceof SwitchStatement) {
            SwitchStatement ss = (SwitchStatement) stmt;
            if (exprUsesSender(ss.getExpression())) return true;
            for (SwitchStatementGroup g : ss.getSwitchStatementGroups()) {
                if (exprUsesSender(g.getExpression())) return true;
                for (Statement s : g.getStatements())
                    if (stmtUsesSender(s)) return true;
            }
        } else if (stmt instanceof FieldDeclaration) {
            for (VariableDeclarator vd : ((FieldDeclaration) stmt).getVariableDeclarators()) {
                VariableInitializer vi = vd.getVariableInitializer();
                if (vi instanceof OrdinaryVariableInitializer)
                    if (exprUsesSender(((OrdinaryVariableInitializer) vi).getValue())) return true;
            }
        } else if (stmt instanceof Expression) {
            return exprUsesSender((Expression) stmt);
        }
        return false;
    }

    private static boolean exprUsesSender(Expression expr) {
        if (expr == null) return false;
        if (expr instanceof TermPrimary) {
            TermPrimary tp = (TermPrimary) expr;
            if ("sender".equals(tp.getName())) return true;
            if (tp.getParentSuffixPrimary() != null)
                for (Expression arg : tp.getParentSuffixPrimary().getArguments())
                    if (exprUsesSender(arg)) return true;
            return false;
        } else if (expr instanceof CastExpression) {
            return exprUsesSender(((CastExpression) expr).getExpression());
        } else if (expr instanceof DotPrimary) {
            DotPrimary dp = (DotPrimary) expr;
            return exprUsesSender(dp.getLeft()) || exprUsesSender(dp.getRight());
        } else if (expr instanceof TernaryExpression) {
            TernaryExpression te = (TernaryExpression) expr;
            return exprUsesSender(te.getCondition()) || exprUsesSender(te.getLeft())
                    || exprUsesSender(te.getRight());
        } else if (expr instanceof BinaryExpression) {
            BinaryExpression be = (BinaryExpression) expr;
            return exprUsesSender(be.getLeft()) || exprUsesSender(be.getRight());
        } else if (expr instanceof UnaryExpression) {
            return exprUsesSender(((UnaryExpression) expr).getExpression());
        } else if (expr instanceof PlusSubExpression) {
            return exprUsesSender(((PlusSubExpression) expr).getValue());
        } else if (expr instanceof InstanceofExpression) {
            return exprUsesSender(((InstanceofExpression) expr).getValue());
        } else if (expr instanceof NonDetExpression) {
            for (Expression c : ((NonDetExpression) expr).getChoices())
                if (exprUsesSender(c)) return true;
        }
        return false;
    }

    // ── dead variable elimination ─────────────────────────────────────────────

    /**
     * Returns the set of dead state variables (written but never meaningfully read)
     * for each reactive class.  A "meaningful read" is one that appears in a
     * condition expression (if/while/for guard) or as an argument to a send
     * statement — reads that appear only in self-update patterns (v++, v+=k) or
     * on the RHS of an assignment to another dead var are not counted.
     */
    public static Map<String, Set<String>> computeDeadVarsByClass(RebecaModel rebecaModel) {
        Map<String, Set<String>> result = new HashMap<>();
        for (ReactiveClassDeclaration rcd : rebecaModel.getRebecaCode().getReactiveClassDeclaration()) {
            Set<String> stateVarNames = new HashSet<>();
            for (FieldDeclaration fd : rcd.getStatevars())
                for (VariableDeclarator vd : fd.getVariableDeclarators())
                    stateVarNames.add(vd.getVariableName());

            Set<String> writtenVars = new HashSet<>(), readVars = new HashSet<>();
            for (MsgsrvDeclaration ms : rcd.getMsgsrvs()) {
                if (ms.getBlock() == null) continue;
                collectVarAccesses(ms.getBlock(), stateVarNames, writtenVars, readVars);
            }

            Set<String> dead = new HashSet<>(writtenVars);
            dead.removeAll(readVars);
            if (!dead.isEmpty())
                result.put(rcd.getName(), dead);
        }
        return result;
    }

    /**
     * Replaces ALL assignments to dead state variables with {@code v = 0},
     * and replaces {@code v++}/{@code v--} on dead vars with {@code v = 0}.
     * This ensures dead variables never contribute spurious distinctions to
     * the state hash.
     */
    public static void eliminateDeadVarNonDet(RebecaModel rebecaModel) {
        Map<String, Set<String>> deadByClass = computeDeadVarsByClass(rebecaModel);
        for (ReactiveClassDeclaration rcd : rebecaModel.getRebecaCode().getReactiveClassDeclaration()) {
            Set<String> deadVars = deadByClass.getOrDefault(rcd.getName(), Collections.emptySet());
            if (deadVars.isEmpty()) continue;
            for (MsgsrvDeclaration ms : rcd.getMsgsrvs())
                patchDeadVarAssignments(ms.getBlock(), deadVars);
        }
    }

    private static void patchDeadVarAssignments(Statement stmt, Set<String> deadVars) {
        if (stmt == null) return;
        if (stmt instanceof BlockStatement) {
            List<Statement> stmts = ((BlockStatement) stmt).getStatements();
            for (int i = 0; i < stmts.size(); i++) {
                Statement s = stmts.get(i);
                // Replace v++ / v-- on dead vars with v = 0 (no-op since v is always 0)
                if (s instanceof PlusSubExpression) {
                    Expression val = ((PlusSubExpression) s).getValue();
                    if (val instanceof TermPrimary) {
                        String varName = ((TermPrimary) val).getName();
                        if (deadVars.contains(varName)) {
                            stmts.set(i, makeZeroAssign(varName));
                            continue;
                        }
                    }
                }
                patchDeadVarAssignments(s, deadVars);
            }
        } else if (stmt instanceof BinaryExpression
                && "=".equals(((BinaryExpression) stmt).getOperator())) {
            BinaryExpression be = (BinaryExpression) stmt;
            if (be.getLeft() instanceof TermPrimary) {
                String varName = ((TermPrimary) be.getLeft()).getName();
                if (deadVars.contains(varName)) {
                    // Zero ALL assignments to dead vars (including non-det).
                    be.setRight(makeZeroLiteral());
                }
            }
        } else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            patchDeadVarAssignments(cs.getStatement(), deadVars);
            patchDeadVarAssignments(cs.getElseStatement(), deadVars);
        } else if (stmt instanceof WhileStatement) {
            patchDeadVarAssignments(((WhileStatement) stmt).getStatement(), deadVars);
        } else if (stmt instanceof ForStatement) {
            patchDeadVarAssignments(((ForStatement) stmt).getStatement(), deadVars);
        }
    }

    private static BinaryExpression makeZeroAssign(String varName) {
        BinaryExpression assign = new BinaryExpression();
        assign.setOperator("=");
        TermPrimary var = new TermPrimary();
        var.setName(varName);
        assign.setLeft(var);
        assign.setRight(makeZeroLiteral());
        return assign;
    }

    private static Literal makeZeroLiteral() {
        Literal zero = new Literal();
        zero.setLiteralValue("0");
        return zero;
    }

    // ── dead parameter detection ──────────────────────────────────────────────

    /**
     * Returns a map from reactive-class name to the set of msgsrv names whose
     * formal parameters are all transitively dead — i.e., every parameter P of
     * the msgsrv is either unused in the body, or only appears in condition
     * expressions whose branches exclusively write to dead state variables.
     *
     * For these msgsrvs the parameter bytes in the queue have no semantic effect
     * on future behaviour; we zero them during state marshaling so that
     * otherwise-identical queue entries with different parameter values merge.
     */
    public static Map<String, Set<String>> findDeadParamMsgsrvsByClass(RebecaModel rebecaModel) {
        Map<String, Set<String>> deadByClass = computeDeadVarsByClass(rebecaModel);
        Map<String, Set<String>> result = new HashMap<>();
        for (ReactiveClassDeclaration rcd : rebecaModel.getRebecaCode().getReactiveClassDeclaration()) {
            Set<String> deadVars = deadByClass.getOrDefault(rcd.getName(), Collections.emptySet());
            Set<String> deadParamMsgsrvs = new LinkedHashSet<>();
            for (MsgsrvDeclaration ms : rcd.getMsgsrvs()) {
                if (ms.getFormalParameters() == null || ms.getFormalParameters().isEmpty()) continue;
                if (allParamsDead(ms, deadVars))
                    deadParamMsgsrvs.add(ms.getName());
            }
            if (!deadParamMsgsrvs.isEmpty())
                result.put(rcd.getName(), deadParamMsgsrvs);
        }
        return result;
    }

    private static boolean allParamsDead(MsgsrvDeclaration ms, Set<String> deadVars) {
        if (ms.getBlock() == null) return true;
        for (FormalParameterDeclaration fp : ms.getFormalParameters())
            if (paramHasLiveUse(fp.getName(), ms.getBlock(), deadVars))
                return false;
        return true;
    }

    /**
     * Returns true if {@code paramName} has at least one "live" use inside
     * {@code stmt}.  A use is dead (safe to ignore) iff it appears only as the
     * discriminator of a conditional whose every branch exclusively writes to
     * dead state variables.  All other uses (send arguments, loop conditions,
     * RHS of live-var assignments, etc.) are live.
     */
    private static boolean paramHasLiveUse(String paramName, Statement stmt, Set<String> deadVars) {
        if (stmt == null) return false;
        if (stmt instanceof BlockStatement) {
            for (Statement s : ((BlockStatement) stmt).getStatements())
                if (paramHasLiveUse(paramName, s, deadVars)) return true;
        } else if (stmt instanceof BinaryExpression
                && "=".equals(((BinaryExpression) stmt).getOperator())) {
            BinaryExpression be = (BinaryExpression) stmt;
            if (exprContainsName(be.getRight(), paramName)) {
                // Param on RHS: live iff LHS is a live (non-dead) state var.
                if (!(be.getLeft() instanceof TermPrimary)) return true;
                String lhsName = ((TermPrimary) be.getLeft()).getName();
                if (!deadVars.contains(lhsName)) return true;
            }
        } else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            if (exprContainsName(cs.getCondition(), paramName)) {
                // Param in condition: live iff any branch has live effects.
                if (!stmtOnlyDeadVarWrites(cs.getStatement(), deadVars)) return true;
                if (!stmtOnlyDeadVarWrites(cs.getElseStatement(), deadVars)) return true;
                // Both branches only write dead vars → this param use is itself dead.
            } else {
                if (paramHasLiveUse(paramName, cs.getStatement(), deadVars)) return true;
                if (paramHasLiveUse(paramName, cs.getElseStatement(), deadVars)) return true;
            }
        } else if (stmt instanceof WhileStatement) {
            WhileStatement ws = (WhileStatement) stmt;
            if (exprContainsName(ws.getCondition(), paramName)) return true;
            if (paramHasLiveUse(paramName, ws.getStatement(), deadVars)) return true;
        } else if (stmt instanceof ForStatement) {
            ForStatement fs = (ForStatement) stmt;
            if (exprContainsName(fs.getCondition(), paramName)) return true;
            if (paramHasLiveUse(paramName, fs.getStatement(), deadVars)) return true;
        } else if (stmt instanceof Expression) {
            // Includes sends (DotPrimary) and expression statements (v++).
            if (exprContainsName((Expression) stmt, paramName)) return true;
        }
        return false;
    }

    /**
     * Returns true iff every write-effect of {@code stmt} targets a dead state
     * variable, and {@code stmt} contains no send statements.  Used to validate
     * that the branches of a "dead conditional" only have dead effects.
     */
    private static boolean stmtOnlyDeadVarWrites(Statement stmt, Set<String> deadVars) {
        if (stmt == null) return true;
        if (stmt instanceof BlockStatement) {
            for (Statement s : ((BlockStatement) stmt).getStatements())
                if (!stmtOnlyDeadVarWrites(s, deadVars)) return false;
        } else if (stmt instanceof BinaryExpression
                && "=".equals(((BinaryExpression) stmt).getOperator())) {
            Expression lhs = ((BinaryExpression) stmt).getLeft();
            if (!(lhs instanceof TermPrimary)) return false;
            if (!deadVars.contains(((TermPrimary) lhs).getName())) return false;
        } else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            return stmtOnlyDeadVarWrites(cs.getStatement(), deadVars)
                && stmtOnlyDeadVarWrites(cs.getElseStatement(), deadVars);
        } else if (stmt instanceof WhileStatement) {
            return stmtOnlyDeadVarWrites(((WhileStatement) stmt).getStatement(), deadVars);
        } else if (stmt instanceof ForStatement) {
            return stmtOnlyDeadVarWrites(((ForStatement) stmt).getStatement(), deadVars);
        } else if (stmt instanceof FieldDeclaration) {
            return true; // local var declaration — no state-var write
        } else if (stmt instanceof Expression) {
            if (stmt instanceof DotPrimary) return false; // send → live effect
            if (stmt instanceof PlusSubExpression) {
                Expression val = ((PlusSubExpression) stmt).getValue();
                return val instanceof TermPrimary
                    && deadVars.contains(((TermPrimary) val).getName());
            }
            return false; // unknown expression → conservative
        } else {
            return false; // unknown statement → conservative
        }
        return true;
    }

    /** Returns true iff {@code name} appears anywhere in {@code expr}. */
    private static boolean exprContainsName(Expression expr, String name) {
        if (expr == null) return false;
        if (expr instanceof TermPrimary) {
            TermPrimary tp = (TermPrimary) expr;
            if (name.equals(tp.getName())) return true;
            if (tp.getParentSuffixPrimary() != null)
                for (Expression arg : tp.getParentSuffixPrimary().getArguments())
                    if (exprContainsName(arg, name)) return true;
        } else if (expr instanceof BinaryExpression) {
            BinaryExpression be = (BinaryExpression) expr;
            return exprContainsName(be.getLeft(), name) || exprContainsName(be.getRight(), name);
        } else if (expr instanceof UnaryExpression) {
            return exprContainsName(((UnaryExpression) expr).getExpression(), name);
        } else if (expr instanceof DotPrimary) {
            DotPrimary dp = (DotPrimary) expr;
            return exprContainsName(dp.getLeft(), name) || exprContainsName(dp.getRight(), name);
        } else if (expr instanceof TernaryExpression) {
            TernaryExpression te = (TernaryExpression) expr;
            return exprContainsName(te.getCondition(), name)
                || exprContainsName(te.getLeft(), name)
                || exprContainsName(te.getRight(), name);
        } else if (expr instanceof PlusSubExpression) {
            return exprContainsName(((PlusSubExpression) expr).getValue(), name);
        } else if (expr instanceof NonDetExpression) {
            for (Expression c : ((NonDetExpression) expr).getChoices())
                if (exprContainsName(c, name)) return true;
        }
        return false;
    }

    // ── public entry point ────────────────────────────────────────────────────

    public static PORSafetyAnalyzer.Result analyze(RebecaModel rebecaModel) {
        return analyze(rebecaModel, null, null);
    }

    public static PORSafetyAnalyzer.Result analyze(RebecaModel rebecaModel,
                                                    String jsonPath, String modelHash) {

        ModelIndex idx    = new ModelIndex(rebecaModel);
        SendGraph  g      = buildSendGraph(idx);
        Map<Integer, Set<Integer>> causal = computeCausalTriggering(g);
        Map<String, Map<Integer, Set<Integer>>> svi = computeSharedVariableInterference(idx);
        boolean[][] safe  = computeSafetyTable(g, causal, svi, idx);

        List<List<Boolean>> table = new ArrayList<>();
        for (int i = 0; i < idx.instanceCount; i++) {
            List<Boolean> row = new ArrayList<>();
            for (int j = 0; j <= idx.maxMsgId; j++)
                row.add(safe[i][j]);
            table.add(row);
        }

        // Compute full pairwise SDI matrix for dynamic per-state checking
        boolean[][][][] sdiRaw = computeSdiMatrix(g, causal, svi, idx);
        List<List<List<List<Boolean>>>> sdiTable = new ArrayList<>();
        for (int i = 0; i < idx.instanceCount; i++) {
            List<List<List<Boolean>>> rowI = new ArrayList<>();
            for (int mi = 0; mi <= idx.maxMsgId; mi++) {
                List<List<Boolean>> rowIM = new ArrayList<>();
                for (int j = 0; j < idx.instanceCount; j++) {
                    List<Boolean> rowJ = new ArrayList<>();
                    for (int mj = 0; mj <= idx.maxMsgId; mj++)
                        rowJ.add(sdiRaw[i][mi][j][mj]);
                    rowIM.add(rowJ);
                }
                rowI.add(rowIM);
            }
            sdiTable.add(rowI);
        }

        // Compute ample-set candidate ordering: self-looping hubs last.
        // Rebecs whose msgsrvs send a message to themselves (self-loop) cycle their own
        // queue and can starve other enabled rebecs when used as the ample set with the
        // refined proviso (which never fires for all-safe models). Deferring them to the
        // end of the candidate list ensures other rebecs are always tried first.
        // Rebecs without self-loops retain their natural (declaration) order.
        boolean[] hasSelfLoop = new boolean[idx.instanceCount];
        for (Map.Entry<Integer, List<Integer>> e : g.targets.entrySet()) {
            int srcInst = instanceOf(e.getKey());
            for (int dstKey : e.getValue()) {
                if (instanceOf(dstKey) == srcInst) { hasSelfLoop[srcInst] = true; break; }
            }
        }
        Integer[] orderArr = new Integer[idx.instanceCount];
        for (int i = 0; i < idx.instanceCount; i++) orderArr[i] = i;
        Arrays.sort(orderArr, (a, b) -> {
            int aSelf = hasSelfLoop[a] ? 1 : 0, bSelf = hasSelfLoop[b] ? 1 : 0;
            return aSelf != bSelf ? Integer.compare(aSelf, bSelf) : Integer.compare(a, b);
        });
        List<Integer> ampSetOrder = Arrays.asList(orderArr);

        if (jsonPath != null) {
            Map<String, int[]> actionIds = new LinkedHashMap<>();
            for (String inst : idx.instanceNames) {
                ReactiveClassDeclaration rc = idx.typeToRcd.get(idx.instanceTypeName.get(inst));
                for (ReactiveClassDeclaration ancestor : inheritanceChain(rc, idx.typeToRcd)) {
                    for (MsgsrvDeclaration ms : ancestor.getMsgsrvs()) {
                        String label = inst + "." + ms.getName();
                        actionIds.putIfAbsent(label, new int[] {idx.instanceIndex.get(inst),
                                resolveMessageId(ms.getName(), idx.instanceTypeName.get(inst), idx)});
                    }
                }
            }
            AriaDependencyInput.apply(jsonPath, modelHash, idx.instanceTypeName, actionIds, sdiTable);
        }
        return new PORSafetyAnalyzer.Result(table, idx.maxMsgId, sdiTable, ampSetOrder);
    }

    // ── AST traversal helpers ─────────────────────────────────────────────────

    private static void collectSends(Statement stmt, List<DotPrimary> out) {
        if (stmt == null) return;
        if (stmt instanceof BlockStatement)
            for (Statement s : ((BlockStatement) stmt).getStatements()) collectSends(s, out);
        else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            collectSendsFromExpr(cs.getCondition(), out);
            collectSends(cs.getStatement(), out);
            if (cs.getElseStatement() != null) collectSends(cs.getElseStatement(), out);
        } else if (stmt instanceof WhileStatement) {
            collectSendsFromExpr(((WhileStatement) stmt).getCondition(), out);
            collectSends(((WhileStatement) stmt).getStatement(), out);
        } else if (stmt instanceof ForStatement)
            collectSends(((ForStatement) stmt).getStatement(), out);
        else if (stmt instanceof Expression)
            collectSendsFromExpr((Expression) stmt, out);
    }

    private static void collectSendsFromExpr(Expression expr, List<DotPrimary> out) {
        if (expr == null) return;
        if (expr instanceof DotPrimary) {
            DotPrimary dp = (DotPrimary) expr;
            if (dp.getLeft() != null && isReactiveClassType(dp.getLeft().getType())) {
                out.add(dp);
                collectSendsFromExpr(dp.getRight(), out);
            } else {
                collectSendsFromExpr(dp.getLeft(), out);
                collectSendsFromExpr(dp.getRight(), out);
            }
        } else if (expr instanceof BinaryExpression) {
            collectSendsFromExpr(((BinaryExpression) expr).getLeft(), out);
            collectSendsFromExpr(((BinaryExpression) expr).getRight(), out);
        } else if (expr instanceof UnaryExpression)
            collectSendsFromExpr(((UnaryExpression) expr).getExpression(), out);
        else if (expr instanceof TermPrimary && ((TermPrimary) expr).getParentSuffixPrimary() != null)
            for (Expression arg : ((TermPrimary) expr).getParentSuffixPrimary().getArguments())
                collectSendsFromExpr(arg, out);
    }

    private static void collectVarAccesses(Statement stmt, Set<String> stateVars,
            Set<String> writes, Set<String> reads) {
        if (stmt == null) return;
        if (stmt instanceof BlockStatement)
            for (Statement s : ((BlockStatement) stmt).getStatements())
                collectVarAccesses(s, stateVars, writes, reads);
        else if (stmt instanceof BinaryExpression && "=".equals(((BinaryExpression) stmt).getOperator())) {
            // assignments are BinaryExpression with "=" operator
            collectWrittenNames(((BinaryExpression) stmt).getLeft(), stateVars, writes);
            collectReadNames(((BinaryExpression) stmt).getRight(), stateVars, reads);
        } else if (stmt instanceof ConditionalStatement) {
            ConditionalStatement cs = (ConditionalStatement) stmt;
            collectReadNames(cs.getCondition(), stateVars, reads);
            collectVarAccesses(cs.getStatement(), stateVars, writes, reads);
            if (cs.getElseStatement() != null)
                collectVarAccesses(cs.getElseStatement(), stateVars, writes, reads);
        } else if (stmt instanceof WhileStatement) {
            collectReadNames(((WhileStatement) stmt).getCondition(), stateVars, reads);
            collectVarAccesses(((WhileStatement) stmt).getStatement(), stateVars, writes, reads);
        } else if (stmt instanceof ForStatement)
            collectVarAccesses(((ForStatement) stmt).getStatement(), stateVars, writes, reads);
        else if (stmt instanceof Expression)
            collectReadNames((Expression) stmt, stateVars, reads);
    }

    private static void collectWrittenNames(Expression expr, Set<String> stateVars, Set<String> writes) {
        if (expr instanceof TermPrimary) {
            String name = ((TermPrimary) expr).getName();
            if (stateVars.contains(name)) writes.add(name);
        }
    }

    private static void collectReadNames(Expression expr, Set<String> stateVars, Set<String> reads) {
        if (expr == null) return;
        if (expr instanceof TermPrimary) {
            TermPrimary tp = (TermPrimary) expr;
            if (stateVars.contains(tp.getName())) reads.add(tp.getName());
            if (tp.getParentSuffixPrimary() != null)
                for (Expression arg : tp.getParentSuffixPrimary().getArguments())
                    collectReadNames(arg, stateVars, reads);
        } else if (expr instanceof BinaryExpression) {
            collectReadNames(((BinaryExpression) expr).getLeft(), stateVars, reads);
            collectReadNames(((BinaryExpression) expr).getRight(), stateVars, reads);
        } else if (expr instanceof UnaryExpression)
            collectReadNames(((UnaryExpression) expr).getExpression(), stateVars, reads);
        else if (expr instanceof DotPrimary) {
            DotPrimary dp = (DotPrimary) expr;
            if (!isReactiveClassType(dp.getLeft() != null ? dp.getLeft().getType() : null))
                collectReadNames(dp.getLeft(), stateVars, reads);
        }
    }

    // ── model structure helpers ───────────────────────────────────────────────

    private static List<ReactiveClassDeclaration> inheritanceChain(
            ReactiveClassDeclaration rcd, Map<String, ReactiveClassDeclaration> typeToRcd) {
        List<ReactiveClassDeclaration> chain = new ArrayList<>();
        ReactiveClassDeclaration current = rcd;
        while (current != null) {
            chain.add(current);
            current = current.getExtends() != null
                    ? typeToRcd.get(current.getExtends().getTypeName()) : null;
        }
        return chain;
    }

    private static List<String> collectFullKnownRebecNames(ReactiveClassDeclaration rcd,
            Map<String, ReactiveClassDeclaration> typeToRcd) {
        List<ReactiveClassDeclaration> chain = inheritanceChain(rcd, typeToRcd);
        Collections.reverse(chain); // root first so slot indices match binding order
        List<String> names = new ArrayList<>();
        for (ReactiveClassDeclaration ancestor : chain)
            for (FieldDeclaration fd : ancestor.getKnownRebecs())
                for (VariableDeclarator vd : fd.getVariableDeclarators())
                    names.add(vd.getVariableName());
        return names;
    }

    private static Set<String> collectAllStateVarNames(ReactiveClassDeclaration rcd,
            Map<String, ReactiveClassDeclaration> typeToRcd) {
        Set<String> names = new HashSet<>();
        for (ReactiveClassDeclaration ancestor : inheritanceChain(rcd, typeToRcd))
            for (FieldDeclaration fd : ancestor.getStatevars())
                for (VariableDeclarator vd : fd.getVariableDeclarators())
                    names.add(vd.getVariableName());
        return names;
    }

    private static int computeMsgIdBase(ReactiveClassDeclaration rcd,
            Map<String, ReactiveClassDeclaration> typeToRcd) {
        int cnt = 1; // 0 reserved for empty queue
        ReactiveClassDeclaration current = rcd;
        while (current.getExtends() != null) {
            current = typeToRcd.get(current.getExtends().getTypeName());
            if (current == null) break;
            cnt += current.getMsgsrvs().size();
        }
        return cnt;
    }

    private static String resolveTargetInstance(Expression left, String senderInst,
            List<String> krNames, List<String> bindings) {
        if (!(left instanceof TermPrimary)) return null;
        String name = ((TermPrimary) left).getName();
        if ("self".equals(name)) return senderInst;
        if ("sender".equals(name)) return null;
        int slot = krNames.indexOf(name);
        if (slot >= 0 && bindings != null && slot < bindings.size()) return bindings.get(slot);
        return null;
    }

    private static Integer resolveMessageId(String msgName, String typeName, ModelIndex idx) {
        ReactiveClassDeclaration rcd = idx.typeToRcd.get(typeName);
        while (rcd != null) {
            int base = idx.startMsgId.get(rcd.getName());
            List<MsgsrvDeclaration> ms = rcd.getMsgsrvs();
            for (int i = 0; i < ms.size(); i++)
                if (msgName.equals(ms.get(i).getName())) return base + i;
            rcd = rcd.getExtends() != null ? idx.typeToRcd.get(rcd.getExtends().getTypeName()) : null;
        }
        return null;
    }

    private static boolean isReactiveClassType(Type t) {
        if (t == null) return false;
        Type base = (t instanceof ArrayType) ? ((ArrayType) t).getOrdinaryPrimitiveType() : t;
        return base.canTypeUpCastTo(CoreRebecaTypeSystem.REACTIVE_CLASS_TYPE);
    }
}
