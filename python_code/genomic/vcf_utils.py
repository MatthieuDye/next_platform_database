import logging
import os
import re

import vcf
from django.conf import settings

from .models import Variant, Gene, VariantAnnotation


class ChromosomeFormat:

    def __init__(self, fmt, translator):
        self.fmt = fmt
        self.translator = translator

    def translate_if_matches(self, chrom):
        if re.match(self.fmt, chrom):
            return True, self.translator(chrom)
        return False, None


chromosome_formats = [
    ChromosomeFormat('[0-9][0-9]?', lambda chrom: int(chrom)),
    # ChromosomeFormat('.*?[XY]', lambda chrom: 23 if chrom[-1] == 'X' else 24),
    ChromosomeFormat('X', lambda chrom: 23),
    ChromosomeFormat('Y', lambda chrom: 24),
    ChromosomeFormat('M', lambda chrom: 25),
    ChromosomeFormat('chrX', lambda chrom: 23),
    ChromosomeFormat('chrY', lambda chrom: 24),
    ChromosomeFormat('chrM', lambda chrom: 25),
    ChromosomeFormat('chr[0-9][0-9]?', lambda chrom: int(chrom[3:])),
]

logger = logging.getLogger('django')


def save_variants(vcf_file):
    opened_file = open(os.path.join(settings.MEDIA_ROOT, vcf_file.file.__str__()), 'r')
    vcf_reader = vcf.Reader(opened_file)
    count = 0
    variants = {}
    for record in vcf_reader:
        count += 1
        record_info = record.samples[0]
        chromosome = record.CHROM
        # Padding chromosome number with a 0 if needed so they can be properly ordered
        for chromosome_format in chromosome_formats:
            match, number = chromosome_format.translate_if_matches(chromosome)
            if match:
                chromosome = number
                break
        else:
            raise ValueError('Unknown chromosome format: {}'.format(chromosome))

        gene = Gene.objects.filter(chromosome=chromosome).filter(start_position__lte=record.POS).filter(end_position__gte=record.POS).first()
        variant = Variant(
            file=vcf_file,
            gene=gene,
            chromosome=chromosome,
            position=record.POS,
            # dbsnp_id=record.ID,
            ref=record.REF,
            alt=record.ALT,
            genotype=record_info['GT'],
            depth_ref=record_info['AD'][0],
            depth_alt=record_info['AD'][1],
            raw_data=str(record_info)
        )

        if record.ID and record.ID.startswith('rs'):
            variant.dbsnp_id = record.ID

        if (chromosome, record.POS) not in variants:
            variants[(chromosome, record.POS)] = []

        variants[(chromosome, record.POS)].append((variant, record.INFO))

    annotations = []

    for key, vars in variants.items():
        variant = vars[0][0]
        variant.save()
        transcript = 0
        for _, info in vars:
            for name, values in info.items():
                if isinstance(values, (list, tuple)):
                    for value in values:
                        annotations = get_annotations_from_value(variant, transcript, name, value, annotations)
                elif values:
                    annotations = get_annotations_from_value(variant, transcript, name, values, annotations)

            transcript += 1

    return count


def get_annotations_from_value(variant, transcript, name, value, annotations):
    if (variant.id, name, value) not in annotations:
        if name in ('DBSNP') and not variant.dbsnp_id:
            variant.dbsnp_id = 'rs' + str(value)
            variant.save()
        elif name in ('CLI_ASSESSMENT') and not variant.checked:
            variant.significance = Variant.getSignificanceKey(value)
            variant.checked = True
            variant.save()
        elif name in ('ING_CLASSIFICATION') and not variant.significance:
            variant.significance = Variant.getSignificanceKey(value)
            variant.save()

        annotation = VariantAnnotation(variant=variant, transcript=transcript, name=name, value=value)
        annotation.save()
        annotations.append((variant.id, name, value))

    return annotations
