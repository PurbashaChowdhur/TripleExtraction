from rdflib import ConjunctiveGraph, exceptions
from rdflib import RDFS, RDF, BNode, OWL, Graph


def sort_uri_list_by_name(uri_list, bypass_namespace=False):
    """
     Sorts a list of uris

     bypassNamespace:
        based on the last bit (usually the name after the namespace) of a uri
        It checks whether the last bit is specified using a # or just a /, eg:
             rdflib.URIRef('http://purl.org/ontology/mo/Vinyl'),
             rdflib.URIRef('http://purl.org/vocab/frbr/core#Work')

     """

    def get_last_bit(uri_string):
        try:
            x = uri_string.split("#")[1]
        except:
            x = uri_string.split("/")[-1]
        return x

    try:
        if bypass_namespace:
            return sorted(uri_list, key=lambda x: get_last_bit(x.__str__()))
        else:
            return sorted(uri_list)
    except:
        # TODO: do more testing.. maybe use a unicode-safe method instead of __str__
        print("Error in <sort_uri_list_by_name>: possibly a UnicodeEncodeError")
        return uri_list


class OntoInspector(object):
    """Class that includes methods for querying an RDFS/OWL ontology"""

    def __init__(self, uri, language=""):
        super(OntoInspector, self).__init__()

        self.rdfGraph = ConjunctiveGraph()
        try:
            self.rdfGraph.parse(uri, format="xml")
        except:
            try:
                self.rdfGraph.parse(uri, format="n3")
            except:
                raise exceptions.Error("Could not parse the file! Is it a valid RDF/OWL ontology?")

        finally:
            # let's cache some useful info for faster access
            self.baseURI = self.get_ontology_uri() or uri
            self.all_classes = self.__get_all_classes()
            self.top_layer = self.__get_top_classes()
            self.tree = self.__get_tree()

    def __inspect(self):
        valid_triples = []
        for s, v, o in self.rdfGraph.triples((None, None, OWL.ObjectProperty)):
            triple = {
                "subject": None,
                "predicate": s.n3(),
                "objects": [],
            }
            for p, o in self.rdfGraph.predicate_objects(s):
                # end node
                if str(p).endswith("range"):
                    triple["objects"].append(o.n3())
                if str(p).endswith("domain"):
                    triple["subject"] = o.n3()

                # print(s, p, o)
            if len(triple["objects"]) > 0 and triple["subject"] is not None:
                # print(triple["predicate"])
                valid_triples.append(triple)

        return valid_triples

    def entities_and_predicates(self):
        entities = [str(ent).split("#")[-1] for ent in self.all_classes]
        predicates = [str(triple["predicate"]).split("#")[-1].replace(">", "") for triple in self.__inspect()]

        return entities, predicates

    def is_blank_node(self, a_class):
        """ small utility that checks if a class is a blank node """
        if type(a_class) == BNode:
            return True
        else:
            return False

    def get_ontology_uri(self, return_as_string=True):
        """
        In [15]: [x for x in o.rdfGraph.triples((None, RDF.type, OWL.Ontology))]
        Out[15]:
        [(rdflib.URIRef('http://purl.com/net/sails'),
          rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
          rdflib.URIRef('http://www.w3.org/2002/07/owl#Ontology'))]

        Mind that this will work only for OWL ontologies.
        In other cases we just return None, and use the URI passed at loading time
        """
        test = [x for x, y, z in self.rdfGraph.triples((None, RDF.type, OWL.Ontology))]
        if test:
            if return_as_string:
                return str(test[0])
            else:
                return test[0]
        else:
            return None

    def __get_all_classes(self, class_predicate="", remove_blank_nodes=True):
        """
        Extracts all the classes from a model
        We use the RDFS and OWL predicate by default; also, we extract non explicitly declared classes
        """

        rdfGraph = self.rdfGraph
        exit = []

        if not class_predicate:
            for s, v, o in rdfGraph.triples((None, RDF.type, OWL.Class)):
                exit.append(s)
            for s, v, o in rdfGraph.triples((None, RDF.type, RDFS.Class)):
                exit.append(s)

            # this extra routine makes sure we include classes not declared explicitly
            # eg when importing another onto and subclassing one of its classes...
            for s, v, o in rdfGraph.triples((None, RDFS.subClassOf, None)):
                if s not in exit:
                    exit.append(s)
                if o not in exit:
                    exit.append(o)

            # this extra routine includes classes found only in rdfs:domain and rdfs:range definitions
            for s, v, o in rdfGraph.triples((None, RDFS.domain, None)):
                if o not in exit:
                    exit.append(o)
            for s, v, o in rdfGraph.triples((None, RDFS.range, None)):
                if o not in exit:
                    exit.append(o)

        else:
            if class_predicate == "rdfs" or class_predicate == "rdf":
                for s, v, o in rdfGraph.triples((None, RDF.type, RDFS.Class)):
                    exit.append(s)
            elif class_predicate == "owl":
                for s, v, o in rdfGraph.triples((None, RDF.type, OWL.Class)):
                    exit.append(s)
            else:
                raise exceptions.Error("ClassPredicate must be either rdf, rdfs or owl")

        exit = list(set(exit))

        if remove_blank_nodes:
            exit = [x for x in exit if not self.is_blank_node(x)]

        return sort_uri_list_by_name(exit)

    def get_class_direct_supers(self, a_class, exclude_bnodes=True):
        return_list = []
        for s, v, o in self.rdfGraph.triples((a_class, RDFS.subClassOf, None)):
            if exclude_bnodes:
                if not self.is_blank_node(o):
                    return_list.append(o)
            else:
                return_list.append(o)

        return sort_uri_list_by_name(list(set(return_list)))

    def get_class_direct_subs(self, a_class, exclude_bnodes=True):
        return_list = []
        for s, v, o in self.rdfGraph.triples((None, RDFS.subClassOf, a_class)):
            if exclude_bnodes:
                if not self.is_blank_node(s):
                    return_list.append(s)

            else:
                return_list.append(s)

        return sort_uri_list_by_name(list(set(return_list)))

    def get_class_all_subs(self, a_class, return_list=None, exclude_bnodes=True):
        if return_list is None:
            return_list = []
        for sub in self.get_class_direct_subs(a_class, exclude_bnodes):
            return_list.append(sub)
            self.get_class_all_subs(sub, return_list, exclude_bnodes)
        return sort_uri_list_by_name(list(set(return_list)))

    def get_class_all_supers(self, a_class, return_list=None, exclude_bnodes=True):
        if return_list is None:
            return_list = []
        for ssuper in self.get_class_direct_supers(a_class, exclude_bnodes):
            return_list.append(ssuper)
            self.get_class_all_supers(ssuper, return_list, exclude_bnodes)
        return sort_uri_list_by_name(list(set(return_list)))

    def get_class_siblings(self, a_class, exclude_bnodes=True):
        return_list = []
        for father in self.get_class_direct_supers(a_class, exclude_bnodes):
            for child in self.get_class_direct_subs(father, exclude_bnodes):
                if child != a_class:
                    return_list.append(child)

        return sort_uri_list_by_name(list(set(return_list)))

    def __get_top_classes(self, class_predicate=''):

        """ Finds the top class in an ontology (works also when we have more than on superclass)
        """

        return_list = []

        # gets all the classes
        for each_class in self.__get_all_classes(class_predicate):
            x = self.get_class_direct_supers(each_class)
            if not x:
                return_list.append(each_class)

        return sort_uri_list_by_name(return_list)

    def __get_tree(self, father=None, out=None):

        """ Reconstructs the taxonomic tree of an ontology, from the 'topClasses' (= classes with no supers, see below)
            Returns a dictionary in which each class is a key, and its direct subs are the values.
            The top classes have key = 0

            Eg.
            {'0' : [class1, class2], class1: [class1-2, class1-3], class2: [class2-1, class2-2]}
        """
        if not father:
            out = {}
            top_classes = self.top_layer
            out[0] = top_classes

            for top in top_classes:
                children = self.get_class_direct_subs(top)
                out[top] = children
                for potential_father in children:
                    self.__get_tree(potential_father, out)

            return out
        else:
            children = self.get_class_direct_subs(father)
            out[father] = children
            for ch in children:
                self.__get_tree(ch, out)