import os
import json
from pathlib import Path
import plotly.express as px

from viktor import ViktorController, UserError
from viktor.core import Storage, File, Color, File
from viktor.geometry import GeoPoint
from viktor.utils import memoize

from viktor.parametrization import ViktorParametrization, Page, GeoPointField, OptionField, NumberField, BooleanField, Tab, \
    IntegerField, ActionButton, LineBreak, FileField, DownloadButton, OptionListElement, TextField, GeoPolylineField, Text, DateField, TextAreaField
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

import requests
import base64
import io
from PIL import Image


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

    bridge = Page('Bridge', views=['get_3d_bridge', 'get_manufacturing_model', 'render_bridge'])
    bridge.span = NumberField('Span', min=5000, max=100000, variant='slider', default=25000, flex=100)
    bridge.lb = LineBreak()
    bridge.segmentation = NumberField('Segmentation', min=1000, max=2550, default=2550, variant='slider', flex=100)
    bridge.download_3dm = DownloadButton('Download printing path', 'download_3dm')
    bridge.download_3dm_model = DownloadButton('Download 3d bridge', 'download_3dm_bridge')
    bridge.lb2 = LineBreak()
    # bridge.image = FileField('Image')
    # bridge.prompt = TextAreaField('Prompt', default='Enter a prompt')

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

        if with_bridge:
            parameters['1f06c0bf-fc7a-4033-9aac-3cd5936f31eb'] = 'true'
        else:
            parameters['1f06c0bf-fc7a-4033-9aac-3cd5936f31eb'] = 'false'

        print(parameters)

        ticket='9eabf5ff5203e71772f9296bca3e3af3f5a6c9821c93e38f3849d2de1ab7df5a16b09744f390791d912fb5a55e4ea99653ee82484ef91a3abd91d1dc026d44da9d228c905e2ec992ecd16bfa00ee667f7de94274a3f53608db429eb278e20ae8fcd63d73178f1647c28f3c2ff738885b59615dc662706637-84bc43300760a165df14f58afc7e786d'
        polylines, distance_km = ShapeDiverDataComputation(parameters, ticket)
        print('distance_km', distance_km)
        return polylines, distance_km

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

        ticket='b0c5c5b5d56766d4a7e47e683024374956cbb4a0179065c599b71ed0ddc9f328920246a1060a205317c69664e84333c0ce9e855705b19731c24004db242e23a1dabf6cc73572d8f4c44c9cb866c149a79ab91f51047c03d701c7140b140f25f8ccbc8171acf8a62fe9731e954e04ac286fa470eb32fe2eca-6eea61d2e420467a47c47ea28369b80f'
        
        print(shapediver_locations)
        glTF_file = ShapeDiverComputation(parameters, ticket)
        return GeometryResult(geometry=glTF_file)

    def download_3dm_bridge(self, params, **kwargs):

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

        ticket='b0c5c5b5d56766d4a7e47e683024374956cbb4a0179065c599b71ed0ddc9f328920246a1060a205317c69664e84333c0ce9e855705b19731c24004db242e23a1dabf6cc73572d8f4c44c9cb866c149a79ab91f51047c03d701c7140b140f25f8ccbc8171acf8a62fe9731e954e04ac286fa470eb32fe2eca-6eea61d2e420467a47c47ea28369b80f'
        
        bridge_3dm_href = ShapeDiver3dmComputation(parameters, ticket)

        fl = File.from_url(bridge_3dm_href)
        return DownloadResult(fl, 'bridge_3d_model.3dm')

    @GeometryView('Manufacturing', duration_guess=10, up_axis='Y', update_label='Run ShapeDiver')
    def get_manufacturing_model(self, params, **kwargs):
        parameters = {}
        parameters['2da40d73-8de9-49a5-9b83-752c2d6f9084'] = params.bridge.span
        parameters['dcbcdc2e-0856-4d71-a7dd-96133621ef5e'] = params.bridge.segmentation

        ticket='9c11edcf8fd7f3dd4951fa0785f547cf8edf6a3a0099dec671dcd9839246b0a1a30910bad86643fd1095ae8f34a7a997149f47dc97f0cf28b63c8b570d321eb3be9dda5e99d60f0ff57a1ea15770c36077302e7b56cafec93e4734f37a1051fc610d0bbab02235fa172670726d367ea8a7b6790343611c3b-d4b74ceeee26c41065b38984254482f8'
        
        glTF_file = ShapeDiverComputation(parameters, ticket)
        return GeometryResult(geometry=glTF_file)

    def download_3dm(self, params, **kwargs):
        parameters = {}
        parameters['2da40d73-8de9-49a5-9b83-752c2d6f9084'] = params.bridge.span
        parameters['dcbcdc2e-0856-4d71-a7dd-96133621ef5e'] = params.bridge.segmentation

        ticket='9c11edcf8fd7f3dd4951fa0785f547cf8edf6a3a0099dec671dcd9839246b0a1a30910bad86643fd1095ae8f34a7a997149f47dc97f0cf28b63c8b570d321eb3be9dda5e99d60f0ff57a1ea15770c36077302e7b56cafec93e4734f37a1051fc610d0bbab02235fa172670726d367ea8a7b6790343611c3b-d4b74ceeee26c41065b38984254482f8'
        
        href = ShapeDiver3dmComputation(parameters, ticket)

        fl = File.from_url(href)
        return DownloadResult(fl, 'bridge_printing_path.3dm')

    def stablediffusion(self, base64_image, custom_prompt):
        # Define the URL and the payload to send.
        url = "http://127.0.0.1:7861"

        payload = {
            "prompt": custom_prompt + "beautiful modern concrete bridge over a river in Rotterdam urban landscape, concrete bridge, modern architecture, Rotterdam, RAW photo, subject, 8k uhd, dslr, high quality, film grain, Fujifilm XT3",
            "negative_prompt": "cable-stayed bridge, suspended bridge, (deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime), text, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck,  BadDream, UnrealisticDream",
            "steps": 20,
            "cfg_scale": 7,
            "width": 736, 
            "height": 512,
            "sd_model_checkpoint": "realvisxlV40_v40LightningBakedvae",
            "sampler_name": "Euler a",
            "enable_hr": True,
            "hr_scale": 2,
            "hr_upscaler": "ESRGAN_4x",
            "denoising_strength": 0.7,
            "alwayson_scripts": {
                "controlnet": {
                    "args": [{
                        "module": "depth_midas",
                        "input_image": base64_image,
                        "model": "control-lora-depth-rank128 [df51c1c8]",
                        "weight": 1,
                        "resize_mode": "Crop and Resize",
                        "lowvram": "true",
                        "processor_res": 512,
                        "threshold_a": 0.5,
                        "threshold_b": 0.5,
                        "guidance_start": 0,
                        "guidance_end": 1,
                        "pixel_perfect": True,
                        "control_mode": "Balanced",
                        "hr_option": "Both",
                    },
                    {
                        "module": "canny",
                        "input_image": base64_image,
                        "model": "control-lora-canny-rank128 [c910cde9]",
                        "weight": 1,
                        "resize_mode": "Crop and Resize",
                        "lowvram": "true",
                        "processor_res": 512,
                        "threshold_a": 100,
                        "threshold_b": 200,
                        "guidance_start": 0,
                        "guidance_end": 1,
                        "pixel_perfect": True,
                        "control_mode": "Balanced",
                        "hr_option": "Both",
                    },
                    ]
                }
            }
        }


        # Send said payload to said URL through the API.
        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
        r = response.json()

        # Decode and save the image.
        with open("output.png", 'wb') as f:
            f.write(base64.b64decode(r['images'][0]))


    @ImageView("Render", duration_guess=5)
    def render_bridge(self, params, **kwargs):

        # if params.bridge.image is None:
        #     raise UserError("No file uploaded")

        # mock up code for demo
        import time
        from viktor import progress_message
        time.sleep(2)
        progress_message('Generating render using stable diffusion')
        time.sleep(10)

        image_path = Path(__file__).parent / 'bridge_render.png'

        # diffusion code    
        # image_bytes = params.bridge.image.file.getvalue_binary()
        # base64_image = base64.b64encode(image_bytes).decode('utf-8')
        # self.stablediffusion(base64_image, params.bridge.prompt)
        # image_path = Path(__file__).parent / 'output.png'
        
        return ImageResult.from_path(image_path)


    def generate_word_document(self, params):
       

       _, distance_with_bridge = self.get_route(params, with_bridge=True)
       _, distance_without_bridge = self.get_route(params, with_bridge=False)

       duration_with_bridge_min = round((distance_with_bridge / 15) * 60)
       duration_without_bridge_min = round((distance_without_bridge / 15) * 60)

       ########################################
       #should be changed automatically!
       starting_point = f"Home, ({round(params.location.start_point.lat, 2)},{round(params.location.start_point.lon, 2)})"
       coffeeshop_point = f"Starbucks ({round(params.location.end_point.lat, 2)},{round(params.location.end_point.lon, 2)})"
       time_before = f"{duration_without_bridge_min}"
       time_after = f"{duration_with_bridge_min}"
       distance_before = f"{round(distance_without_bridge)}"
       distance_after = f"{round(distance_with_bridge)}"
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
       image_path = Path(__file__).parent / "bridge_render.png"
       with open(image_path, 'rb') as image:
        word_file_image = WordFileImage(image, 'map_figure', width=width_value, height=height_value)
       components.append(word_file_image)

       #2.Place image before version
       image_path = Path(__file__).parent / "without_bridge.png"
       with open(image_path, 'rb') as image:
        word_file_image = WordFileImage(image, 'map_before', width=width_value, height=height_value)
       components.append(word_file_image)

       #3.Place image after version
       image_path = Path(__file__).parent / "with_bridge.png"
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

