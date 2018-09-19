"""Models form the Genomic app."""
from __future__ import unicode_literals

import os

from clinical.models import Case, Topography

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver

from .validators import validate_file_extension


def _file_upload_path(instance, filename):
    return os.path.join('vcf_files', str(instance.case.project.id), filename)


class File(models.Model):
    """Object to store VCF files."""

    file = models.FileField(unique=True, upload_to=_file_upload_path, validators=[validate_file_extension])
    case = models.ForeignKey(Case, models.CASCADE)
    uploader = models.ForeignKey(User, models.PROTECT)
    lab_info = models.ForeignKey('LabInfo', models.PROTECT)
    format = models.CharField(max_length=17, default='vcf')
    type = models.CharField(max_length=17, default='Somatic variants')  # originally it was an ENUM('Somatic variants', 'Germline variants')
    uploaded_dt = models.DateTimeField(auto_now_add=True)
    size = models.IntegerField()
    topography = models.ForeignKey(Topography, models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        """To define the name of the table."""

        db_table = 'vcf_file'

    def __str__(self):
        """Str function."""
        return str(self.file).replace('vcf_files/' + str(self.case.project.id) + '/', '')

    def can_be_accessed_by(self, user):
        return self.uploader == user\
               or (self.uploader.profile.centre == user.profile.centre
                   and user.groups.filter(name='Centre Admins').exists()) \
               or user.groups.filter(name='Researchers').exists() \
               or user.groups.filter(name='Clinicians').exists()

@receiver(models.signals.post_delete, sender=File)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `File` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

class LabInfo(models.Model):
    """Object to keep track of what kind of processing, dry and wet, has been applied to the sample to produce the VCF files."""

    id = models.AutoField(primary_key=True)
    centre = models.ForeignKey('profile.Centre', models.CASCADE)
    pipeline = models.ForeignKey('Pipeline', models.PROTECT)
    capture_kit_type = models.CharField(max_length=17)  # originally it was ENUM('Exome Seq', 'Panel', 'WGS')
    capture_kit_name = models.CharField(max_length=45)
    ext_name = models.CharField(max_length=128)

    class Meta:
        """To define the name of the table."""

        db_table = 'lab_info'

    def __str__(self):
        """Str function."""
        return str(self.ext_name)  # Could not make a call to the foreign key pipeline (or centre) in django forms [dropdowns].
        # This is a known issue with django-pyodbc-azure==1.11.0.0. Update of azure will also require an update of Django.
        # Hard coded the string ext_name in users-initial-data.json which is run on platform initialization.


class RefGenome(models.Model):
    """Object used to define the reference genome used for the alignment and positions of the genes."""

    name = models.CharField(unique=True, max_length=45)
    info = models.TextField(blank=True, null=True)
    chr01 = models.CharField(max_length=20)
    chr02 = models.CharField(max_length=20)
    chr03 = models.CharField(max_length=20)
    chr04 = models.CharField(max_length=20)
    chr05 = models.CharField(max_length=20)
    chr06 = models.CharField(max_length=20)
    chr07 = models.CharField(max_length=20)
    chr08 = models.CharField(max_length=20)
    chr09 = models.CharField(max_length=20)
    chr10 = models.CharField(max_length=20)
    chr11 = models.CharField(max_length=20)
    chr12 = models.CharField(max_length=20)
    chr13 = models.CharField(max_length=20)
    chr14 = models.CharField(max_length=20)
    chr15 = models.CharField(max_length=20)
    chr16 = models.CharField(max_length=20)
    chr17 = models.CharField(max_length=20)
    chr18 = models.CharField(max_length=20)
    chr19 = models.CharField(max_length=20)
    chr20 = models.CharField(max_length=20)
    chr21 = models.CharField(max_length=20)
    chr22 = models.CharField(max_length=20)
    chrX = models.CharField(max_length=20)
    chrY = models.CharField(max_length=20)
    chrM = models.CharField(max_length=20)

    class Meta:
        """To define the name of the table."""

        db_table = 'ref_genome'

    def __str__(self):
        """Str function."""
        return self.name


class Pipeline(models.Model):
    id = models.AutoField(primary_key=True)
    ref_genome = models.ForeignKey('RefGenome', models.PROTECT)
    name = models.CharField(max_length=45)
    url = models.CharField(max_length=200)

    class Meta:
        db_table = 'pipeline'

    def __str__(self):
        return self.name

CHROMOSOMES = (
    (1, '01'), (2, '02'), (3, '03'), (4, '04'), (5, '05'),
    (6, '06'), (7, '07'), (8, '08'), (9, '09'), (10, '10'),
    (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'),
    (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'),
    (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M'),
)

CHROMOSOME_CODES = []
for listed_chromosome in CHROMOSOMES:
    CHROMOSOME_CODES.append(listed_chromosome[0])


def known_chromosome(chromosome):
    """Validator for chromosomes."""
    if chromosome not in CHROMOSOME_CODES:
        raise ValidationError('The chromosome {} is unknown to the PCM platform.'.format(str(chromosome)))


class Gene(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45, unique=False)
    ref_genome = models.ForeignKey('RefGenome', models.CASCADE, null=False)
    chromosome = models.IntegerField(choices=CHROMOSOMES)
    start_position = models.IntegerField()
    end_position = models.IntegerField()

    class Meta:
        db_table = 'gene'

    def __str__(self):
        return self.name+' ('+self.ref_genome.name+')'

    def save(self, *args, **kwargs):
        """Overriding the save method in order to call clean()  [validation of treatment type]."""
        known_chromosome(self.chromosome)
        # self.clean()
        super(Gene, self).save(*args, **kwargs)


SIGNIFICANCES = ((0, 'Benign'), (1, 'Likely benign'), (2, 'Uncertain significance'), (3, 'Likely pathogenic'), (4, 'Pathogenic'))


class Variant(models.Model):
    file = models.ForeignKey('File', models.CASCADE)
    chromosome = models.IntegerField(choices=CHROMOSOMES)
    position = models.IntegerField()
    ref = models.CharField(max_length=200)
    alt = models.CharField(max_length=200)
    description = models.CharField(max_length=200, null=True)
    effect = models.CharField(max_length=200, null=True)
    genotype = models.CharField(max_length=10)
    depth_ref = models.IntegerField()
    depth_alt = models.IntegerField()
    raw_data = models.TextField()
    dbsnp_id = models.CharField(max_length=20, blank=True, null=True)
    cosmic_id = models.CharField(max_length=20, blank=True, null=True)
    gene = models.ForeignKey('Gene', models.SET_NULL, null=True)
    checked = models.IntegerField(blank=True, null=True)
    significance = models.IntegerField(choices=SIGNIFICANCES, null=True)

    variant_influences = models.ManyToManyField('Transcript')

    class Meta:
        db_table = 'variant'
        unique_together = ('file', 'position', 'ref', 'alt')

    def __str__(self):
        # chromosome_name = 'chr' + self.get_chromosome_display()
        # reference_sequence = getattr(self.file.lab_info.pipeline.ref_genome,chromosome_name)
        # return reference_sequence + ':g.' + str(self.position) + self.ref + '>' + self.alt.replace('[', '').replace(']', '')
        return '[' + self.gene.name + ']' + str(self.position - self.gene.start_position) + self.ref + '>' + self.alt.replace('[', '').replace(']', '')

    def save(self, *args, **kwargs):
        """Overriding the save method in order to call clean()  [validation of treatment type]."""
        known_chromosome(self.chromosome)
        super(Variant, self).save(*args, **kwargs)


    @staticmethod
    def searchVariantsByPosition(ref_genome, chromosome, start_position, end_position):
        return Variant.objects.filter(file__lab_info__pipeline__ref_genome=ref_genome).filter(chromosome=chromosome).filter(position__gte=start_position).filter(position__lte=end_position).order_by('file')

    @staticmethod
    def searchVariantsByGene(gene):
        return Variant.objects.filter(gene=gene).order_by('file')

    @staticmethod
    def getSignificanceKey(significance):
        formatted_significance = significance.lower().replace('_', ' ')
        return next(iter([x[0] for x in SIGNIFICANCES if formatted_significance == x[1].lower()]), None)

    def get_annotations(self):
        return list(VariantAnnotation.objects.filter(variant=self))

class VariantAnnotation(models.Model):
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE)
    transcript = models.IntegerField()
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=200)

    class Meta:
        db_table = 'variantannotation'
        unique_together = 'variant', 'transcript', 'name', 'value'

class Transcript(models.Model):
    class Meta:
        db_table = 'transcript'

    isoform = models.CharField(max_length = 200)
    reference_sequence = models.CharField(max_length = 200)
    producing_gene = models.ForeignKey('Gene', models.CASCADE)

