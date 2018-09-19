import csv
import html
import json
import logging
import os
from datetime import datetime
from io import StringIO


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from aauh.get_redcap_data import find_patient_ids_by_cpr, retrieve_redcap_data, retrieve_project
from clinical.models import *
from profile.models import Centre
from .forms import SearchByPositionForm, SearchByGeneForm, VcfForm
from .models import File, Variant, RefGenome, Gene, LabInfo
from .vcf_utils import save_variants


logger = logging.getLogger('django')


class FileUploadApiBase:
    def post(self, request):
        with transaction.atomic():
            try:
                patient = self.__get_or_create_patient(request.POST)
                if isinstance(patient, str):
                    transaction.set_rollback(True)
                    return HttpResponseBadRequest(patient)
                case = self.__get_or_create_case(request.POST, patient)
                if isinstance(case, str):
                    transaction.set_rollback(True)
                    return HttpResponseBadRequest(case)

                uploader = User.objects.get(username='dennis')
                lab_info_id = request.POST['labinfo']
                lab_info = LabInfo.objects.get(pk=lab_info_id)
                format = request.POST['format']
                type = request.POST['type']
                uploaded_dt = datetime.now()

                file = request.FILES['file']
                size = file.size
                name = file.name

                res = File.objects.update_or_create(
                    file=file, case=case, uploader=uploader, lab_info=lab_info,
                    format=format, type=type, uploaded_dt=uploaded_dt, size=size, name=name
                )
                return HttpResponseRedirect(reverse('file', kwargs={'file_id': res[0].pk}))
            except MultiValueDictKeyError as e:
                logger.error(str(e))
                transaction.set_rollback(True)
                return HttpResponseBadRequest("Malformed upload")

    def __get_or_create_patient(self, post):
        if 'patient_id' not in post:
            centre_id = post['centre_id']
            centre = Centre.objects.get(pk=centre_id)
            local_id = post['local_id']
            patient_sex = post['sex']
            res = Patient.objects.create(centre=centre, centre_patient_id=local_id, sex=patient_sex,
                                         birthdate=datetime.strptime(post['birthdate'], '%d%m%y'))
            return res

        patient_id = post['patient_id']
        if Patient.objects.filter(pk=patient_id).exists():
            return Patient.objects.get(pk=patient_id)
        return 'Unknown Patient ID'

    def __get_or_create_case(self, post, patient):
        if 'case_id' not in post:
            project_id = post['project_id']
            project = Project.objects.get(pk=project_id)
            created_time = post['created_time']
            morphology_code = post['morphology_code']
            morphology = Morphology.get_by_icdo3_code(morphology_code)
            topography_code = post['topography_code']
            topography = Topography.get_by_icdo3_code(topography_code)
            diagnosis_code = post['diagnosis_code']
            diagnosis = Diagnosis.get_by_icd10_code(diagnosis_code)
            diagnosis_time = post['diagnosis_date']
            relapse = post['relapse']

            if topography is None:
                return 'Unknown Topography'
            if morphology is None:
                return 'Unknown Morphology'
            if diagnosis is None:
                return 'Unknown Diagnosis'

            res = Case.objects.create(
                project=project, created_dt=created_time,
                patient=patient, morphology=morphology, topography=topography, diagnosis=diagnosis,
                diagnosis_date=diagnosis_time, relapse_number=relapse
            )
            return res

        case_id = post['case_id']
        if Case.objects.filter(pk=case_id).exists():
            return Case.objects.get(pk=case_id)
        return 'Unknown Case ID'


@method_decorator(csrf_exempt, name='dispatch')
class FileView(LoginRequiredMixin, View, FileUploadApiBase):
    def get(self, request, file_id):
        try:
            file = File.objects.get(pk=file_id)
            if not file.can_be_accessed_by(request.user) and settings.ENFORCE_FILE_ACCESS_RESTRICTIONS:
                return render(request, 'genomic/file_no_access.html', {'uploader': file.uploader})
        except KeyError:
            # typically there is no 'id' in the GET parameters
            return HttpResponseRedirect(reverse("files"))
        except ValueError:
            # typically the id passed is not an integer
            return HttpResponseRedirect(reverse("files"))
        except ObjectDoesNotExist:
            # typically there is no file entry with this value
            return HttpResponseRedirect(reverse("files"))

        variants = file.variant_set.all().order_by('chromosome', 'position')
        drugs = {var.gene: find_drugs_targeting_gene(var.gene.name) for var in variants if var.gene}
        pmkbs = {var.gene: list(PMKBGeneInfo.objects.filter(gene__iexact=var.gene.name).all()) for var in variants if var.gene}
        annotations = {(var.chromosome, var.position): [{ann.name: [ann.value, ann.transcript]} for ann in var.get_annotations()] for var in variants}
        download_access = file.can_be_accessed_by(request.user)
        download_url = file.file.url

        return render(
            request,
            'genomic/file.html', 
            {'file': file, 'case': file.case, 'patient': file.case.patient, 'variants': variants, 'drugs': drugs, 'pmkbs': pmkbs,
             'annotations': annotations, 'download_access': download_access, 'download_url': download_url}
        )


@method_decorator(csrf_exempt, name='dispatch')
class FileUploadEndpoint(View, FileUploadApiBase):
    pass  # Use inherited post, nothing else needed for now


class FilesListView(LoginRequiredMixin, View):
    def post(self, request):
        case = get_accessible_case(request, request.POST["case_id"])
        form = VcfForm(request.user, case, request.POST, request.FILES)
        if form.is_valid():
            vcf_file = form.save()
            try:
                save_variants(vcf_file)
            except Exception as e:
                vcf_file.delete()
                # slug = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))
                # print(slug)
                # old_file_name = os.path.join(settings.MEDIA_ROOT, vcf_file.file.__str__())
                # new_file_name = old_file_name + "." + slug + ".to_be_removed"
                # os.rename(old_file_name, new_file_name)
                # os.unlink(new_file_name)
                messages.error(request, 'There was an error during the attempted upload of the file. The file was not uploaded.')
                logger.error(str(e))

                return HttpResponseRedirect(reverse("case", kwargs={'case_id': case.id}))

            return HttpResponseRedirect(reverse("file", kwargs={'file_id': vcf_file.id}))

        return HttpResponseRedirect(reverse("case", kwargs={'case_id': case.id}))


class SearchVariantsView(LoginRequiredMixin, View):
    def get(self, request):
        gene_form = SearchByGeneForm(request.GET)
        position_form = SearchByPositionForm(request.GET)

        variants = {}
        extra_info = None
        known_drugs = None

        if 'gene' in request.GET:
            if gene_form.is_valid() and gene_form.cleaned_data['gene']:
                gene = Gene.objects.filter(name=gene_form.cleaned_data['gene']).first()
                if gene:
                    variants = Variant.searchVariantsByGene(gene)
                    if not variants:
                        messages.info(request, 'No case found')
                else:
                    messages.warning(
                        request,
                        html.escape(gene_form.cleaned_data['gene']) + ' does not seem to be a valid gene name.'
                    )
            extra_info_candidates = PMKBGeneInfo.objects.filter(gene__iexact=request.GET['gene'])

            if len(extra_info_candidates) > 0:
                extra_info = extra_info_candidates[0]

            known_drugs = find_drugs_targeting_gene(request.GET['gene'])
            if len(known_drugs) == 0:
                known_drugs = None

        if 'chromosome' in request.GET:
            if position_form.is_valid():
                if position_form.cleaned_data['chromosome']:
                    ref_genome = RefGenome.objects.first()
                    # Quick fix of the case where the user submits position_form with no start or end position.
                    if position_form.cleaned_data['start_position'] is None:
                        position_form.cleaned_data['start_position'] = 1
                    if position_form.cleaned_data['end_position'] is None:
                        position_form.cleaned_data['end_position'] = 100000000
                    variants = Variant.searchVariantsByPosition(
                        ref_genome,
                        position_form.cleaned_data['chromosome'],
                        position_form.cleaned_data['start_position'],
                        position_form.cleaned_data['end_position']
                    )
                    if not variants:
                        messages.info(
                            request,
                            'No case found on chromosome ' + position_form.cleaned_data['chromosome'] + ' between base pairs ' +
                            str(position_form.cleaned_data['start_position']) + ' and ' + str(position_form.cleaned_data['end_position']) +
                            ' for ref genome ' + ref_genome.name
                        )

        return render(
            request, 'genomic/search.html',
            {'gene_form': gene_form, 'position_form': position_form, 'variants': variants, 'extra_info': extra_info, 'known_drugs': known_drugs}
        )


class DrugView(LoginRequiredMixin, View):
    def get(self, request, drug_id):
        drug = Drug.objects.get(pk=drug_id)
        synonyms = list(DrugSynonym.objects.filter(drug__exact=drug).all())
        interactions = list(Interaction.objects.filter(int_drug__exact=drug).all())
        return render(request, 'genomic/drug.html', {'drug': drug, 'synonyms': synonyms, 'interactions': interactions})


#CV# same function in clinical/views.py, should be refactored
def get_accessible_case(request, case_id):
    case = Case.objects.get(pk=case_id)
    if case.patient.centre.id != request.user.profile.centre.id:
        raise PermissionDenied('The user does not have access to this case')
    return case


class GeneInfoView(LoginRequiredMixin, View):
    def get(self, request, gene_id):
        return render(request, 'genomic/gene_info.html', {'info': PMKBGeneInfo.objects.get(pk=gene_id)})


class ExtraInfoEndpoint(LoginRequiredMixin, View):
    def get(self, request, gene_name):
        # We can not use get since we might get two genes with the same name if it is on both ChrX and ChrY
        gene = Gene.objects.filter(name__exact=gene_name).first()
        pmkbs = PMKBGeneInfo.objects.filter(gene__exact=gene_name).all()
        pmkb = pmkbs[0] if len(pmkbs) > 0 else None
        interactions = find_drugs_targeting_gene(gene_name)

        response = {}
        if pmkb:
            response['pmkb_data'] = self._serialize_pmkb(pmkb)
        if len(interactions) > 0:
            response['drug_data'] = [self._serialize_interaction(interaction) for interaction in interactions]
        return JsonResponse(response)

    def _serialize_interaction(self, interaction):
        return {'id': interaction.int_drug.drug_id,
                'name': interaction.int_drug.drug_name,
                'type': interaction.interaction_type,
                'sources': [source.source_literature for source in interaction.sources.all()]}

    def _serialize_pmkb(self, pmkb):
        return {'id': pmkb.id,
                'gene': pmkb.gene,
                'tier': pmkb.tier,
                'tumor_types': [tt.tumor_name for tt in list(pmkb.tumor_types.all())],
                'tissue_types': [tt.tissue_name for tt in list(pmkb.tissue_types.all())],
                'variants': [v.variant_name for v in list(pmkb.variants.all())],
                'interpretations': pmkb.interpretations,
                'citations': [c.citation for c in list(pmkb.citations.all())]}


def parse_batch_upload_metadata(uploaded_file):
    reader = csv.DictReader(StringIO(uploaded_file.read().decode('utf-8')), ('File', 'Patient', 'Case'), delimiter=',')
    result = []
    for row in reader:
        result.append(row)
    return result


@method_decorator(csrf_exempt, name='dispatch')
class BatchUploadView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'genomic/batch_upload.html')


@method_decorator(csrf_exempt, name='dispatch')
class BatchUploadApiEndpoint(View):
    def post(self, request):
        import pandas

        (clin_df, incl_df, lab_df) = retrieve_redcap_data(events_for_clin='case_arm_1, case_arm_2, case_arm_3')
        error_records = pandas.DataFrame(columns=['text', 'severity', 'type', 'area'])
        cpr_to_patient_id_dict = find_patient_ids_by_cpr(error_records, incl_df, clin_df)
        valid_patient_ids = Patient.objects.values_list('id', flat=True)

        with transaction.atomic():
            report = []
            try:
                # Get the upload data from the request
                data_json = request.POST['data']
                data_list = json.loads(data_json)

                uploaded_file_names = [file.name for file in request.FILES.values()]
                metadata_file_names = [data[2] for data in data_list]
                files_to_indices = json.loads(request.POST['files-to-indices'])

                dirty_files = []

                # Verify that there is a 1-to-1 correspondence between metadata entries and files
                for file_data in data_list:
                    file_name = file_data[2]
                    if file_name not in uploaded_file_names:
                        report.append(
                            (-1, "The file {}, which was specified in the metadata for patient {}, was not uploaded."
                             .format(file_name, file_data[0])))
                        dirty_files.append(file_name)

                for key, file in request.FILES.items():
                    if file.name not in metadata_file_names and key != 'metadata':
                        report.append((files_to_indices[file.name],
                                       "The file {} was uploaded, but not mentioned in the metadata.".format(
                                           file.name)))
                        dirty_files.append(file.name)

                for file_data in data_list:
                    file_name = file_data[2].lstrip().rstrip()
                    cpr_or_id = file_data[0].lstrip().rstrip()

                    if file_name in dirty_files:
                        continue

                    if not BatchUploadApiEndpoint._correct_cpr_format(cpr_or_id)\
                            and cpr_or_id not in valid_patient_ids:
                        report.append((files_to_indices[file_name],
                                       "Incorrect cpr format / Unknown patient ID: " + cpr_or_id + ". The file "
                                       + file_name + " was not uploaded to the PCM DB."))
                        continue
                    if cpr_or_id not in cpr_to_patient_id_dict and cpr_or_id not in valid_patient_ids:
                        report.append((files_to_indices[file_name],
                                       "There is no patient with this CPR number or patient ID: " + cpr_or_id + ". The file "
                                       + file_name + " was not uploaded to the PCM DB."))
                        continue
                    try:
                        date_str = file_data[1].lstrip().rstrip()
                        diag_datetime_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError as error:
                        report.append(
                            (
                                files_to_indices[file_name],
                                "Issue with the diagnosis date " + file_data[
                                    1] + " for cpr/id " + cpr_or_id + ". File " + file_name + " not uploaded."
                                                                                     " Error msg: " + str(error)
                            ))
                        continue
                    # INFO / WARNING : Hard coding the centre to 'AAUH'
                    # TO-DO: Make a solution which does not crash if the centre name of Aaalborg is changed.
                    patient_id = cpr_to_patient_id_dict.get(cpr_or_id, cpr_or_id)  # If it isn't in the dict at this
                                                                                   # point, it must be a valjd patient id
                    patients = Patient.objects.filter(centre_patient_id=patient_id, centre__name='AAUH')
                    if len(patients) == 0:
                        # Could not find the patient
                        report.append(
                            (
                                files_to_indices[file_name],
                                "The PCM DB contains no AAUH-patient with the cpr/id " + cpr_or_id + ". Please check that the cpr/id is correct, that the patient"
                                                                                            " is registered in Redcaps Clinical DB under that cpr, and that the PCM DB has been synchronized with Redcap. "
                                                                                            "The file " + file_name + " was not uploaded to the PCM DB."
                            ))
                        continue
                    if len(patients) > 1:
                        # The centre contains more than one patient witht that cpr. This should never happen.
                        report.append(
                            (
                                files_to_indices[file_name],
                                "Found more than one AAUH patient object in the PDM DB with the cpr/id " + cpr_or_id + ". The "
                                                                                                              "file " + file_name + " was not uploaded to the PCM DB."
                            ))
                        continue
                    patient = patients.first()
                    # INFO / WARNING : Hard coding the project to 'AAUH Project'
                    # TO-DO: Make a solution which does not crash if the project is changed.

                    cases = Case.objects.filter(patient=patient, diagnosis_date=diag_datetime_obj,
                                                project__name='AAUH Project')
                    if len(cases) == 0:
                        # Could not find the case
                        report.append(
                            (
                                files_to_indices[file_name],
                                "Could not find the case for the cpr/id " + cpr_or_id + " and diagnosis date " + date_str + "."
                                                                                                                   "The file " + file_name + " was not uploaded to the PCM DB."
                            ))
                        continue
                    if len(cases) > 1:
                        # Found more than one case
                        report.append(
                            (
                                files_to_indices[file_name],
                                "Found more than one AAUH case for the cpr/id " + cpr_or_id + " and diagnosis date " + date_str + "."
                                                                                                                         "The file " + file_name + " was not uploaded to the PCM DB."
                            ))
                        continue
                    case = cases.first()


                    # uploader = User.objects.get(username='charles')
                    uploader = User.objects.get(username=request.user)                    
                    ################## lab_info_id = request.POST['labinfo']
                    lab_info_id = 1
                    lab_info = LabInfo.objects.get(pk=lab_info_id)
                    file_format = "vcf"
                    file_type = "wes"
                    uploaded_dt = timezone.now()

                    if file_name in request.FILES:
                        file = request.FILES[file_name]
                    else:
                        for name, f in request.FILES.items():
                            if f.name == file_name:
                                file = f
                    if file is None:
                        report.append((files_to_indices[file_name],
                                       "The file {} was not uploaded (correctly). Please check the file name.".format(file_name)))
                        continue
                    size = file.size
                    name = file.name
                    try:
                        file_objs = File.objects.filter(case=case, name=name)

                        if len(file_objs) > 1:
                            raise ValueError("Multiple files with same case and file name!")

                        if len(file_objs) == 1:
                            old_obj = file_objs.first()
                            old_file_path = os.path.join(settings.MEDIA_ROOT, old_obj.file.__str__())
                            os.remove(old_file_path)
                            Variant.objects.filter(file=old_obj).delete()
                            old_obj.delete()

                        obj = File.objects.create(
                            case=case,
                            name=name,
                            file=file,
                            uploader=uploader,
                            lab_info=lab_info,
                            format=file_format,
                            type=file_type,
                            uploaded_dt=uploaded_dt,
                            size=size)

                        save_variants(obj)

                    except IntegrityError as error:
                        report.append(
                            (
                                files_to_indices[file_name],
                                "INTEGRITY ERROR! The PCM DB was unable to import the file " + file_name + " for the AAUH case with cpr/id " + cpr_or_id +
                                " and diagnosis date " + date_str + "."
                            ))
                        continue

                return JsonResponse(report, safe=False)

            except (MultiValueDictKeyError, LookupError, KeyError) as e:
                print(e)
                transaction.set_rollback(True)
                raise e
                #return HttpResponseBadRequest("Malformed upload")

    # Copied from the aauh module
    @staticmethod
    def _correct_cpr_format(cpr):
        import pandas
        """Check the format of the cpr string."""
        if pandas.isnull(cpr):
            return False
        if len(cpr) > 11:
            # print("Cpr consists of too many characters. Cpr : " + cpr)
            return False
        if len(cpr) < 11:
            # print("Cpr consists of too few characters. Cpr : " + cpr)
            return False
        cpr_split_position = cpr.find("-")
        if cpr_split_position != 6:
            # print("Cpr with hyphen missing or in wrong position. Cpr : " + cpr)
            return False
        # Now we know that the cpr string contains at least one hyphen
        cpr_split = cpr.split("-")
        if len(cpr_split) > 2:
            # print("Cpr with too many hyphens. Cpr : " + cpr)
            return False
        first_part_of_cpr = cpr_split[0]
        second_part_of_cpr = cpr_split[1]
        if not first_part_of_cpr.isdigit():
            # print("First part of cpr does not consist of only digits. Cpr : " + cpr)
            return False
        if not second_part_of_cpr.isdigit():
            # print("Second part of cpr does not consist of only digits. Cpr : " + cpr)
            return False
        return True

