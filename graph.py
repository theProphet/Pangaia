#!/usr/bin/env python
# Mark Janssen, <average@mit.edu> February 5, 2001

"""Graph class."""

__version__ = "$Revision: 2.12 $"
__author__  = "$Author: average $"
__date__    = "$Date: 2003/06/17 06:58:52 $"

#change a lot of these for loops to use faster map() function (see FAQ and QuickReference)
#also: map/reduce/filter now work with any iterable object (including dictionaries!)
#add persistence
#implementation options:  { id: Vertex(id).{tail:Edge(tail)}}, {Vertex(id):kjSet(Edges)
#  {id: vertex(id)}{id:{Edge(proxy(Vertex(tail)))}; g.add(vertex, VertType=BaseVert), etc..
#XXX Use of exceptions for control flow may prevent seeing actual errors.  Perhaps catch exception, plus error string and assert string is as expected
#XXX Fix default value issues for Vertex: g.add(5) makes g[5].default=1 only when 5 not in g

from __future__ import generators

from defdict import *

#EdgeBaseType = int
VertexBaseType = defdict
GraphBaseType = defdict
EDGEVALUE = 1

_DEBUG = True
_PROFILE = True

NumberType = (int, float, long, complex) #for WeightedVertex validation

#should all non-verb methods (sum_in, in_degree, etc.) be properties??
#should Vertex be a subclass of WVertex? (re: __str__(), __setitem__())

class VertexMixin(object):
    """Various common vertex methods."""

    def in_vertices(self):  #O(n)
        """Return iterator over the vertices that point to self.

        >>> g = Graph()
        >>> g.add(1, [2, 3, 4])
        >>> g.add(2, [3, 2])
        >>> list(g[2].in_vertices())      #XXX arbitrary order
        [1, 2]
        """
        for head in self._graph.itervalues():
            if self._id in head:
                yield head._id

    def in_degree(self):
        """Return number of edges pointing into vertex.

        >>> g = Graph()
        >>> g.add(1, [2, 3, 4])
        >>> g.add(2, [3, 2])
        >>> g[1].in_degree(), g[2].in_degree(), g[4].in_degree()
        (0, 2, 1)
        """
        return len(list(self.in_vertices()))

    out_vertices = VertexBaseType.iterkeys
    out_degree = VertexBaseType.__len__

    def _validate(self):
        """Assert Vertex invariants.

        >>> g = Graph()
        >>> g.add(1,2)
        >>> dict.__setitem__(g[1], 3, 1)  #tail value 3 not in graph
        >>> g[1]._validate()
        Traceback (most recent call last):
        AssertionError: Non-existant tail 3 in vertex 1
        >>> g.add(3,1)
        >>> g[3]._id = 2
        >>> g._validate()  #should call vertex validates too
        Traceback (most recent call last):
        AssertionError: _graph[_id] is not self
        """
        hash(self._id) #id should be hashable
        assert isinstance(self._graph, Graph), "_graph attribute not a Graph"
        assert self._graph[self._id] is self,  "_graph[_id] is not self"
        for t in self:
            assert t in self._graph, "Non-existant tail %r in vertex %r" % (t, self._id)


class WeightedEdgeMixin(VertexMixin):
    """Various methods for vertex types that have number edge values."""

    def sum_in(self):
        """Return sum of all edges that point to vertex.

        >>> g = Graph(VertexType=WVertex)
        >>> g.add(1, [1, 2, 3])
        >>> g.add(4, 1, 3)
        >>> g[1].sum_in(), g[3].sum_in(), g[4].sum_in()
        (4, 1, 0)
        """
        g, t = self._graph, self._id
        sum = 0
        for h in self.in_vertices():
            sum += g[h][t]
        return sum

    def sum_out(self):
        """Return sum of all edges that leave from vertex.

        >>> g = Graph(VertexType=WVertex)
        >>> g.add(1, [1, 2, 3])
        >>> g.add(1, 4, 3)
        >>> g[1].sum_out(), g[2].sum_out()
        (6, 0)
        """
        return sum(self.itervalues())

    def __str__(self): #XXX this seems redundant
        """Return string of tail vertices with edge weight values.

        >>> g = Graph(VertexType=WVertex)
        >>> g.add(1, [1, 3, 4]); g.add(1, 3, 7)
        >>> print g[1]
        {1: 1, 3: 7, 4: 1}
        """
        if _DEBUG: self._validate() #XXX validate gets called in parent class?
        if not self: return '{}'    #nothing to sort
        keys = self.keys()
        keys.sort()
        return '{%s}' % ', '.join(["%r: %r" % (k, self[k]) for k in keys])

    def _validate(self):
        super(WeightedEdgeMixin, self)._validate() #Vertex._validate(self)
        for weight in self.itervalues():
            assert isinstance(weight, NumberType)


class Vertex(VertexBaseType, VertexMixin):
    """Vertex holds the set of the vertices of its own outward directed edges.
    Edge values are user-settable and use overwrite semantics."""
    #Add id property to determine id, given Vertex
    #XXX figure out what to do wrt edge value: should Vertex take no default edgevalue and leave it to WVertex?

    __slots__ = ['_graph', '_id']  #Put all Vertex attributes here.  Uses base class' dictionary, instead of creating duplicate

    def __init__(self, graph, id, init={}, edge_value=EDGEVALUE, collision=OVERWRITE):
        """Create a vertex object in graph.  Assumes id already in graph.
        Will add tails in init as necessary."""
        self._graph = graph  #graph to which this vertex belongs
        self._id = id
        super(Vertex, self).__init__(init, edge_value, collision)
        if init: graph.add(list(init)) #ensure tails are in graph

    def add(self, tail, edge_value=USE_DEFAULT, collision=OVERWRITE):
        """Add the tails to Vertex with optional edge value.  Add tails to graph if needed.

        >>> g = Graph(VertexType=WVertex)
        >>> g.add(5)        #add vertex with id=5 to graph, default edge value=1
        >>> g[5].add(5)     #edges pointing back to self are allowed
        >>> g[5].add(7, 42) #add single out-edge from vertex 5 to 7 with weight 42
        >>> assert 7 in g   #vertex 7 automatically added to graph
        >>> g[5].add([3, 2, 4])   #add 3 out edges from 5, default weight 1
        >>> print g[5]      #show out-edges from vertex 5
        {2: 1, 3: 1, 4: 1, 5: 1, 7: 42}
        >>> g[5].add(7, 24) #edge values are over-written
        >>> g[5][7]
        24
        >>> g[5].add(7)     #edge value over-written with default if not specified
        >>> g[5][7]
        1
        """
        try:  #single tail addition
            self.setdefault(tail, edge_value, collision)
        except TypeError, error:  #multiple tail addition
            if not isinstance(tail, list): raise TypeError(error)
            self.update(tail, edge_value, collision)

    def discard(self, tail):
        """Removes tail(s) if present, otherwise does nothing.

        >>> g = Graph()
        >>> g.add(5, range(5))
        >>> print g[5]
        {0, 1, 2, 3, 4}
        >>> g[5].discard(3)     #remove single edge
        >>> g[5].discard(90)    #discard of non-existent edge ignored
        >>> g[5].discard([0, 1, 90]) #discard multiple edges
        >>> print g[5]
        {2, 4}
        """
        try: #single tail removal
            del self[tail]
        except LookupError:  return     #ignore non-existent tails
        except TypeError, error: #must have been given a tail list
            if not isinstance(tail, list): raise TypeError(error)
            for t in tail:  #XXX inefficient if self is near empty
                try:
                    del self[t]
                except LookupError:
                    if not len(self): break  #good place to check if self is empty yet...

    def __setitem__(self, tail, value):
        """Set edge value.  If tail does not exist, it is created and added to graph
        if necessary.

        >>> g = Graph(VertexType=WVertex)
        >>> g[1][2] = 1
        >>> g[1][3] += 1    #new tail (3): starts as value False (0), now add 1.
        >>> print g
        {1: {2: 1, 3: 1}, 2: {}, 3: {}}
        """
        if type(self) is Vertex and value!=self.default: raise ValueError("Vertex type does not support edge-value assignment.")
        if tail not in self._graph: #do this first to preserve invariants in case vertex addition fails
            self._graph.add(tail)
        super(Vertex, self).__setitem__(tail, value)

    def __getitem__(self, tail):
        """Return edge value or False if tail non-existent.

        >>> g = Graph(VertexType=WVertex)
        >>> g[1][3]
        False
        >>> g.add(1,3)
        >>> g[1][3]
        1
        """
        return dict.get(self, tail, False)

    def __str__(self):
        """Return string of tail vertices in set notation.

        >>> g = Graph()
        >>> g.add(1, [1, 3, 4])
        >>> print g[1]
        {1, 3, 4}
        """
        if _DEBUG: self._validate()
        if not self: return '{}'    #nothing to sort
        keys = self.keys()
        keys.sort()
        return '{%s}' % ', '.join(map(repr, keys))

    def copy(self): raise NotImplementedError


class WVertex(WeightedEdgeMixin, Vertex):
    """Vertex with methods to sum edge weights."""


def MERGE_VERTEX(g, h, vert): g[h].update(vert)

class Graph(GraphBaseType):
    """Basic class implementing a directed Graph.  Vertices without edges are allowed.
    Self-referencing vertices are allowed."""
    #Basic data structure {vertex id: {t1: edge; t2: edge}}
    #Add label to __init__ to attach description to graph?
    #Perhaps make default vertex type WVertex and change doctests accordingly.

    __slots__ = ['VertexType']

    def __init__(self, initgraph=None, VertexType=Vertex):
        """Create the graph, optionally initializing from another graph.
        Optional VertexType parameter can be passed to specify default vertex type.

        >>> g = Graph(VertexType=WVertex)
        >>> len(g), g
        (0, {})
        >>> g.add([1, 2, 3], [2, 3], 5)
        >>> print g
        {1: {2: 5, 3: 5}, 2: {2: 5, 3: 5}, 3: {2: 5, 3: 5}}
        >>> g2 = Graph(g, Vertex)       #can initialize with other Graph type, will convert to Vertex type
        >>> print g2
        {1: {2, 3}, 2: {2, 3}, 3: {2, 3}}
        """
        #XXX (Node is not subclass of Vertex) if not issubclass(VertexType, Vertex): raise TypeError("Invalid vertex type")
        self.VertexType = VertexType
        super(Graph, self).__init__(default={})
        if initgraph: #super class implementation calls dict.update on dict object so must initialize manually to ensure dict values get checked
            self.update(initgraph)  #will copy vertices to VertexType

    def update(self, other, default = USE_DEFAULT, collision=MERGE_VERTEX): #XXX could remove this if collision was attribute of defdict
        """Merges one graph with another.  All vertices will be convertex to VertexType.  Takes union of edge lists.
        >>> g1, g2 = Graph(VertexType=Vertex), Graph(VertexType=WVertex)
        >>> g1.add(1, [1, 2])
        >>> g2.add(3, [2, 3]); g2.add(1, 2, 3); g2.add(1, 4, 2)
        >>> g1.update(g2)   #XXX weight values get set on plain Vertex.
        >>> print g1
        {1: {1, 2, 4}, 2: {}, 3: {2, 3}, 4: {}}
        >>> g2.add(3, 5)  #changes to g2 should not affect g1
        >>> g1._validate()
        """
        super(Graph, self).update(other, default, collision)

    def add(self, head, tail=[], edge_value=EDGEVALUE):
        """Add the vertices and/or edges.
        Parameters can be single vertex or list of vertices.
        If no second parameter given, assume vertex addition only.

        >>> g = Graph(VertexType=WVertex)
        >>> g.add(1)            #single vertex addition
        >>> g.add(1)            #adding existing vertex is ignored
        >>> g.add([2, 3, 4])    #multiple vertex addition
        >>> g.add([2])          #list containing only one vertex is allowed
        >>> print g
        {1: {}, 2: {}, 3: {}, 4: {}}

        If second parameter given, then edge addition is performed.
        Vertices are added as necessary.  An optional edge value
        is accepted as a third parameter.

        >>> g.add(2, 1)         #edge from vertex 2 to vertex 1
        >>> g.add(1, 5, 100)    #edge from 1 to new vertex 5 with weight 100
        >>> g.add(1, 5, 90)     #adding existing edge, edge value overwritten
        >>> g.add(3, 3, 2)      #loops are allowed
        >>> g.add(3, 3)         #edge weight overwritten by default if not specified
        >>> print g
        {1: {5: 90}, 2: {1: 1}, 3: {3: 1}, 4: {}, 5: {}}

        Vertex lists allowed on either parameter for multiple edge addition.

        >>> g.clear()                 #remove all vertices (and edges)
        >>> g.add(1, [0, 2])          #add edges (1, 0) and (1, 2)
        >>> g.add(1, [1])
        >>> print g
        {0: {}, 1: {0: 1, 1: 1, 2: 1}, 2: {}}
        >>> g.add(range(3), range(3)) #fully-connected 3-vertex graph
        >>> print g
        {0: {0: 1, 1: 1, 2: 1}, 1: {0: 1, 1: 1, 2: 1}, 2: {0: 1, 1: 1, 2: 1}}
        """
        #XXX if no edge_value given, then value should not be overwritten
        try:  #single head addition
            self[head].add(tail, edge_value)
        except TypeError, error:  #multiple head addition
            if not isinstance(head, list): raise TypeError(error)
            for h in head:  #XXX will add same tails multiple times
                self[h].add(tail, edge_value)

    def discard(self, head, tail=[]):
        """Remove vertices and/or edges.  Parameters can be single vertex or list of vertices.
        If tail is empty, then vertex deletions are made and any connected edges.

        >>> g = Graph()
        >>> g.add(range(3), range(4))
        >>> g.discard(1)                #remove vertex 1
        >>> g.discard(10)               #discard of non-existent vertex ignored
        >>> g.discard([1])              #list with single vertex is fine
        >>> g.discard([1, 3])           #discards vertices in list
        >>> print g
        {0: {0, 2}, 2: {0, 2}}

        If tail is non-empty, then only edge deletions are made.
        >>> g.discard(0, 2)             #discard edge
        >>> g.discard(5, 0)             #non-existent edge ignored
        >>> g.discard(2, [1, 0, 2, 2])  #will discard two actual edges
        >>> print g
        {0: {0}, 2: {}}
        """
        if tail==[]:    #vertex deletions
            try:
                del self[head]
            except LookupError: pass   #do nothing if given non-existent vertex
            except TypeError, error:          #given head list
                if not isinstance(head, list): raise TypeError(error)
                for h in head[:]:       #must use copy since removing below
                    if h in self:
                        self[h].clear()
                        super(Graph, self).__delitem__(h) #don't duplicate effort (will discard in_vertices below)
                    else: head.remove(h) #for faster tail removal in next loop
                for h in self.itervalues():   #visit remaining vertices and remove occurances of head items in edge lists
                    h.discard(head)
        else:   #edge deletions only
            if not isinstance(head, list): head = [head] #quick and dirty to avoid extra code
            for h in head:
                if h in self:
                    self[h].discard(tail)
        if _DEBUG: self._validate()

    def __contains__(self, vid): #XXX probably slows things down for little value?
        """Returns non-zero if v in self.  If a list is given, all
        items are checked for containment.
        >>> g = Graph()
        >>> g[1].add([1, 2, 2, 3])
        >>> 1 in g and 2 in g
        True
        >>> [1, 2, 3] in g
        True
        >>> [1, 4] in g
        False
        >>> [] in g
        True
        """
        try:
            return dict.__contains__(self, vid)
        except TypeError, error:   #must have been given list
            if not isinstance(vid, list): raise TypeError(error)
            for v in vid:
                if not dict.__contains__(self, v):
                    return False
            return True

    def __getitem__(self, vid): #could just set equal to GraphBaseType.setdefault, but doctest module complains
        """Return value of corresponding key.  If key does not exist, create it
        with default value.

        >>> g = Graph()
        >>> g[1].add([1,2])
        >>> g[3][1]
        False
        >>> print g  #NOTE: Vertex(3) created!
        {1: {1, 2}, 2: {}, 3: {}}
        """
        return self.setdefault(vid, {}) #will convert plain {} to VertexType if necessary

    def __setitem__(self, vid, value):
        """Set graph[vid] to VertexType(value).

        >>> g = Graph(VertexType=WVertex)
        >>> g[1] = {}  #set g[1] to empty vertex (no out edges)
        >>> type(g[1])
        <class 'graph.WVertex'>
        >>> g[2] = {1: 4, 3: 9} #non-existent vertex values get created automatically
        >>> print g             #XXX what if VertexType==Vertex -> how to specify no edge value???
        {1: {}, 2: {1: 4, 3: 9}, 3: {}}
        >>> g._validate()
        >>>
        """
        #convert to VertexType or create copy of VertexType
        dict.__setitem__(self, vid, self.VertexType(self, vid, value)) #XXX shallow copy

    def __delitem__(self, head):
        """Delete a single vertex and associated edges.
        >>> g = Graph()
        >>> g.add([1, 2], [1, 2, 3])
        >>> del g[2]    #will remove vertex 2 and edges [(1, 2), (2, 1), (2, 2), (2, 3)]
        >>> print g
        {1: {1, 3}, 3: {}}

        Raises LookupError if given non-existant vertex.
        >>> del g[2]
        Traceback (most recent call last):
        ...
        KeyError: 2
        """
        dict.__getitem__(self, head).clear() #removes out vertices (bypass key creation with dict.__getitem__)
        for v in self[head].in_vertices():
            del self[v][head]
        super(Graph, self).__delitem__(head)

    def __str__(self):
        """Return graph in adjacency format.

        >>> g = Graph()
        >>> g.add(range(3), range(3))
        >>> str(g)
        '{0: {0, 1, 2}, 1: {0, 1, 2}, 2: {0, 1, 2}}'
        >>> g = Graph(VertexType=WVertex)
        >>> g.add(range(3), range(3))
        >>> str(g)
        '{0: {0: 1, 1: 1, 2: 1}, 1: {0: 1, 1: 1, 2: 1}, 2: {0: 1, 1: 1, 2: 1}}'
        """
        if _DEBUG: self._validate()
        return super(Graph, self).__str__()
        #return '{%s}' % ', '.join(map(str, self.itervalues()))

    def display(self):
        """Display adjacency list.

        >>> g=Graph()
        >>> g.add(range(2), range(3))
        >>> g.display()
        0: {0, 1, 2}
        1: {0, 1, 2}
        2: {}
        """
        for vid, v in self.iteritems():
            print "%s: %s" % (vid, v)

    #alternate syntax for various items
    vertices = GraphBaseType.iterkeys
    order = GraphBaseType.__len__

    def pop(self, key, default): raise NotImplementedError
    def popitem(self): raise NotImplementedError
    def copy(self): raise NotImplementedError

    def _validate(self):
        """Check graph invariants.

        >>> g = Graph()
        >>> g[1] = {2: 3, 3: 9}
        >>> g._validate()
        >>> dict.__setitem__(g, 1, {2: 3, 3: 9}) #bypass Graph
        >>> g._validate()
        Traceback (most recent call last):
        AssertionError: vertex type not found on 1
        """
        #NOTE:  calling this after each add/discard slows things down considerably!
        for vid, v in self.iteritems():
            assert isinstance(v, self.VertexType), "vertex type not found on " + str(vid)
            v._validate()


def gprofile(g, size=100):
    import time
    print "Profiling (ignoring debug)..."
    _DEBUG = 0
    for i in [1,2]:
        start=time.clock()
        g.add(range(size),range(100,size + 100))
        finish=time.clock()
        print "Add %i, 100-(%i+100); pass %i: %5.2fs" %  (size, size, i, (finish-start))
    for i in [1,2]:
        start=time.clock()
        g.discard(range(size + 50), range(100))#, range(1000))
        finish=time.clock()
        print "Discard (%i+50), 100; pass %i:  %5.2fs" % (size, i, (finish-start))
    g.clear()
    g.add(0)
    for i in [1,2]:
        start=time.clock()
        g[0].update(range(size))
        finish=time.clock()
        print "Update %i, %i; pass %i:  %5.2fs" % (size, size, i, (finish-start))
    g.clear()

def _test():
    import doctest, graph
    return doctest.testmod(graph, isprivate=lambda i, j: 0)

if __name__ == '__main__':
#    g=Graph(VertexType=Vertex)
#    test(g, 100)
    _test()
