#!/usr/bin/env python3
"""Compile the template's actual alternative predicates and test their safety boundary."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
text=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
def function(name):
    start=text.index('bool TimedModelChecker::'+name)
    end=text.index('\n}\n',start)+3
    return text[start:end]
source=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>
using namespace std;
typedef int TIME_TYPE;
struct Packet {
    unsigned char method, sender, p, q;
    int time, deadline;
    bool operator==(const Packet& b) const {
        return method==b.method && sender==b.sender && p==b.p && q==b.q && time==b.time && deadline==b.deadline;
    }
};
struct Actor {
    int maxQueueLength=5, maxParamLength=2;
    unsigned char messageQueue[5]={}, senderQueue[5]={}, params[5][2]={};
    unsigned char* paramQueue[5];
    int executionTime[5]={}, deadline[5]={};
    const char* getName() { return "A"; }
    void load(const vector<Packet>& v) {
        for(int i=0;i<5;i++) {
            Packet x=i<(int)v.size()?v[i]:Packet{0,0,0,0,0,0};
            messageQueue[i]=x.method; senderQueue[i]=x.sender;
            params[i][0]=x.p; params[i][1]=x.q; paramQueue[i]=params[i];
            executionTime[i]=x.time; deadline[i]=x.deadline;
        }
    }
};
struct State { int stateID=1; } state;
struct Node { State* state; };
class TimedModelChecker {
public:
    Actor actor; Actor* rebecs[1]={&actor}; Node current={&state};
    int alternatives=1; bool safeIds[4]={false,true,true,true}; vector<int> checked;
    int getNumberOfAlternatives(int, int) { return alternatives; }
    bool areActiveActionsSafe(void*,int,int id) { checked.push_back(id); return safeIds[id]; }
    bool areAllActiveAlternativesSafe(int r, TIME_TYPE execTime);
    bool isEquivalentQueueAlternative(int r, int alternative);
};
FUNCTIONS
vector<Packet> moveHead(vector<Packet> v,int k) {
    for(int i=k;i>0;i--)swap(v[i],v[i-1]);
    return v;
}
int main() {
    TimedModelChecker c;
    vector<Packet> alphabet={{1,0,0,0,0,99},{2,0,0,0,0,99},{1,1,0,0,0,99},
        {1,0,1,0,0,99},{1,0,0,0,1,99},{1,0,0,0,0,98}};
    long merged=0;
    for(int n=1;n<=5;n++) {
        long total=1;for(int i=0;i<n;i++)total*=alphabet.size();
        for(long code=0;code<total;code++) {
            vector<Packet> v;long value=code;
            for(int i=0;i<n;i++){v.push_back(alphabet[value%alphabet.size()]);value/=alphabet.size();}
            c.actor.load(v);
            assert(!c.isEquivalentQueueAlternative(0,0));
            for(int k=1;k<n;k++) {
                bool duplicate=c.isEquivalentQueueAlternative(0,k);
                assert(duplicate==(v[k]==v[k-1]));
                if(duplicate){assert(moveHead(v,k)==moveHead(v,k-1));merged++;}
            }
        }
    }
    assert(merged>0);
    // Equal nonadjacent messages with an intervening different one must survive.
    c.actor.load({alphabet[0],alphabet[1],alphabet[0]});
    assert(!c.isEquivalentQueueAlternative(0,2));
    c.actor.load({alphabet[0],alphabet[0]});c.actor.paramQueue[1]=NULL;
    assert(!c.isEquivalentQueueAlternative(0,1));
    c.actor.load({alphabet[0],alphabet[1]});c.alternatives=2;
    assert(c.areAllActiveAlternativesSafe(0,0));
    assert(c.checked==vector<int>({1,2}));
    c.safeIds[2]=false;c.checked.clear();
    assert(!c.areAllActiveAlternativesSafe(0,0)); // safe head cannot hide unsafe alternative
    assert(c.checked==vector<int>({1,2}));
    c.safeIds[2]=true;c.safeIds[1]=false;
    assert(!c.areAllActiveAlternativesSafe(0,0));
    cout<<"PASS: exhaustive queue equivalence, nonadjacent counterexample, metadata differences, all-alternative safety"<<endl;
}
'''.replace('FUNCTIONS',function('areAllActiveAlternativesSafe')+'\n'+function('isEquivalentQueueAlternative'))
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'queue.cpp';cpp.write_text(source)
    for optimization in ('-O0','-O2'):
        subprocess.run(['g++','-std=c++11',optimization,'-Wall','-Wextra','-Werror',str(cpp),'-o',str(Path(tmp)/'test')],check=True)
        subprocess.run([str(Path(tmp)/'test')],check=True)
