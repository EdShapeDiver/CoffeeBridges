import os
import json
from pathlib import Path
import plotly.express as px

from viktor import ViktorController, UserError
from viktor.core import Storage, File, Color, File
from viktor.geometry import GeoPoint
from viktor.utils import memoize

from viktor.parametrization import ViktorParametrization, Page, GeoPointField, OptionField, NumberField, BooleanField, Tab, \
    IntegerField, ActionButton, LineBreak, FileField, DownloadButton, OptionListElement, TextField, GeoPolylineField, Text, DateField
from viktor.result import DownloadResult
from viktor.views import MapView, MapResult, MapPoint, GeometryView, GeometryResult, WebView, WebResult, \
    PlotlyAndDataResult, PlotlyAndDataView, PlotlyView, PlotlyResult, DataView, DataResult, MapPolyline, ImageView, ImageResult, PDFView, PDFResult
from viktor.external.generic import GenericAnalysis
from viktor.external.word import render_word_file
from viktor.external.word import WordFileTag, WordFileImage

from pathlib import Path

from viktor.utils import convert_word_to_pdf

from io import StringIO

import numpy as np

from viktor.geometry import RDWGSConverter


import matplotlib.pyplot as plt
from shapediver.ShapeDiverComputation import ShapeDiverComputation, ShapeDiverDataComputation, ShapeDiver3dmComputation

from google import create_html, get_elevation


def param_site_class_visible(params, **kwargs):
    if params.structural.code and params.structural.code.lower().startswith('asce7'):
        return True
    else:
        return False


SECRET = os.getenv('GOOGLE_API_TOKEN')


class Parametrization(ViktorParametrization):
    intro = Page('Introduction', views=['introduction_view'])
    
    location = Page('Location', views=['get_map_view', 'elevation'])
    location.start_point = GeoPointField('Start point')
    location.end_point = GeoPointField('End point')
    location.bridge_location = GeoPolylineField('Bridge location')
    location.with_bridge = BooleanField('Include bridge on route')

    bridge = Page('Bridge', views=['get_3d_bridge', 'get_manufacturing_model'])
    bridge.span = NumberField('Span', min=5000, max=100000, variant='slider', default=25000, flex=100)
    bridge.lb = LineBreak()
    bridge.segmentation = NumberField('Segmentation', min=1000, max=2550, default=2550, variant='slider', flex=100)
    bridge.download_3dm = DownloadButton('Download printing path', 'download_3dm')

    reporting = Page('Expensive PDFs', views=['pdf_view'])
    reporting.project_name = TextField('Name of coffee lovers')
    reporting.project_date = DateField('Choose a date')


class Controller(ViktorController):
    label = 'Building'
    parametrization = Parametrization

    def get_route(self, params, with_bridge):
        start_bridge = params.location.bridge_location.points[0]
        end_bridge = params.location.bridge_location.points[1]
        start_route_lat = params.location.start_point.lat
        start_route_lon = params.location.start_point.lon
        end_route_lat = params.location.end_point.lat
        end_route_lon = params.location.end_point.lon
        start_bridge_lat = start_bridge.lat
        start_bridge_lon = start_bridge.lon
        end_bridge_lat = end_bridge.lat
        end_bridge_lon = end_bridge.lon

        parameters = {}
        parameters['c6f5073a-4fa7-47cf-8d5a-56aa64656e51'] = start_route_lat
        parameters['6bf2f510-166f-4d5d-b1a3-1f853fb99ef4'] = start_route_lon
        parameters['7cde3167-8ab0-4b4a-b439-0f5f126da52d'] = end_route_lat
        parameters['f390415b-c09f-43ab-80ca-804395e351a5'] = end_route_lon
        parameters['8f95080c-0cbe-430c-8181-7876c37e54f5'] = start_bridge_lat
        parameters['5b61b727-fa71-4762-b5d2-c29ca40f6abc'] = start_bridge_lon
        parameters['1ef66459-c499-4492-b4da-3404e954a806'] = end_bridge_lat
        parameters['436e5eb7-89fe-4a9d-badb-ab947dd2635b'] = end_bridge_lon

        if params.location.with_bridge:
            parameters['1f06c0bf-fc7a-4033-9aac-3cd5936f31eb'] = 'true'
        else:
            parameters['1f06c0bf-fc7a-4033-9aac-3cd5936f31eb'] = 'false'

        print(parameters)

        ticket='3b773ae01d9b4e8bd6079ad70b8eed101b77fe0c2a7f21ffba3967b568573b7953223412800772936d8980923b711152be730d91847d60852c8198a6995e7d8b9996cf6b48bfbd5410e44c671458cabe0aac23739078fcf19ec0ae2cf696213af9cc6c490cbc7f9eb9ed57ff9f2f9134510a62528cf85c95-f2882bcadce4a59d285e2d86541c4fde'
        polylines = ShapeDiverDataComputation(parameters, ticket)
        total_distance = 0
        return polylines, total_distance

    @WebView('Introduction', duration_guess=1)
    def introduction_view(self, params, **kwargs):
        html_path = Path(__file__).parent / 'introduction_page.html'
        return WebResult.from_path(html_path)

    @MapView('Map', duration_guess=1)
    def get_map_view(self, params, **kwargs):

        features = []
        if params.location.start_point is not None:
            center_marker = MapPoint.from_geo_point(params.location.start_point, color=Color.green())
            features.append(center_marker)

        if params.location.end_point is not None:
            center_marker = MapPoint.from_geo_point(params.location.end_point, color=Color.green())
            features.append(center_marker) 

        if params.location.bridge_location is not None:
            center_marker = MapPolyline.from_geo_polyline(params.location.bridge_location)
            features.append(center_marker) 
            locations = self.get_locations(params.location.bridge_location, SECRET)
            for lat, lon, elevation in locations:
                pass
                # features.append(MapPoint(lat, lon))



        if (params.location.start_point is not None and
            params.location.end_point is not None and
            params.location.bridge_location is not None):

            polylines, _ = self.get_route(params, params.location.with_bridge)
            
            print('polylines', polylines)
            for polyline in polylines:
                map_points = []
                for lon, lat, elevation in polyline:
                    print('adding route point', lon, lat)
                    map_points.append(MapPoint(lat, lon))
                features.append(MapPolyline(*map_points))

                # map_points.append(MapPoint(lat, lon))
            # features.append(MapPolyline(*map_points))

        return MapResult(features)


    # @memoize
    def get_locations(self, bridge_location, secret):
        start = bridge_location.points[0]
        end = bridge_location.points[1]
        d_lat = end.lat - start.lat
        d_lon = end.lon - start.lon

        step_lat = d_lat / 10
        step_lon = d_lon / 10

        current_lat = start.lat
        current_lon = start.lon
        locations = []
        for x in range(10):
            elevation = get_elevation(current_lat, current_lon, secret)
            locations.append((current_lat, current_lon, elevation))                
            current_lat += step_lat
            current_lon += step_lon

        return locations

    @ImageView("Elevation", duration_guess=5)
    def elevation(self, params, **kwargs):
        fig = plt.figure()

        if params.location.bridge_location is not None:
            locations = self.get_locations(params.location.bridge_location, SECRET)
        else:
            locations = []

        x = 0
        x_vals = []
        y_vals = []
        for lat, lon, elevation in locations:
            x_vals.append(x)
            y_vals.append(elevation)
            x += 1
        plt.plot(x_vals, y_vals)

        svg_data = StringIO()
        fig.savefig(svg_data, format='svg')
        plt.close()

        return ImageResult(svg_data)

    @GeometryView('3D bridge', duration_guess=10, up_axis='Y', update_label='Run ShapeDiver')
    def get_3d_bridge(self, params, **kwargs):
        parameters = {}

        locations = self.get_locations(params.location.bridge_location, SECRET)

        shapediver_locations = []
        for lat, lon, elevation in locations:
            x,y = RDWGSConverter.from_wgs_to_rd((lat, lon))
            shapediver_locations.append([x, y, elevation])

        # centering
        x_start, y_start, _ = shapediver_locations[round(len(shapediver_locations)/2)]

        moved_shapediver_locations = [[loc[0]-x_start, loc[1]-y_start, loc[2]] for loc in shapediver_locations]

        parameters['bdd0afd3-d14f-4b77-bb05-90ef7cd7f850'] = moved_shapediver_locations
        parameters['264b7596-c96e-4eec-b6e7-a9055925de1a'] = params.bridge.span
        print(parameters)

        ticket='862ead2a526a0d70a54393ea058d0b246390aade049ee45ea7d80a7072a7aa639846ce95a1f2d1c27b5f193ba5671a000732caff95d1c920e9103e44762ef6478780d9d58f538d4eb175b70c4beb2c81c4e0eeca819d30a03c53069a9de947b3f0a2f62959d54a6060a0a9e46c068aa577dc11c539cf113d-0ec555a918be16853e01ac16ffa03796'
        
        print(shapediver_locations)
        glTF_file = ShapeDiverComputation(parameters, ticket)
        return GeometryResult(geometry=glTF_file)

    @GeometryView('Manufacturing', duration_guess=10, up_axis='Y', update_label='Run ShapeDiver')
    def get_manufacturing_model(self, params, **kwargs):
        parameters = {}
        parameters['2da40d73-8de9-49a5-9b83-752c2d6f9084'] = params.bridge.span
        parameters['dcbcdc2e-0856-4d71-a7dd-96133621ef5e'] = params.bridge.segmentation

        ticket='f2ba5fbf1ba817e36cabe7dd162c3ddda94ab4e55f4ad59f7f000455d6ece043a5377de40d61f13943ac97bca2baa95fac04ce694fd516d9fb2ae4c73c3b148bd6cd0ac58bbe58ab5a07a10c4486f5ea56bedfc5380da3a545e045b68ee52ab638acce5037dfafe12171bb504a70d82b297b25feb047eda7-38249c0c09f94266f8317d85143ed8ca'
        
        glTF_file = ShapeDiverComputation(parameters, ticket)
        return GeometryResult(geometry=glTF_file)

    def download_3dm(self, params, **kwargs):
        parameters = {}
        parameters['2da40d73-8de9-49a5-9b83-752c2d6f9084'] = params.bridge.span
        parameters['dcbcdc2e-0856-4d71-a7dd-96133621ef5e'] = params.bridge.segmentation

        ticket='f2ba5fbf1ba817e36cabe7dd162c3ddda94ab4e55f4ad59f7f000455d6ece043a5377de40d61f13943ac97bca2baa95fac04ce694fd516d9fb2ae4c73c3b148bd6cd0ac58bbe58ab5a07a10c4486f5ea56bedfc5380da3a545e045b68ee52ab638acce5037dfafe12171bb504a70d82b297b25feb047eda7-38249c0c09f94266f8317d85143ed8ca'
        
        href = ShapeDiver3dmComputation(parameters, ticket)

        fl = File.from_url(href)
        return DownloadResult(fl, 'bridge_printing_path.3dm')



    def generate_word_document(self, params):
       

       _, distance_with_bridge = self.get_route(params, with_bridge=True)
       _, distance_without_bridge = self.get_route(params, with_bridge=False)

       duration_with_bridge_min = round((distance_with_bridge / 15) * 60)
       duration_without_bridge_min = round((distance_without_bridge / 15) * 60)

       ########################################
       #should be changed automatically!
       starting_point = f"Home, ({params.location.start_point.lat},{params.location.start_point.lon},z)"
       coffeeshop_point = f"Starbucks ({params.location.end_point.lat},{params.location.end_point.lon},z)"
       time_before = f"{duration_without_bridge_min}"
       time_after = f"{duration_with_bridge_min}"
       distance_before = f"{distance_without_bridge}"
       distance_after = f"{distance_with_bridge}"
       people_before = "6000"
       people_after = "10000"
       bridge_weight = "AAA"
       width_value = 180
       height_value = 180
       ########################################

       #create empty components lists to filled later
       components = []

       # Fill components list with data
       components.append(WordFileTag("Client_name", params.reporting.project_name))
       components.append(WordFileTag("project_date", str(params.reporting.project_date)))
       components.append(WordFileTag("starting_point", str(starting_point)))
       components.append(WordFileTag("coffeeshop_point", str(coffeeshop_point)))
       components.append(WordFileTag("time_before", str(time_before)))
       components.append(WordFileTag("time_after", str(time_after)))
       components.append(WordFileTag("distance_before", str(distance_before)))
       components.append(WordFileTag("distance_after", str(distance_after)))
       components.append(WordFileTag("people_before", str(people_before)))
       components.append(WordFileTag("people_after", str(people_after)))
       components.append(WordFileTag("bridge_weight", str(bridge_weight)))

       #1.Place image from a starting point to a coffeeshop point point with Bridge locations
       image_path = Path(__file__).parent / "map.jpg"
       with open(image_path, 'rb') as image:
        word_file_image = WordFileImage(image, 'map_figure', width=width_value, height=height_value)
       components.append(word_file_image)

       #2.Place image before version
       image_path = Path(__file__).parent / "map_before.jpg"
       with open(image_path, 'rb') as image:
        word_file_image = WordFileImage(image, 'map_before', width=width_value, height=height_value)
       components.append(word_file_image)

       #3.Place image after version
       image_path = Path(__file__).parent / "map_after.jpg"
       with open(image_path, 'rb') as image:
        word_file_image = WordFileImage(image, 'map_after', width=width_value, height=height_value)
       components.append(word_file_image)


       # Get path to template and render word file
       template_path = Path(__file__).parent / "report_template_empty.docx"
       with open(template_path, 'rb') as template:
        word_file = render_word_file(template, components)
       
       return word_file

    @PDFView("PDF viewer", duration_guess=5)
    def pdf_view(self, params, **kwargs):
        word_file = self.generate_word_document(params)

        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)

        return PDFResult(file=pdf_file)
   
    def download_pdf_file(self, params, **kwargs):
        word_file = self.generate_word_document(params)

        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)

        return DownloadResult(pdf_file, "BridgeForCoffee.pdf")

