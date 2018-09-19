"""Views for the clinical part."""
# import time

from datetime import datetime

from aauh.redcap_utils import get_redcap_dictionary, get_redcap_records, labelize_redcap_data

from dal import autocomplete

from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from genomic.forms import VcfForm
from genomic.models import File, LabInfo, Variant

import pandas

from .forms import CaseForm, PatientForm, TreatmentForm

from .models import (
    Case,
    Diagnosis,
    DiagnosisSynonym,
    Drug,
    DrugSynonym,
    Morphology,
    MorphologySynonym,
    Patient,
    Project,
    Topography,
    TopographySynonym,
    Treatment
)


class PatientsListView(LoginRequiredMixin, View):
    """List all the patients of the centre of the user."""

    def get(self, request):
        """To list available patients."""
        return self.__render_patients_list(request)

    def post(self, request):
        """To create a new patient."""
        form = PatientForm(request.user.profile.centre, request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            return HttpResponseRedirect(reverse("patient", kwargs={'patient_id': patient.id}))
        return self.__render_patients_list(request, form)

    def __render_patients_list(self, request, form=None):
        patients = Patient.objects.filter(centre=request.user.profile.centre).order_by('-id')
        patients_list = list()
        for patient in patients:
            age = relativedelta(datetime.now(), patient.birthdate).years

            primary_case = patient.case_set.order_by('diagnosis_date').first()

            if primary_case:
                diagnosis = primary_case.diagnosis
                relapses = patient.case_set.all().count() - 1
            else:
                diagnosis = None
                relapses = None

            patients_list.append(
                {
                    'id': patient.id,
                    'centre_patient_id': patient.centre_patient_id,
                    'sex': patient.get_sex_display(),
                    'diagnosis': diagnosis,
                    'relapses': relapses,
                    'age': age
                }
            )

        if form is None:
            form = PatientForm(request.user.profile.centre)

        return render(
            request,
            'clinical/patients_list.html',
            {'patients': patients_list, 'form': form}
        )


class PatientView(LoginRequiredMixin, View):
    """To see the patient and its associated cases."""

    def get(self, request, patient_id):
        """To see the patients."""
        patient = get_accessible_patient(request, patient_id)

        primary_case = patient.case_set.order_by('diagnosis_date').first()
        if primary_case:
            patient.age = relativedelta(primary_case.diagnosis_date, patient.birthdate).years
        else:
            patient.age = ""

        cases = Case.objects.filter(patient=patient).order_by('-id')
        form = CaseForm(patient)

        return render(
            request,
            'clinical/patient.html',
            {'patient': patient, 'cases': cases, 'form': form}
        )

    def post(self, request, patient_id):
        """To update the patient (front-end not implemented yet...)."""
        patient = get_accessible_patient(request, patient_id)
        form = PatientForm(patient.centre, request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("patient", kwargs={'patient_id': patient.id}))
        else:
            messages.warning(request, form.errors)

        return HttpResponseRedirect(reverse("patients_list"))


class CasesListView(LoginRequiredMixin, View):
    """To see all the cases of the centre of the user."""

    def get(self, request):
        cases = Case.objects.filter(patient__centre__id=request.user.profile.centre.id).order_by('-id')

        return render(request, 'clinical/cases_list.html', {'cases': cases})

    # To create a new case for patient with id patient_id
    def post(self, request):
        patient = get_accessible_patient(request, request.POST["patient_id"])

        form = CaseForm(patient, request.POST)
        if form.is_valid():
            case = form.save()
            return HttpResponseRedirect(reverse("case", kwargs={'case_id': case.id}))
        else:
            messages.warning(request, form.errors)

        return HttpResponseRedirect(reverse("patient", kwargs={'patient_id': patient.id}))


class CaseView(LoginRequiredMixin, View):
    """To see the case with id case_id and the files associated (see in genomic app for the rest)."""

    def get(self, request, case_id):
        case = get_accessible_case(request, case_id)
        files = File.objects.filter(case=case.id).order_by('-id')

        drug_and_treatment_str = get_case_treatment_str(case)

        form_vcf = VcfForm(
            request.user, case, initial={'lab_info': LabInfo.objects.filter(centre=request.user.profile.centre).first()}
        )

        form_vcf.fields["lab_info"].queryset = LabInfo.objects.filter(centre=request.user.profile.centre)

        patient = case.patient

        patient.age = relativedelta(case.diagnosis_date, patient.birthdate).years

        if (pandas.isnull(case.status)):
            case.status = "-"

        form_treat_elem = TreatmentForm(case)

        return render(
            request,
            'clinical/case.html',
            {
                'case': case,
                'patient': patient,
                'files': files,
                'form_vcf': form_vcf,
                'form_treat_elem': form_treat_elem,
                'treatments': drug_and_treatment_str
            }
        )

    # To update the case (front-end not implemented yet...)
    def post(self, request, case_id):
        case = get_accessible_case(request, case_id)
        form = CaseForm(case.patient, request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("case", kwargs={'case_id': case.id}))

        return HttpResponseRedirect(reverse("patient", kwargs={'patient_id': case.patient.id}))


class ReportView(LoginRequiredMixin, View):
    """To see the case with id case_id and the files associated (see in genomic app for the rest)."""

    def get(self, request, patient_id):
        """To see the patient report."""
        # prev_time = time.time()
        patient = get_accessible_patient(request, patient_id)

        patient.age = None
        # print('patient_retrieved: ' + str(time.time() - prev_time)); prev_time = time.time()

        cases = Case.objects.filter(patient=patient).order_by('relapse_number')
        # print('cases_retrieved: ' + str(time.time() - prev_time)); prev_time = time.time()

        cases_with_treatment = []
        first_case = None
        current_case = None
        for case in cases:
            if not first_case:
                first_case = case
                patient.age = relativedelta(first_case.diagnosis_date, patient.birthdate).years

            case.treatment_str = get_case_treatment_str(case)
            case.variants = Variant.objects.filter(file__case=case, significance__gte=3)  # 3 should be likely_pathogenic
            cases_with_treatment.append(case)
            current_case = case

        # print('current_case_retrieved: ' + str(time.time() - prev_time)); prev_time = time.time()

        clinical_df = []
        medications_df = []
        blood_tests_df = []
        side_effects_df = []

        if request.user.profile.centre.id == 1:  # so AAUH user
            clinical_df = get_redcap_records(
                settings.API_CLINICAL_TOKEN, None, None, [''], [None], [current_case.project_case_id]
            )
            # print('redcap_clinical_data_retrieved: ' + str(time.time() - prev_time)); prev_time = time.time()

            clinical_df = clinical_df.loc[clinical_df['redcap_event_name'] == 'case_arm_1']

            clinical_dictionary_df = get_redcap_dictionary(settings.API_CLINICAL_TOKEN)

            # print('redcap_clinical_dict_retrieved: ' + str(time.time() - prev_time)); prev_time = time.time()

            # removing the "FOO_complete" columns that do contain any meaningfull info
            # and it's not even in the dictionary
            data_col = [col for col in clinical_df if not col.endswith('_complete')]
            clinical_df = labelize_redcap_data(clinical_df[data_col], clinical_dictionary_df)
            medications_df = clinical_df.loc[clinical_df.redcap_repeat_instrument == 'medication'].dropna(axis=1, how='all')
            side_effects_df = clinical_df.loc[clinical_df['redcap_repeat_instrument'] == 'side_effect'].dropna(axis=1, how='all')
            blood_tests_df = clinical_df.loc[clinical_df['redcap_repeat_instrument'] == 'blood_test'].dropna(axis=1, how='all')
            clinical_df = clinical_df.loc[pandas.isnull(clinical_df['redcap_repeat_instrument'])].dropna(axis=1, how='all')

            # print('data_labelized: ' + str(time.time() - prev_time)); prev_time = time.time()

        instruments = (
            {'prefix': 'prog', 'label': 'Prognostic factors'},
            {'prefix': 'comorb', 'label': 'Comorbidities'},
            {'prefix': 'exposure', 'label': 'Exposure'},
            {'prefix': 'status', 'label': 'Status'},
            {'prefix': 'diag', 'label': 'Diagnosis'},
            {'prefix': 'imaging', 'label': 'Imaging'},
            {'prefix': 'comments', 'label': 'Comments'}
        )
        rendered = render(
            request,
            'clinical/report.html',
            {
                'patient': patient, 'current_case': current_case, 'prev_cases': cases_with_treatment[:-1], 'first_case': first_case,
                'clinical_data': clinical_df,
                'clinical_dictionary': clinical_dictionary_df,
                'instruments': instruments,
                'medications': medications_df,
                'side_effects': side_effects_df,
                'blood_tests': blood_tests_df
            }
        )

        # print('rendererd: ' + str(time.time() - prev_time)); prev_time = time.time()

        return rendered


class UpdateTreatmentsView(LoginRequiredMixin, View):
    """To see the case with id case_id and the files associated (see in genomic app for the rest)."""

    def get(self, request, case_id):
        case = get_accessible_case(request, case_id)
        files = File.objects.filter(case=case.id).order_by('-id')
        treat_elements = Treatment.objects.filter(case=case.id).order_by('treat_instance')

        treatment_str = ', '.join(Drug.code_str(elem.code) for elem in treat_elements)

        form_vcf = VcfForm(
            request.user, case, initial={'lab_info': LabInfo.objects.filter(centre=request.user.profile.centre).first()}
        )

        form_vcf.fields["lab_info"].queryset = LabInfo.objects.filter(centre=request.user.profile.centre)

        patient = case.patient

        patient.age = relativedelta(case.diagnosis_date, patient.birthdate).years

        form_treat_elem = TreatmentForm(case)
        return render(
            request,
            'clinical/update_treatments.html',
            {
                'case': case,
                'patient': patient,
                'files': files,
                'treat_elements': treat_elements,
                'form_vcf': form_vcf,
                'form_treat_elem': form_treat_elem,
                'treatments': treatment_str
            }
        )

    # To update the case (front-end not implemented yet...)
    def post(self, request, case_id):
        case = get_accessible_case(request, case_id)
        form = CaseForm(case.patient, request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("case", kwargs={'case_id': case.id}))

        return HttpResponseRedirect(reverse("patient", kwargs={'patient_id': case.patient.id}))


class TreatmentView(LoginRequiredMixin, View):
    def post(self, request):
        case = get_accessible_case(request, request.POST["case_id"])
        form = TreatmentForm(case, request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'Treatment element added successfully.')
        else:
            messages.warning(request, form.errors)
            # return HttpResponseRedirect(reverse("treatment"))

        return HttpResponseRedirect(reverse("update-treatments", kwargs={'case_id': case.id}))


class MorphologyAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    raise_exception = True  # If there is no user logged in, show a 403 error

    def get_refs(self):
        match_start = MorphologySynonym.objects.filter(description__istartswith=self.q)
        if match_start.count() > 0:
            return match_start
        return MorphologySynonym.objects.filter(description__icontains=self.q)

    def get_queryset(self):
        refs = self.get_refs().all()
        tops = []
        for ref in refs:
            top = ref.morphology
            if top.id not in tops:
                tops.append(top.id)
        return Morphology.objects.filter(id__in=tops).order_by('id')


class TopographyAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    raise_exception = True

    def get_refs(self):
        match_start = TopographySynonym.objects.filter(description__istartswith=self.q)
        if match_start.count() > 0:
            return match_start
        return TopographySynonym.objects.filter(description__icontains=self.q)

    def get_queryset(self):
        refs = self.get_refs().all()
        tops = []
        for ref in refs:
            top = ref.topography
            if top.id not in tops:
                tops.append(top.id)
        return Topography.objects.filter(id__in=tops).order_by('id')


class DiagnosisAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    raise_exception = True

    def get_refs(self):
        match_start = DiagnosisSynonym.objects.filter(description__istartswith=self.q)
        if match_start.count() > 0:
            return match_start
        return DiagnosisSynonym.objects.filter(Q(description__icontains=self.q) | Q(diagnosis__code__istartswith=self.q))

    def get_queryset(self):
        refs = self.get_refs().all()
        diagnoses = []
        for ref in refs:
            diagnosis = ref.diagnosis
            if diagnosis.id not in diagnoses:
                diagnoses.append(diagnosis.id)
        return Diagnosis.objects.filter(id__in=diagnoses).order_by('id')


class DrugAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    raise_exception = True  # If there is no user logged in, show a 403 error

    def get_refs(self):
        match_start = DrugSynonym.objects.filter(description__istartswith=self.q)
        if match_start.count() > 0:
            return match_start
        return DrugSynonym.objects.filter(description__icontains=self.q)

    def get_queryset(self):
        refs = self.get_refs().all()
        tops = []
        for ref in refs:
            top = ref.drug
            if top.id not in tops:
                tops.append(top.id)
        return Drug.objects.filter(id__in=tops)


# Utils functions to make sure the object is accessible to the user
def get_accessible_patient(request, patient_id):
    patient = Patient.objects.get(pk=patient_id)
    if patient.centre != request.user.profile.centre:
        raise PermissionDenied('The user does not have access to this patient')
    return patient


def get_accessible_case(request, case_id):
    case = Case.objects.get(pk=case_id)
    if case.patient.centre.id != request.user.profile.centre.id:
        raise PermissionDenied('The user does not have access to this case')
    return case


def get_case_treatment_str(case):
    treat_elements = Treatment.objects.filter(case=case.id).order_by('treat_instance')

    drug_lst = []
    treat_lst = []
    for elem in treat_elements:
        drug_name = Drug.off_name_str(elem.drug)
        if drug_name != 'Undefined':
            drug_lst.append(drug_name)
        treat_type = elem.treat_type
        if treat_type not in ['cont', 'cycl', 'cond']:
            if treat_type == 'allo':
                treat_lst.append('Allotrans.')
            elif treat_type == 'waw':
                treat_lst.append('WAW')
            elif treat_type == 'rad':
                treat_lst.append('RT')
            elif treat_type == 'auto':
                treat_lst.append('Autotrans.')
            elif treat_type == 'surg':
                treat_lst.append('Surgery')
            elif treat_type == 'exptr' and pandas.isnull(elem.drug):
                treat_lst.append('Experimental')
            else:
                treat_lst.append('Other')

    drug_lst = sorted(list(set(drug_lst)))  # converting to the list to a set removes duplicates.

    treat_lst = sorted(list(set(treat_lst)))

    drug_and_treatment_lst = drug_lst + treat_lst
    if len(drug_and_treatment_lst) == 0:
        drug_and_treatment_str = '-'
    else:
        drug_and_treatment_str = ', '.join(drug_treat for drug_treat in drug_and_treatment_lst)

    return drug_and_treatment_str


@method_decorator(csrf_exempt, name='dispatch')
class PatientListEndpoint(View):

    def get(self, request, centre_id=-1):
        if centre_id == -1:
            patients = list(Patient.objects.all())
        else:
            patients = list(Patient.objects.filter(centre__id=centre_id).all())
        response = [{'id': p.id, 'centre': p.centre.id, 'local id': p.centre_patient_id, 'sex': p.sex, 'birthdate': p.birthdate} for p in patients]
        return JsonResponse(response, safe=False)  # safe=False because it's a list, not a dict


@method_decorator(csrf_exempt, name='dispatch')
class CaseListEndpoint(View):

    def get(self, request, project_id=-1):
        if project_id == -1:
            cases = list(Case.objects.all())
        else:
            cases = list(Case.objects.filter(project__id=project_id).all())
        response = [{'id': c.id, 'centre': c.project.centre.id, 'project': c.project.id, 'local id': c.project_case_id,
                     'patient': c.patient.centre_patient_id, 'created': str(c.created_dt),
                     'morphology': str(c.morphology), 'topography': str(c.topography), 'diagnosis': str(c.diagnosis),
                     'diagnosis_date': str(c.diagnosis_date), 'relapse': c.relapse_number,
                     'num_files': File.objects.filter(case=c).count()} for c in cases]
        return JsonResponse(response, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class ProjectListEndpoint(View):

    def get(self, request, centre_id=-1):
        if centre_id == -1:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(centre__id=centre_id)
        response = [{'id': p.id, 'centre': p.centre.id, 'name': p.name} for p in projects]
        return JsonResponse(response, safe=False)