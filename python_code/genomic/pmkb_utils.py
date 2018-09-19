import re

import xlrd
from django.db import transaction

from .models import *


def __read_row(sheet, row):
    gene = sheet.cell(row, 0).value
    tumor_types_raw = re.split(r',\s*', sheet.cell(row, 1).value)
    tissue_types_raw = re.split(r',\s*', sheet.cell(row, 2).value)
    variants_raw = re.split(r',\s*', sheet.cell(row, 3).value)
    tier = sheet.cell(row, 4).value
    if tier == '':
        tier = 0
    interp = sheet.cell(row, 5).value
    citations = []
    for column in range(6, sheet.ncols - 1):
        citation = sheet.cell(row, column).value
        if citation == '':
            break
        citations.append(PMKBCitation.objects.create(citation=citation))

    if len(tumor_types_raw) > 10:
        tumor_types_raw = []
    if len (tissue_types_raw) > 10:
        tissue_types_raw = []

    tumor_types = map(lambda raw: PMKBTumorType.objects.get_or_create(tumor_name=raw), tumor_types_raw)
    tissue_types = map(lambda raw: PMKBTissueType.objects.get_or_create(tissue_name=raw), tissue_types_raw)
    variants = map(lambda raw: PMKBVariant.objects.get_or_create(variant_name=raw), variants_raw)

    result = PMKBGeneInfo.objects.create(gene=gene, tier=tier, interpretations=interp)
    for tumor_type in tumor_types:
        result.tumor_types.add(tumor_type[0])

    for tissue_type in tissue_types:
        result.tissue_types.add(tissue_type[0])

    for variant in variants:
        result.variants.add(variant[0])
        
    for citation in citations:
        result.citations.add(citation)
    return result


@transaction.atomic
def get_pmkb_info_from_file(filename):
    workbook = xlrd.open_workbook(filename)
    sheet = workbook.sheet_by_index(0)
    if sheet.ncols < 6:
        raise RuntimeError('Incorrectly formatted file: Need at least 6 columns')
    results = []
    for i in range(1, sheet.nrows):
        if sheet.cell(i, 0).value == '':
            break
        results.append(__read_row(sheet, i))
    return results
