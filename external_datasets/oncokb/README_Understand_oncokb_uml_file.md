How to read the uml diagram ?

The diagram shows how we can read OncoKB atasets with our tables.
Before that, we have to know OncoKB gives us two differents datasets : all variants, and actionable variants; actionable variants are a part of variants.

whats happening fot the tables


GENE
OncoKB just uses the gene id and name. This corresponds in fact at the pubmed gene id. It is a particular id by the way, we should consider using a more general one, but we should keeping this one (as an attribute dor instance).


TRANSCRIPT
In the OncoKB files, transcripts are identified with their isoform sequence and the pubmed reference of this sequence.

VARIANT
Here, variants have an alteration code, the description of the effect caused on the protein (which is exactly the same description as the code alteration), their oncogenicity level, and the mutation effect on the human organism.

Actionable gene and all tables which are linked to them are linked to a supplementary table too : the drug_effects one.

DRUG_EFFECT
This table corresponds in fact to a line of the annotated variants oncokb csv file. For a variant, a morphology (cancer type) and some drugs, it displays the level of evidence of drug effects.
The drug effect is enough particular to conceptualize.
Firstly, a gene can be actionable if there is some drugs which have an effect on it. This means, for an actionable gene, you have a drug effect instance linked to drug(s), morphology(ies), and reference(s).
In the case where the gene is not considered as actionable, the drug effect instance exists, but it is empty. However, you can still have references linked to it.

DRUG
This table contans just the name of the drug for this file.
Several drugs can appear in the same row.

MORPHOLOGY
This table contains the cancer type name.

REFERENCE
Here are all the references in all documents. The type is "pubmed id (pmid)" or "abstract" for instance, while the description corresponds to the value of the id or the full bibliographical reference.