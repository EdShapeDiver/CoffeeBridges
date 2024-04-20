import os
import json
from pathlib import Path
import plotly.express as px

from viktor import ViktorController, UserError
from viktor.core import Storage, File
from viktor.geometry import GeoPoint

from viktor.parametrization import ViktorParametrization, Page, GeoPointField, OptionField, NumberField, BooleanField, Tab, \
    IntegerField, ActionButton, LineBreak, FileField, DownloadButton, OptionListElement, TextField, GeoPolylineField, Text
from viktor.result import DownloadResult
from viktor.views import MapView, MapResult, MapPoint, GeometryView, GeometryResult, WebView, WebResult, \
    PlotlyAndDataResult, PlotlyAndDataView, PlotlyView, PlotlyResult, DataView, DataResult, MapPolyline, ImageView, ImageResult
from viktor.external.generic import GenericAnalysis
from io import StringIO

import numpy as np


import matplotlib.pyplot as plt
from shapediver.ShapeDiverComputation import ShapeDiverComputation

from google import create_html, get_elevation


def param_site_class_visible(params, **kwargs):
    if params.structural.code and params.structural.code.lower().startswith('asce7'):
        return True
    else:
        return False


class Parametrization(ViktorParametrization):
    intro = Page('Introduction')
    intro.txt = Text("This in the introduction placeholder")
    
    location = Page('Location', views=['get_map_view', 'get_geometry_view', 'get_svg_view', 'generate_map'])
    location.start_point = GeoPointField('Start point')
    location.end_point = GeoPointField('End point')
    location.bridge_location = GeoPolylineField('Bridge location')

class Controller(ViktorController):
    label = 'Building'
    parametrization = Parametrization

    @MapView('Map', duration_guess=1)
    def get_map_view(self, params, **kwargs):

        features = []
        if params.location.start_point is not None:
            center_marker = MapPoint.from_geo_point(params.location.start_point)
            features.append(center_marker)

        if params.location.end_point is not None:
            center_marker = MapPoint.from_geo_point(params.location.end_point)
            features.append(center_marker) 

        if params.location.bridge_location is not None:
            center_marker = MapPolyline.from_geo_polyline(params.location.bridge_location)
            features.append(center_marker) 
        
        return MapResult(features)

    @GeometryView('Geometry view', duration_guess=10, up_axis='Y', update_label='Run ShapeDiver')
    def get_geometry_view(self, params, **kwargs):
        parameters = {}
        parameters['6a571a4b-666d-41b8-8e92-b7e0db708ff1'] = str(params.location.start_point.lat)
        parameters['976a1b23-31ad-4a12-b080-90593a63ed8d'] = str(params.location.start_point.lon)
        parameters['77e44938-758a-4a7a-b122-a3c348663f76'] = str(params.location.end_point.lat)
        parameters['6b2f7439-2334-47d1-bddd-bcf1970a1a55'] = str(params.location.end_point.lon)
        print(parameters)
        glTF_file = ShapeDiverComputation(parameters)
        return GeometryResult(geometry=glTF_file)

    @WebView('My map', duration_guess=5)
    def generate_map(self, params, **kwargs):

        lon = 4.6
        lat = 52.5
        secret = 'token'

        elevation = get_elevation(lat, lon, secret)
        print('elevation=', elevation)

        html = create_html(lon, lat, secret)
        return WebResult(html=html)
