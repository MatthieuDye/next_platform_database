# next_platform_database

TO ADD YOUR WORK TO THE REPOSITORY, 
Use the git_update script typing

sh git_update.sh 

in your terminal

REMAINING WORK

Should be deleted from the code
- all tables that concern The Cancer Targetome (the github repository is not updated anymore. Drugbank takes its place). In DBeaver, those tables have a "genomic_<class_name> prefix.
- all tables linked to pmkb files. In DBeaver, those tables have a "genomic_pmkb<class_name>" prefix.

In effect some of those tables are redundant (ex: genomic_drug and drug) and own useless attributes (ex: all genomic_drug attributes are based on The Cancer Targetome).

When this step is done, the mapping can be implemented, adding corresponding tables and links into the code.

Finally, database updates will be realized with cronjobs.