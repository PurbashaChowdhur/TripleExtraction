from langchain_ollama import ChatOllama
import json
import re

ENTITY_PATTERN = re.compile(r'\[(\d+)\],\s(\w+):(\w+)')
PREDICATE_PATTERN = re.compile(r'\[(\d+)\]\s(\w+)\s\[(\d+)\]')

from main1 import OntoInspector


class KGExtractor:
    def __init__(self, model: str = "hf.co/bartowski/Triplex-GGUF:F32"):
        self.llm = ChatOllama(
            model=model,
            temperature=0,
            base_url="http://127.0.0.1:11434"
            # base_url="http://labs.larus-ba.it/ollama"
            # other params ...
        )

    def load_ontologies(self, ontologies=None):
        if ontologies is None:
            ontologies = []

        entities_and_predicates = {"entities": [], "predicates": []}
        for ontology in ontologies:
            inspector = OntoInspector(uri=ontology)
            entities, predicates = inspector.entities_and_predicates()
            entities_and_predicates["entities"] = entities_and_predicates["entities"] + entities
            entities_and_predicates["predicates"] = entities_and_predicates["predicates"] + predicates

        return entities_and_predicates

    def get_triplets(self, text: str = "", entities: list[str] = None, predicates: list[str] = None):
        response = self.__get_response(entities=entities, predicates=predicates, text=text)
        return self.__parse_to_triplets(response=response)

    def __get_response(self, entities: list[str] = None, predicates: list[str] = None, text: str = "") -> dict:
        if predicates is None:
            predicates = []
        if entities is None:
            entities = []

        messages = [
            # ("system", "You are a helpful translator. Translate the user sentence to English."),
            (
                "human",
                f"""Perform Named Entity Recognition (NER) and extract knowledge graph triplets from the text. NER identifies named entities of given entity types, and triple extraction identifies relationships between entities using specified predicates.

                   **Entity Types:**
                   {entities}

                   **Predicates:**
                   {predicates}

                   **Text:**
                   {text}
                """
            ),
        ]

        response = self.llm.invoke(
            messages
        )
        return json.loads(response.content.replace("```json", "").replace("```", ""))

    def __parse_to_triplets(self, response=None) -> tuple[list[dict], list[dict]]:
        if response is None:
            response = {}

        entities = []
        predicates = []
        entities_and_predicates: list[str] = response["entities_and_triples"]
        for entity_or_predicate in entities_and_predicates:
            # predicate
            if entity_or_predicate.startswith("[") and entity_or_predicate.endswith("]"):
                match = PREDICATE_PATTERN.match(entity_or_predicate)
                start = match.group(1)
                type = match.group(2)
                end = match.group(3)
                tokens = entity_or_predicate.split(" ")
                predicates.append({
                    "start": tokens[0],
                    "type": tokens[1],
                    "end": tokens[2],
                })
            else:
                match = ENTITY_PATTERN.match(entity_or_predicate)
                if len(match.groups()) == 3:
                    id = match.group(1)
                    type = match.group(2)
                    value = match.group(3)

                    entities.append({
                        "id": id,
                        "type": type,
                        "value": value,
                    })

        return entities, predicates


extractor = KGExtractor()
entities_and_predicates = extractor.load_ontologies(ontologies=["airo.rdf"])

ent, pred = extractor.get_triplets(
    entities=entities_and_predicates["entities"],
    predicates=entities_and_predicates["predicates"],
    text="""
        1. A risk management system shall be established, implemented, documented and maintained in relation to 
        high-risk AI systems. 
        2. The risk management system shall be understood as a continuous iterative process planned 
        and run throughout the entire lifecycle of a high-risk AI system, requiring regular systematic review and 
        updating. It shall comprise the following steps: 
            (a) the identification and analysis of the known and the reasonably foreseeable risks that the high-risk AI 
            system can pose to health, safety or fundamental rights when the high-risk AI system is used in accordance 
            with its intended purpose; 
            (b) the estimation and evaluation of the risks that may emerge when the high-risk AI system is used in 
            accordance with its intended purpose, and under conditions of reasonably foreseeable misuse; 
            (c) the evaluation of other risks possibly arising,based on the analysis of data gathered from 
            the post-market monitoring system referred to in Article 72; 
            (d) the adoption of appropriate and targeted risk management measures designed to address the risks 
            identified pursuant to point (a). 
        3. The risks referred to in this Article shall concern only those which may be reasonably mitigated 
        or eliminated through the development or design of the high-risk AI system, or the provision of adequate 
        technical information. 
        4. The risk management measures referred to in paragraph 2, point (d), shall give due 
        consideration to the effects and possible interaction resulting from the combined application of the 
        requirements set out in this Section, with a view to minimising risks more effectively while achieving 
        an appropriate balance in implementing the measures to fulfil those requirements. 
        5. The risk management measures referred to in paragraph 2, point (d), shall be such that the relevant residual 
        risk associated with each hazard, as well as the overall residual risk of the high-risk AI systems is judged to 
        be acceptable. In identifying the most appropriate risk management measures, the following shall be ensured: 
            (a) elimination or reduction of risks identified and evaluated pursuant to paragraph 2 in as far as 
            technically feasible through adequate design and development of the high-risk AI system; 
            (b) where appropriate, implementation of adequate mitigation and control measures 
            addressing risks that cannot be eliminated; 
            (c) provision of information required pursuant to Article 13 and, where appropriate, training to deployers. 
            With a view to eliminating or reducing risks related to the use of the high-risk AI system, due 
            consideration shall be given to the technical knowledge, experience, education, the training to be expected 
            by the deployer, and the presumable context in which the system is intended to be used. 
        6. High-risk AI systems shall be tested for the purpose of identifying the most appropriate and targeted 
        risk management measures. Testing shall ensure that high-risk AI systems perform consistently for their intended 
        purpose and that they are in compliance with the requirements set out in this Section. 
        7. Testing procedures may include testing in real-world conditions in accordance with Article 60. 
        8. The testing of high-risk AI systems shall be performed, as appropriate, at any time throughout the 
        development process, and, in any event, prior to their being placed on the market or put into service. 
        Testing shall be carried out against prior defined metrics and probabilistic thresholds 
        that are appropriate to the intended purpose of the high-risk AI system. 
        9. When implementing the risk management system as provided for in paragraphs 1 to 7, providers shall give 
        consideration to whether in view of its intended purpose the high-risk AI system is likely to have an adverse 
        impact on persons under the age of 18 and, as appropriate, other vulnerable groups. 
        10. For providers of high-risk AI systems that are subject to requirements regarding internal risk management 
        processes under other relevant provisions of Union law, the aspects provided in paragraphs 1 to 9 may be part 
        of, or combined with, the risk management procedures established pursuant to that law. 
        """
)

for e in ent:
    print(e)
for p in pred:
    print(p)
