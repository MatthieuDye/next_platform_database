"""Models for the clinical app."""
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    """Model for project."""

    id = models.AutoField(primary_key=True)
    centre = models.ForeignKey('profile.Centre', on_delete=models.PROTECT, db_column='centre_fk_id')
    name = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        """Create database table."""

        db_table = 'project'

    def __str__(self):
        """Define str on self."""
        return self.name


SEXES = (
    (1, 'Male'),
    (0, 'Female'),
)


class Patient(models.Model):
    """Model for patients."""

    id = models.AutoField(primary_key=True)
    centre = models.ForeignKey('profile.Centre', on_delete=models.PROTECT, db_column='centre_fk_id')
    sex = models.IntegerField(choices=SEXES)
    # 36 characters to support UUID, see https://en.wikipedia.org/wiki/Universally_unique_identifier
    # AAUH - This is the first record_id on the Redcap "Relaps - Inclusions" project for this patient
    centre_patient_id = models.CharField(max_length=36, verbose_name='Patient ID')
    birthdate = models.DateField()

    class Meta:
        """Create database table."""

        db_table = 'patient'
        unique_together = ('centre', 'centre_patient_id')

    def __str__(self):
        """Define str on self."""
        return 'Patient from {} centre with ID {}'.format(self.centre, self.centre_patient_id)


STATUS_CHOICES = (
    ('treatment', 'In treatment'),
    ('normal_follow_up', 'Normal follow-up'),
    ('lost_to_follow_up', 'Lost to follow-up'),
    ('relapse', 'Relapse'),
    ('dead', 'Dead')
)


class Case(models.Model):
    """Model for patient specific case."""

    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, db_column='patient_fk_id')
    project = models.ForeignKey('Project', on_delete=models.PROTECT, db_column='project_fk_id')
    created_dt = models.DateTimeField(auto_now_add=True)
    morphology = models.ForeignKey('Morphology', on_delete=models.SET_NULL, blank=True, null=True, db_column='morphology_fk_id')
    diagnosis_date = models.DateField(blank=True, null=True)
    topography = models.ForeignKey('Topography', on_delete=models.SET_NULL, blank=True, null=True, db_column='topography_fk_id')
    relapse_number = models.IntegerField(blank=True, null=True)
    project_case_id = models.CharField(max_length=36)  # AAUH - This is the record_id on the Redcap "Relaps - Clinical Data" project
    diagnosis = models.ForeignKey('Diagnosis', on_delete=models.SET_NULL, blank=True, null=True, db_column='diagnosis_fk_id')
    status = models.CharField(blank=True, null=True, max_length=64, choices=STATUS_CHOICES)
    status_date = models.DateField(blank=True, null=True)
    regimen = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        """Create database table."""

        db_table = 'patient_case'
        unique_together = ('project', 'project_case_id')

    def __str__(self):
        """Define str on self."""
        # FIXME/TO-DO:
        # return 'Case from {} project with ID {}'.format(self.project, self.project_case_id)
        # We could like to return a string as indicated above, but it is not possible right now.
        # https://github.com/michiya/django-pyodbc-azure/issues/116
        # It seems the solution might be to update django and django-pyodbc-azure.
        # See issue #90 on Github
        return 'Project case ID {}'.format(self.project_case_id)


class Permission(models.Model):
    granted = models.ForeignKey(User, models.CASCADE, related_name='granted_user')
    granter = models.ForeignKey(User, models.CASCADE)
    case = models.ForeignKey('Case', models.CASCADE)
    created_dt = models.DateTimeField()
    end_dt = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'permission'
        unique_together = ('granted', 'granter', 'case',)

    def __str__(self):
        return 'Permission on case ' + str(
            self.case.id) + ' from ' + self.granter.username + ' to ' + self.granted.username


class Morphology(models.Model):
    """Morphology model, just a reference, look at MorphologySynonym for codes and descriptions."""

    class Meta:
        """Table name in DB."""

        db_table = 'morphology'

    def __str__(self):
        """Str function used when printing the object."""
        synonyms = MorphologySynonym.objects.filter(morphology=self)
        icdo3_name_synonym = synonyms.filter(type__exact='icdo_name').first()
        icdo3_code_synonym = synonyms.filter(type__exact='icdo_code').first()
        pato_name_synonym = synonyms.filter(type__exact='pato_name').first()
        pato_code_synonym = synonyms.filter(type__exact='pato_code').first()

        if icdo3_name_synonym is not None and icdo3_code_synonym is not None:
            return icdo3_code_synonym.description + ' - ' + icdo3_name_synonym.description

        elif pato_name_synonym is not None and pato_code_synonym is not None:
            return pato_code_synonym.description + ' - ' + pato_name_synonym.description

        elif icdo3_name_synonym is not None:
            return icdo3_name_synonym.description

        elif pato_name_synonym is not None:
            return pato_name_synonym.description

        elif icdo3_code_synonym is not None:
            return icdo3_code_synonym.description

        elif pato_code_synonym is not None:
            return pato_code_synonym.description

        else:
            return 'Undefined'

    @staticmethod
    def get_by_icdo3_code(icdo3_code):
        synonyms = MorphologySynonym.objects.filter(type__exact='icdo_code', description__iexact=icdo3_code)
        if synonyms.exists():
            return synonyms.get().morphology
        return None


class MorphologySynonym(models.Model):
    """MorphologySynonym model, to store info (code, name) for the morphology."""

    morphology = models.ForeignKey(Morphology, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    type = models.CharField(max_length=20)

    class Meta:
        """Table name in DB."""

        db_table = 'morphology_synonym'


class Topography(models.Model):
    """Topography model, i.e. the location of the sample/tumour."""

    class Meta:
        """Table name in DB."""

        db_table = 'topography'

    def __str__(self):
        """Str function used when printing the object."""
        synonyms = TopographySynonym.objects.filter(topography=self)
        icdo3_name_synonym = synonyms.filter(type__exact='icdo_name').first()
        icdo3_code_synonym = synonyms.filter(type__exact='icdo_code').first()
        pato_name_synonym = synonyms.filter(type__exact='pato_name').first()
        pato_code_synonym = synonyms.filter(type__exact='pato_code').first()

        if icdo3_name_synonym is not None and icdo3_code_synonym is not None \
                and pato_name_synonym is not None and pato_code_synonym is not None:
            return '{} - {} ({} - {})'.format(icdo3_code_synonym.description, icdo3_name_synonym.description,
                                              pato_code_synonym.description, pato_name_synonym.description)

        elif icdo3_name_synonym is not None and icdo3_code_synonym is not None:
            return icdo3_code_synonym.description + ' - ' + icdo3_name_synonym.description

        elif pato_name_synonym is not None and pato_code_synonym is not None:
            return pato_code_synonym.description + ' - ' + pato_name_synonym.description

        elif icdo3_name_synonym is not None:
            return icdo3_name_synonym.description

        elif pato_name_synonym is not None:
            return pato_name_synonym.description

        elif icdo3_code_synonym is not None:
            return icdo3_code_synonym.description

        elif pato_code_synonym is not None:
            return pato_code_synonym.description

        else:
            return 'Undefined'

    @staticmethod
    def get_by_icdo3_code(icdo3_code):
        refs = TopographySynonym.objects.filter(type__exact='icdo_code', description__iexact=icdo3_code)
        if refs.exists():
            return refs.get().topography
        return None


class TopographySynonym(models.Model):
    """TopographySynonym model, to store info (code, name) for the topography."""

    topography = models.ForeignKey(Topography, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    type = models.CharField(max_length=20)

    class Meta:
        """Name of table in DB."""

        db_table = 'topography_synonym'


class Diagnosis(models.Model):
    """Diagnosis model, just a reference, look at DiagnosisSynonym for codes and descriptions."""

    parent = models.ForeignKey('Diagnosis', null=True, on_delete=models.CASCADE)

    def __str__(self):
        """Str function used when printing the object."""
        synonyms = DiagnosisSynonym.objects.filter(diagnosis=self).all()

        name_synonym = synonyms.filter(type__exact='icd10_name').first()
        if name_synonym is None:
            name_synonym = synonyms.filter(type__exact='sks_name').first()

        code_synonym = synonyms.filter(type__exact='icd10_code').first()
        if code_synonym is None:
            code_synonym = synonyms.filter(type__exact='sks_code').first()

        if name_synonym is None and code_synonym is None:
            return 'Undefined'
        elif name_synonym is None:
            return code_synonym.description
        elif code_synonym is None:
            return name_synonym.description
        else:
            return code_synonym.description + ' - ' + name_synonym.description

    class Meta:
        """Name of table in DB."""

        db_table = 'diagnosis'

    @staticmethod
    def get_by_icd10_code(code):
        diag = DiagnosisSynonym.objects.filter(type__exact='icd10_code', description__iexact=code)
        if diag.exists():
            return diag.get().diagnosis
        return None


class DiagnosisSynonym(models.Model):
    """TopographySynonym model, to store info (code, name) for the diagnosis."""

    diagnosis = models.ForeignKey('Diagnosis', on_delete=models.CASCADE)
    description = models.CharField(max_length=300)
    type = models.CharField(max_length=30)

    class Meta:
        """Name of table in DB."""

        db_table = 'diagnosis_synonym'


TREAT_TYPES = (
    ('cycl', 'Cycle drug'),
    ('cont', 'Continuous drug'),
    ('cond', 'Conditioning drug'),
    ('allo', 'Allotransplantation'),
    ('auto', 'Autotransplantation'),
    ('waw', 'Watch and wait'),
    ('rad', 'Radiation treatment'),
    ('exptr', 'Experimental treatment'),
    ('surg', 'Surgery'))


TREAT_TYPE_CODE = []
for listed_treat_type in TREAT_TYPES:
    TREAT_TYPE_CODE.append(listed_treat_type[0])


def known_treatment(treat_type):
    """Validator for treatment types."""
    if treat_type not in TREAT_TYPE_CODE:
        raise ValidationError('{} is not a valid treatment type.'.format(treat_type))


class Treatment(models.Model):
    """Model for case specific treatment."""

    id = models.AutoField(primary_key=True)
    case = models.ForeignKey('Case', blank=False, null=False, on_delete=models.CASCADE, db_column='case_fk_id')
    treat_instance = models.PositiveIntegerField(blank=False, null=False)
    treat_type = models.CharField(blank=False, null=False, choices=TREAT_TYPES, max_length=64)
    drug = models.ForeignKey('Drug', on_delete=models.SET_NULL, blank=True, null=True, db_column='drug_fk_id')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)  # mg for drugs and gray for radiation

    class Meta:
        """Create database table."""

        db_table = 'treatment_element'

    def __str__(self):
        """Define str on self."""
        return 'Treament element ID {}'.format(self.id)

    def save(self, *args, **kwargs):
        """Overriding the save method in order to call known_treatment [validation of treatment type]."""
        known_treatment(self.treat_type)
        super(Treatment, self).save(*args, **kwargs)


class Drug(models.Model):
    """Drug model, just a reference, look at DrugSynonym for codes and descriptions."""

    class Meta:
        """Table name in DB."""

        db_table = 'drug'

    def __str__(self):
        """Str function used when printing the object."""
        synonyms = DrugSynonym.objects.filter(drug=self)
        code_synonym = synonyms.filter(type__exact='code').first()
        name_synonym = synonyms.filter(type__exact='official_name').first()

        if name_synonym is None and code_synonym is None:
            return 'Undefined'
        elif name_synonym is None:
            return code_synonym.description
        elif code_synonym is None:
            return name_synonym.description
        else:
            return code_synonym.description + ' - ' + name_synonym.description

    def code_str(self):
        """Str function used when printing the object."""
        synonyms = DrugSynonym.objects.filter(drug=self)
        code_synonym = synonyms.filter(type__exact='code').first()

        if code_synonym is None:
            return 'Undefined'
        else:
            return code_synonym.description

    def off_name_str(self):
        """Str function used when printing the object."""
        synonyms = DrugSynonym.objects.filter(drug=self)
        name_synonym = synonyms.filter(type__exact='official_name').first()

        if name_synonym is None:
            return 'Undefined'
        else:
            return name_synonym.description


class DrugSynonym(models.Model):
    """DrugSynonym model, to store info (code, name) for the drug."""

    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    type = models.CharField(max_length=20)

    class Meta:
        """Table name in DB."""

        db_table = 'drug_synonym'

LEVEL = (
    (1, 'Level 1'), (2, 'Level 2A'), (3, 'Level 2B'), (4, 'Level 3A'), (5, 'Level 3B'),
    (6, 'Level 4'), (7, 'Level R1'),
)

TIER = (
    (1, 'Tier  1'), (2, 'Tier 2'), (3, 'Tier 3'),
)


class DrugEffect(models.Model):

    class Meta:
        db_table = 'drug_effect'

    description = models.CharField(max_length=300)
    level = models.IntegerField(blank = True, null = True, choices=LEVEL)
    tier = models.IntegerField(blank = True, null = True, choices=TIER)
    actionable = models.BooleanField(default=False)

    tissue_type = models.ForeignKey(Topography, on_delete=models.CASCADE)
    cancer_type = models.ForeignKey(Morphology, on_delete=models.CASCADE)
    variant  = models.ForeignKey('genomic.Variant', on_delete=models.CASCADE)

    advices = models.ManyToManyField('Drug')


class Reference(models.Model):

    class Meta:
        db_table = 'reference'

    type = models.CharField(max_length=300)
    description = models.CharField(max_length=300)

    reference_gives_details = models.ManyToManyField('DrugEffect')