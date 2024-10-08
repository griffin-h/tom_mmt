from tom_observations.facility import BaseRoboticObservationForm, BaseRoboticObservationFacility
from tom_observations.models import ObservationRecord
from tom_dataproducts.data_processor import run_data_processor, DataProcessor
from tom_dataproducts.models import DataProduct
from tom_dataproducts.utils import create_image_dataproduct
from tom_targets.models import Target
from astropy.coordinates import SkyCoord
from django import forms
from django.core.files.base import ContentFile
from crispy_forms.layout import Layout, Row, Column
from crispy_forms.bootstrap import AppendedText
import pymmt
from django.conf import settings
import requests
from datetime import datetime
import re
import mimetypes
from tarfile import TarFile
import os
import logging

logger = logging.getLogger(__name__)


class MMTBaseObservationForm(BaseRoboticObservationForm):
    magnitude = forms.FloatField()
    visits = forms.IntegerField(initial=1, min_value=1)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows':8}), required=False)
    priority = forms.ChoiceField(choices=[
        (3, 'low'),
        (2, 'medium'),
        (1, 'high'),
    ], initial=(1, 'high'))
    target_of_opportunity = forms.BooleanField(initial=True)

    def is_valid(self):
        self.full_clean()
        facility = MMTFacility()
        observation_payload = self.observation_payload()
        errors = facility.validate_observation(observation_payload)
        if errors:
            self.add_error(None, errors)
        return super().is_valid()


class MMTBinospecObservationForm(MMTBaseObservationForm):
    program = forms.ChoiceField(choices=settings.FACILITIES['MMT']['programs']['Binospec'])


class MMTMMIRSObservationForm(MMTBaseObservationForm):
    program = forms.ChoiceField(choices=settings.FACILITIES['MMT']['programs']['MMIRS'])


class MMTBinospecImagingForm(MMTBinospecObservationForm):
    filter = forms.ChoiceField(choices=[('g', 'g'), ('r', 'r'), ('i', 'i'), ('z', 'z')])
    exposure_time = forms.IntegerField(min_value=1, initial=100)
    number_of_exposures = forms.IntegerField(initial=5, min_value=1)

    def layout(self):
        return Layout(
            Row(Column('magnitude'), Column(AppendedText('exposure_time', 's')), Column('filter')),
            Row(Column('visits'), Column('number_of_exposures'), Column('priority')),
            Row(Column('program')),
            Row(Column('target_of_opportunity')),
            Row(Column('notes')),
        )

    def observation_payload(self):
        target = Target.objects.get(pk=self.cleaned_data['target_id'])
        ra, dec = SkyCoord(target.ra, target.dec, unit='deg').to_string('hmsdms', sep=':', precision=1).split()
        payload = {
            'observationtype': 'imaging',
            'objectid': re.sub('[^a-zA-Z0-9]', '', target.name),  # only alphanumeric characters allowed
            'ra': ra,
            'dec': dec,
            'epoch': 'J2000',
            'instrumentid': 16,
            'magnitude': self.cleaned_data['magnitude'],
            'maskid': 110,
            'filter': self.cleaned_data['filter'],
            'visits': self.cleaned_data['visits'],
            'exposuretime': self.cleaned_data['exposure_time'],
            'numberexposures': self.cleaned_data['number_of_exposures'],
            'priority': self.cleaned_data['priority'],
            'program': self.cleaned_data['program'],
            'notes': self.cleaned_data['notes'],
            'targetofopportunity': self.cleaned_data['target_of_opportunity'],
        }
        return payload


class MMTMMIRSImagingForm(MMTMMIRSObservationForm):
    exposure_time = forms.IntegerField(min_value=1, initial=60)
    filter = forms.ChoiceField(choices=[('J', 'J'), ('H', 'H'), ('K', 'K'), ('Ks', 'Ks')])
    gain = forms.ChoiceField(choices=[
        ('low', 'low noise'),
        ('high', 'high dynamic range')
    ], initial='high')
    read_tab = forms.ChoiceField(choices=[
        ('ramp_1.475', 'ramp 1.475 s'),
        ('ramp_4.426', 'ramp 4.426 s'),
        ('fowler', 'Fowler')
    ], initial='ramp_1.475')
    dither_size = forms.FloatField(min_value=20, initial=30)
    number_of_exposures = forms.IntegerField(initial=2, min_value=1)

    def layout(self):
        return Layout(
            Row(Column('magnitude'), Column(AppendedText('exposure_time', 's')), Column('filter')),
            Row(Column('gain'), Column('read_tab'), Column(AppendedText('dither_size', 'arcsec'))),
            Row(Column('visits'), Column('number_of_exposures'), Column('priority')),
            Row(Column('program')),
            Row(Column('target_of_opportunity')),
            Row(Column('notes')),
        )

    def observation_payload(self):
        target = Target.objects.get(pk=self.cleaned_data['target_id'])
        ra, dec = SkyCoord(target.ra, target.dec, unit='deg').to_string('hmsdms', sep=':', precision=1).split()
        payload = {
            'observationtype': 'imaging',
            'objectid': re.sub('[^a-zA-Z0-9]', '', target.name),  # only alphanumeric characters allowed
            'ra': ra,
            'dec': dec,
            'epoch': 'J2000',
            'instrumentid': 15,
            'magnitude': self.cleaned_data['magnitude'],
            'maskid': 110,
            'filter': self.cleaned_data['filter'],
            'visits': self.cleaned_data['visits'],
            'exposuretime': self.cleaned_data['exposure_time'],
            'numberexposures': self.cleaned_data['number_of_exposures'],
            'priority': self.cleaned_data['priority'],
            'program': self.cleaned_data['program'],
            'gain': self.cleaned_data['gain'],
            'ReadTab': self.cleaned_data['read_tab'],
            'DitherSize': self.cleaned_data['dither_size'],
            'notes': self.cleaned_data['notes'],
            'targetofopportunity': self.cleaned_data['target_of_opportunity'],
        }
        return payload


class MMTBinospecSpectroscopyForm(MMTBinospecObservationForm):
    exposure_time = forms.IntegerField(min_value=1, initial=900)
    filter = forms.ChoiceField(choices=[('LP3500', 'LP3500'), ('LP3800', 'LP3800')], initial=('LP3800', 'LP3800'))
    grating = forms.ChoiceField(choices=[(270, 270), (600, 600), (1000, 1000)], initial=270)
    central_wavelength = forms.FloatField(min_value=4108, max_value=9279, initial=6800)
    number_of_exposures = forms.IntegerField(initial=2, min_value=1)
    slit_width = forms.ChoiceField(choices=[
        ('Longslit0_75', '0.75'),
        ('Longslit1', '1.00'),
        ('Longslit1_25', '1.25'),
        ('Longslit1_5', '1.50'),
        ('Longslit5', '5.00'),
    ], initial='Longslit1')
    finder_chart = forms.FileField()

    def layout(self):
        return Layout(
            Row(
                Column('magnitude'),
                Column(AppendedText('exposure_time', 's')),
                Column(AppendedText('slit_width', 'arcsec'))
            ),
            Row(
                Column(AppendedText('grating', 'l/mm')),
                Column(AppendedText('central_wavelength', 'Å')),
                Column('filter')
            ),
            Row(Column('visits'), Column('number_of_exposures'), Column('priority')),
            Row(Column('program')),
            Row(Column('target_of_opportunity'), Column('finder_chart')),
            Row(Column('notes')),
        )

    def observation_payload(self):
        target = Target.objects.get(pk=self.cleaned_data['target_id'])
        ra, dec = SkyCoord(target.ra, target.dec, unit='deg').to_string('hmsdms', sep=':', precision=1).split()
        maskid = {
            'Longslit0_75': 113,
            'Longslit1': 111,
            'Longslit1_25': 131,
            'Longslit1_5': 114,
            'Longslit5': 121,
        }.get(self.cleaned_data['slit_width'])
        payload = {
            'observationtype': 'longslit',
            'objectid': re.sub('[^a-zA-Z0-9]', '', target.name),  # only alphanumeric characters allowed
            'ra': ra,
            'dec': dec,
            'epoch': 'J2000',
            'instrumentid': 16,
            'magnitude': self.cleaned_data['magnitude'],
            'grating': self.cleaned_data['grating'],
            'centralwavelength': self.cleaned_data['central_wavelength'],
            'slitwidth': self.cleaned_data['slit_width'],
            'maskid': maskid,
            'filter': self.cleaned_data['filter'],
            'visits': self.cleaned_data['visits'],
            'notes': self.cleaned_data['notes'],
            'exposuretime': self.cleaned_data['exposure_time'],
            'numberexposures': self.cleaned_data['number_of_exposures'],
            'priority': self.cleaned_data['priority'],
            'targetofopportunity': self.cleaned_data['target_of_opportunity'],
            'finder_chart': self.cleaned_data['finder_chart'],
            'program': self.cleaned_data['program'],
        }
        return payload

    def serialize_parameters(self) -> dict:
        parameters = super().serialize_parameters()
        parameters['finder_chart'] = parameters['finder_chart'].name
        return parameters


class MMTMMIRSSpectroscopyForm(MMTMMIRSObservationForm):
    grism = forms.ChoiceField(choices=[
        ('J+zJ', 'J + zJ (0.94–1.51 μm)'),
        ('HK+HK', 'HK + HK (1.25–2.49 μm)'),
        ('HK3+HK', 'HK3 + HK (1.25–2.34 μm)')
    ], label='Grism + Filter', help_text='HK3 has higher sensitivity but less coverage than HK')
    gain = forms.ChoiceField(choices=[
        ('low', 'low noise'),
        ('high', 'high dynamic range')
    ], initial='low')
    read_tab = forms.ChoiceField(choices=[
        ('ramp_1.475', 'ramp 1.475 s'),
        ('ramp_4.426', 'ramp 4.426 s'),
        ('fowler', 'Fowler')
    ], initial='ramp_4.426')
    dither_size = forms.FloatField(initial=30)
    slit_width = forms.ChoiceField(choices=[
        ('1pixel', '0.2'),
        ('2pixel', '0.4'),
        ('3pixel', '0.6'),
        ('4pixel', '0.8'),
        ('5pixel', '1.0'),
        ('6pixel', '1.2'),
        ('12pixel', '2.4')
    ], initial='5pixel')
    finder_chart = forms.FileField()
    exposure_time = forms.IntegerField(min_value=1, initial=180)
    number_of_exposures = forms.IntegerField(initial=4, min_value=1)

    def layout(self):
        return Layout(
            Row(
                Column('magnitude'),
                Column(AppendedText('exposure_time', 's')),
                Column(AppendedText('slit_width', 'arcsec'))
            ),
            Row(Column('grism')),
            Row(Column('gain'), Column('read_tab'), Column(AppendedText('dither_size', 'arcsec'))),
            Row(Column('visits'), Column('number_of_exposures'), Column('priority')),
            Row(Column('program')),
            Row(Column('target_of_opportunity'), Column('finder_chart')),
            Row(Column('notes')),
        )

    def observation_payload(self):
        target = Target.objects.get(pk=self.cleaned_data['target_id'])
        ra, dec = SkyCoord(target.ra, target.dec, unit='deg').to_string('hmsdms', sep=':', precision=1).split()
        grism, filter = self.cleaned_data['grism'].split('+')
        payload = {
            'observationtype': 'longslit',
            'objectid': re.sub('[^a-zA-Z0-9]', '', target.name),  # only alphanumeric characters allowed
            'ra': ra,
            'dec': dec,
            'epoch': 'J2000',
            'instrumentid': 15,
            'magnitude': self.cleaned_data['magnitude'],
            'notes': self.cleaned_data['notes'],
            'gain': self.cleaned_data['gain'],
            'ReadTab': self.cleaned_data['read_tab'],
            'DitherSize': self.cleaned_data['dither_size'],
            'grism': grism,
            'slitwidth': self.cleaned_data['slit_width'],
            'maskid': 111,
            'filter': filter,
            'visits': self.cleaned_data['visits'],
            'exposuretime': self.cleaned_data['exposure_time'],
            'numberexposures': self.cleaned_data['number_of_exposures'],
            'priority': self.cleaned_data['priority'],
            'targetofopportunity': self.cleaned_data['target_of_opportunity'],
            'finder_chart': self.cleaned_data['finder_chart'],
            'slitwidthproperty': 'long',
            'program': self.cleaned_data['program'],
        }
        return payload

    def serialize_parameters(self) -> dict:
        parameters = super().serialize_parameters()
        parameters['finder_chart'] = parameters['finder_chart'].name
        return parameters


class MMTFacility(BaseRoboticObservationFacility):
    name = 'MMT'
    observation_forms = {
        'BINOSPEC_IMAGING': MMTBinospecImagingForm,
        'MMIRS_IMAGING': MMTMMIRSImagingForm,
        'BINOSPEC_SPECTROSCOPY': MMTBinospecSpectroscopyForm,
        'MMIRS_SPECTROSCOPY': MMTMMIRSSpectroscopyForm,
    }
    SITES = {
        'F. L. Whipple': {
            'sitecode': 'flwo',
            'latitude': 31.688944,
            'longitude': -110.884611,
            'elevation': 2616
        },
    }

    def data_products(self, observation_id, product_id=None):
        token = ObservationRecord.objects.get(observation_id=observation_id).parameters.get('program')
        datalist = pymmt.Datalist(token=token)
        datalist.get(targetid=observation_id, data_type='reduced')

        # flatten the dictionary structure across all data sets
        data_products = []
        for datalist in datalist.data:
            for file_info in datalist['datafiles']:
                image = pymmt.Image(token=token)
                image._build_url({'datafileid': file_info['id'], 'token': token})
                file_info['url'] = image.url
                if product_id is None or file_info['id'] == int(product_id):  # None means get all of them
                    data_products.append(file_info)

        return data_products

    def save_data_products(self, observation_record, product_id=None):
        final_products = []
        products = self.data_products(observation_record.observation_id, product_id)

        for product in products:
            dp, created = DataProduct.objects.get_or_create(
                product_id=product['id'],
                target=observation_record.target,
                observation_record=observation_record,
                data_product_type='MMT',  # same as the built-in method except for this line
            )
            if created:
                product_data = requests.get(product['url']).content
                dfile = ContentFile(product_data)
                dp.data.save(product['filename'], dfile)
                dp.save()
                logger.info('Saved new dataproduct: {}'.format(dp.data))
                run_data_processor(dp)
            if settings.AUTO_THUMBNAILS:
                create_image_dataproduct(dp)
                dp.get_preview()
            final_products.append(dp)
        return final_products

    def get_form(self, observation_type):
        return self.observation_forms.get(observation_type, MMTBaseObservationForm)

    def get_observation_status(self, observation_id):
        token = ObservationRecord.objects.get(observation_id=observation_id).parameters.get('program')
        target = pymmt.Target(token=token, payload={'targetid': observation_id})
        if not target.request.ok:
            status = 'UNKNOWN'
        elif target.disabled:
            status = 'CANCELED'
        elif target.iscomplete:
            status = 'COMPLETED'
        elif target.percentcompleted:
            status = f'{target.percentcompleted:.0f}% COMPLETE'
        else:
            status = 'PENDING'
        return {'state': status, 'scheduled_start': None, 'scheduled_end': None}

    def submit_observation(self, observation_payload):
        target = pymmt.Target(token=observation_payload['program'], payload=observation_payload)
        target.post()
        target.upload_finder(observation_payload['finder_chart'])
        return [target.id]

    def validate_observation(self, observation_payload):
        # Target.validate is automatically called by Target.__init__
        target = pymmt.Target(token=observation_payload['program'], payload=observation_payload)
        return target.message['Errors']

    def get_terminal_observing_states(self):
        return ['CANCELED', 'COMPLETED']

    def get_observing_sites(self):
        return self.SITES

    def cancel_observation(self, observation_id):
        token = ObservationRecord.objects.get(observation_id=observation_id).parameters.get('program')
        target = pymmt.Target(token=token, payload={'targetid': observation_id})
        target.delete()

    def get_observation_url(self, observation_id):
        token = ObservationRecord.objects.get(observation_id=observation_id).parameters.get('program')
        # javascript is required to get to the observation_id level, but this is close enough
        return f"https://scheduler.mmto.arizona.edu/catalog.php?token={token}"

    def get_facility_status(self):
        queues = pymmt.Instruments().get_instruments()
        if queues:
            status = queues[0].get('name', 'UNKNOWN')
        else:
            response = requests.get('https://scheduler.mmto.arizona.edu/APIv2/trimester//schedule/all')
            schedule = response.json()
            for run in schedule['published']['runs']:
                start = datetime.strptime(run['start'], '%Y-%m-%d %H:%M:%S-%f')
                end = datetime.strptime(run['end'], '%Y-%m-%d')
                if start < datetime.now() < end:
                    if run.get('instrument') is not None:
                        status = f"{run['instrument']['name']} ({run['title']})"
                    else:
                        status = run['title']
                    break
            else:
                status = 'NO RUN SCHEDULED'
        facility_status = {
            'code': 'MMT',
            'sites': [{
                'code': 'flwo',
                'telescopes': [{
                    'code': 'flwo.doma.6m5a',
                    'status': status,
                }]
            }]
        }
        return facility_status

    def get_facility_weather_urls(self):
        return {'code': 'MMT', 'sites': [{'code': 'flwo',
                                          'weather_url': 'https://www.mmto.org/current-weather-at-the-mmt/'}]}


class MMTDataProcessor(DataProcessor):
    def process_data(self, data_product):
        mimetype = mimetypes.guess_type(data_product.data.path)[0]
        if mimetype == 'application/x-tar':
            logger.info('Untarring MMT file: {}'.format(data_product.data))
            with TarFile(fileobj=data_product.data) as tarfile:
                for member in tarfile.getmembers():
                    if member.name.endswith('_B.fits'):
                        fitsfile = tarfile.extractfile(member)
                        fitsname = os.path.basename(member.name)
                        dp, created = DataProduct.objects.get_or_create(
                            product_id=member.name,
                            target=data_product.target,
                            observation_record=data_product.observation_record,
                            data=ContentFile(fitsfile.read(), fitsname),
                            data_product_type='spectroscopy',
                        )
                        logger.info('Saved new dataproduct: {}'.format(dp.data))
                        run_data_processor(dp)
        return []
