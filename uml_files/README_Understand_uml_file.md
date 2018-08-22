How to read the uml diagram ?

Here is the descrition oof tables and attributes, when necessary. 
Some tables are already present in the NEXT platform database, and don't need more explanations.*

GENE

Here is the main table. Compared to the already-existing one, I just add an "actionable" attribute. "Actionable" is defined here to mean that some action can be taken by the individual and/or her physician to prevent a genetic-related disease or disorder from occurring, or to alter in some way its natural progression. 

A gene produces a lot of transcripts.
A gene can become a variant because of mutations. It exists as many variants as it exists mutations - I mean a lot of.

TRANSCRIPT

Mature RNA which will serve to build proteins. It has a particular sequence made of nucleotides.
It contains of course a reference to the gene it comes from.

VARIANT

A variant is a change in the gene sequence (adding, changing, deleting). A variant is linked to one and only one gene. Its owns an alteration code, a description, an effect on the human organism, and an oncogenicity level.

For a certain variant, we can find drug effects, which are linked to a certain drug, for a certain part of the human body (topography), for a particular type of cancer (morphology).

DRUG_EFFECT

This class contains all informations about the effect on a drug on a definied cancer type prouced by a particular variant in a particular part of the human body.
It has a description of the effect, the tier (or level of evidence, see http://oncokb.org/#/levels). We have a link to the disease diagnosed on a patient.

DRUG

This table already exists in the project database. We just have to link it to the drug effect class (by a foreign key for instance).
A drug can interact with several other drugs, having side-effects on the organism.
A drug have synonyms.

DRUG_SYNONYM

A drug synonym is linked to a particular drug. It has a code which diffirenciate it from another synonym (ex: french_name is different from english_name or danish_name, or ICD-10 coe for instance), and has a name.

REFERENCE

This table gathers all kind of external references the base contains.
It has a type attribute (abstract, article, website, etc.), a description (for a website, the url for instance: for a book, the bibliographical link), and a source (can be pubmed for instance).

DIAGNOSIS

The diagnosis in the patient disease diagnosed at a certain time.
This table doesn't need any more information compared to the one which already exists in the current project.

TOPOGRAPHY

Human body localization.
This table doesn't need any more information compared to the one which already exists in the current project.

TOPOGRAPHY SYNONYM

This table gathers all the synonyms for a certain topograhy (ex: "Poumons, "Lungs", "Lunger")
It doesn't need any more information compared to the one which already exists in the current project.

MORPHOLOGY

Cancer type definition.
This table doesn't need any more information compared to the one which already exists in the current project.

MORPHOLOGY SYNONYM

This table gathers all the synonyms for a certain morphology.
It doesn't need any more information compared to the one which already exists in the current project.
