#!/usr/bin/env python3
# Keep the function signature,
# but replace its body with your implementation.
#
# Note that this is the driver function.
# Please write a well-structured implemention by creating other functions
# outside of this one,
# each of which has a designated purpose.
#
# As a good programming practice,
# please do not use any script-level variables that are modifiable.
# This is because those variables live on forever once the script is imported,
# and the changes to them will persist across different invocations of the
# imported functions.

# to test if external commands were used:
# after running strace -f -o topo-test.tr pytest
# do:
# grep exec topo-test.tr (nothing but the pytest command itself should output)
# grep system topo-test.tr (nothing should output)

import sys
import os
import zlib
from pathlib import Path

class CommitNode:
    def __init__(self, commit_hash):
        self.commit_hash = commit_hash
        self.parents = []
        self.children = []
        self.branch = ""
        self.visit = -1  # 0 as temp mark, 1 as permanent mark
        self.cidx = 0

    def add_parent(self, parent):  # parents organized as sorted list
        i = 0
        h1 = parent.commit_hash
        while i < len(self.parents):
            h2 = self.parents[i].commit_hash
            if (h2 == h1):
                return
            if (h2 > h1):
                self.parents.insert(i, parent)
                return
            i += 1
        self.parents.append(parent)

    def add_child(self, child):  # children organized as sorted list
        i = 0
        h1 = child.commit_hash
        while i < len(self.children):
            h2 = self.children[i].commit_hash
            if (h2 == h1):
                return
            if (h2 > h1):
                self.children.insert(i, child)
                return
            i += 1
        self.children.append(child)

    def hash(self):
        return self.commit_hash

    def get_parents(self):
        return self.parents

    def get_children(self):
        return self.children

    def set_branch(self, val):
        self.branch = val

    def get_branch(self):
        return self.branch

    def get_visit(self):
        return self.visit

    def set_visit(self, val):
        self.visit = val

    def get_cidx(self):
        return self.cidx

    def set_cidx(self, val):
        self.cidx = val

    # comparison operator
    def __lt__(self, node1):
        self.commit_hash < node1.commit_hash

class CommitDict:
    def __init__(self):
        self.dict = dict()

    def add(self, nodehash, node):
        self.dict[nodehash] = node
        return node

    def get(self, nodehash):
        return self.dict.get(nodehash)

    def getdict(self):
        return self.dict

# find the directory that contains the .git directory
def locate_git():
    mypath = os.getcwd()
    foundgit = False
    while not foundgit:
        parentdir = os.path.dirname(mypath)
        for file in os.scandir():
            if file.is_dir and file.name == '.git':
                foundgit = True
                return mypath
        if not foundgit:
            # return if we have reached the root node and ".git" not found
            if mypath == parentdir:
                return ""
            else:
                mypath = parentdir
                os.chdir(mypath)
    return mypath.absolute

# find all local branches in .git/refs
def get_branches(gitpath):
    newpath = gitpath + "/.git/refs/heads"
    headpath = gitpath + "/.git/HEAD"
    branches = []
    file1 = open(headpath, 'r')
    line1 = file1.readline().strip()
    file1.close()
    filename = "/tmp/" + "my-" + Path(gitpath).name + "-branch-heads.txt"
    mydict = CommitDict()
    for dirpath, dirname, files in os.walk(newpath):
        for file in files:
            fn = dirpath + "/" + file
            file1 = open(fn, 'r')
            bname = fn[len(newpath)+1:]
            line1 = file1.readline().strip()
            file1.close()
            pnode = mydict.get(line1)
            if pnode is None: # add branches if they don't exist yet in the list
                node = mydict.add(line1, CommitNode(line1))
                node.set_branch(bname)
                branches.append(node)
                pnode = node
            else:
                pnode.set_branch(pnode.get_branch()+" "+file)
    return branches

# find all commit nodes by scanning everything in .git/objects
def load_commits(toppath, nodedict, cmqueue):
    for dirpath, dirname, files in os.walk(toppath):
        folder = dirpath
        prefix = dirpath[-2:]
        for x in files:
            # the object is in 2-digits/other-digits pattern
            # to get the full hash value
            file1 = open(folder + "/" + x, 'rb')
            data1 = file1.read()
            file1.close()
            data2 = zlib.decompress(data1)
            line = str(data2[:6])
            if line.startswith("b'commit'"):
                lines = data2.decode().split("\n")
                hashval = prefix + x
                node = nodedict.get(hashval)
                if node is None:
                    node = nodedict.add(hashval, CommitNode(hashval))
                    cmqueue.append(node)
                i = 1
                while i < len(lines):
                    line = lines[i]
                    i += 1
                    if line.startswith("parent"):  # add parent nodes
                        vals = line.split(' ')
                        pnode = nodedict.get(vals[1])
                        if pnode is None:
                            pnode = nodedict.add(vals[1], CommitNode(vals[1]))
                            cmqueue.append(pnode)
                        node.add_parent(pnode)
                        pnode.add_child(node)
                    else:
                        break

# generate a topological ordering sing a iterative depth-first search
def build_topology(cmqueue, tlist):
    for x in cmqueue:
        visit = x.get_visit()
        if visit > 0:  # has permanent mark
            continue
        if visit < 0:  # no mark
            x.set_visit(0)  # set temp mark
            x.set_cidx(0)  # index to track how many children have been iterated over
            nq = []
            nq.append(x)
            while len(nq) > 0:
                y = nq[len(nq)-1]  # peek at stack top
                if (y.get_visit() > 0):  # already has permanent mark
                    nq.pop()
                    continue
                idx = y.get_cidx()
                nchild = len(y.get_children())
                if nchild == 0 or idx >= nchild:  # checked all children?
                    tlist.append(y)
                    y.set_visit(1)  # set permanent mark
                    nq.pop()
                else:
                    z = y.get_children()[idx]
                    nq.append(z)
                    idx += 1  # visit next child next time
                    y.set_cidx(idx)

# print the topological ordering
def print_path(tlist):
    finished = False
    for x in tlist:
        x.set_visit(0)
        x.set_cidx(0)
    pathcount = 0
    nidx = 0
    while not finished:
        while nidx < len(tlist):
            x = tlist[nidx]
            visit = x.get_visit()
            nparents = len(x.get_parents())
            if visit < nparents:
                ph = x
                break
            else:
                nidx += 1
        # done if no new leaf found
        if (nidx >= len(tlist)):
            finished = True
            break
        # build path
        if pathcount > 0:
            sys.stdout.write("\n")
        pathcount += 1
        pathend = False
        x = ph
        while not pathend:
            visit = x.get_visit()
            nc = len(x.get_children())
            np = len(x.get_parents())
            cidx = x.get_cidx()
            if nc > 1 and cidx < nc:
                # sticky end if next node is not parent of current node
                s = x.hash() + "="
                sys.stdout.write("{0}\n".format(s))
                pathend = True
                break
            else:
                # sticky start after a newline has been printed
                s = x.hash() + " " + x.get_branch()
                if np > 0 and visit > 0:
                    s = "="+x.hash()
                sys.stdout.write("{0}\n".format(s))

            if np > 0:
                # get parent
                px = x
                if (visit > np):
                    x = x
                x = x.get_parents()[visit]
                px.set_visit(px.get_visit() + 1)
                cidx = x.get_cidx()
                nc = len(x.get_children())
                if cidx < nc:
                    x.set_cidx(cidx+1)
            else:
                break   # reached root
    sys.stdout.write("\n")

# generate the topological order
def topo_order_commits():
    gitpath = locate_git()
    if gitpath == "":
        sys.stderr.write("Not inside a Git repository")
        exit(1)
    branches = get_branches(gitpath)
    allcommits = CommitDict()
    cmqueue = []    # queue to hold all nodes

# check branches and build graph iteratively
    toppath = gitpath + "/.git/objects"
    load_commits(toppath, allcommits, cmqueue)
    for x in branches:
        node = allcommits.get(x.hash())
        if node is not None:
            node.set_branch(x.get_branch())

# generate a topological ordering of the commits
    topolist = []
    build_topology(cmqueue, topolist)

# print the ordering
    print_path(topolist)

if __name__ == '__main__':
    topo_order_commits()
