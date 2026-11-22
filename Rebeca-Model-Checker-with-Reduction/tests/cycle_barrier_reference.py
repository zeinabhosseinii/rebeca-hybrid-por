#!/usr/bin/env python3
"""Finite reference for explicit full-expansion barriers; not an online graph lookup."""
from collections import Counter,deque


def reduce_with_barriers(graph):
    opened={graph.initial};closed=set();full=set();queue=deque([graph.initial])
    selected={};counts=Counter();decisions=[]
    while queue:
        state=queue.popleft();opened.remove(state);closed.add(state)
        chosen=None;exhaustive=False
        for action in sorted(graph.edges[state]):
            is_full=len(graph.edges[state])==1
            ok,evidence=(True,{'reason':'exhaustive'}) if is_full else graph.certify(state,action)
            if not ok:continue
            targets=graph.edges[state][action]
            bad=[t for t in targets if t in closed and t not in full]
            accepted=is_full or not bad
            decisions.append({'state':state,'action':action,'accepted':accepted,'exhaustive':is_full,
                              'closed_full_targets':sorted(targets & full),'rejected_targets':bad})
            if not accepted:counts['proviso_reject']+=1;continue
            counts['closed_full_accepts']+=len(targets & full)
            chosen=action;exhaustive=is_full;break
        actions=graph.edges[state] if chosen is None else {chosen:graph.edges[state][chosen]}
        selected[state]=list(actions)
        if chosen is None or exhaustive:full.add(state);counts['full']+=1
        else:counts['reduced']+=1
        for action,targets in actions.items():
            for target in sorted(targets):
                if target not in closed and target not in opened:opened.add(target);queue.append(target)
    return selected,dict(counts),decisions
