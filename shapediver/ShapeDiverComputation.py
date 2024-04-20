import json

from viktor.core import Storage
from viktor import File, UserMessage, UserError
import os

# ShapeDiver ticket and modelViewUrl
from shapediver.ShapeDiverTinySdkViktorUtils import ShapeDiverTinySessionSdkMemoized

ticket = os.getenv("SD_TICKET")
if ticket is None or len(ticket) == 0:
    ticket = "805b009e9bde7f264dc1804b71545266315d5d376ac67b9dca41f8d2d9adfecb2818965cd585e8190ede1abd23a752ef66297083b89b6d06bf6ad9c36e72e0712cafffc14fe797cfd263fac1129c6cf304a6730d7541b0aa9aca81648a5aeb419587b0401fb2cb470ac006a8d67cfb09391ae3fc14f2d757-b8a594f1bf2ff362c4e8247591715430"
modelViewUrl = os.getenv("SD_MODEL_VIEW_URL")
if modelViewUrl is None or len(modelViewUrl) == 0:
    modelViewUrl = "https://sdr7euc1.eu-central-1.shapediver.com"


def ShapeDiverComputation(parameters):
 
    # Initialize a session with the model (memoized)
    shapeDiverSessionSdk = ShapeDiverTinySessionSdkMemoized(ticket, modelViewUrl, forceNewSession = True)

    # compute outputs and exports of ShapeDiver model at the same time, 
    # get resulting glTF 2 assets and export assets
    result = shapeDiverSessionSdk.export(paramDict = parameters, includeOutputs = True)

    # get resulting exported asset of export called "BUILDING_STRUCTURE"
    exportItems = result.exportContentItems(exportName = "BUILDING_STRUCTURE")
    if len(exportItems) != 1: 
        UserMessage.warning(f'No exported asset found for export "BUILDING_STRUCTURE".')
    else:
        Storage().set('BUILDING_STRUCTURE', data=File.from_url(exportItems[0]['href']), scope='entity')
    
    # get resulting exported asset of export called "BUILDING_FLOOR_EDGE"
    exportItems = result.exportContentItems(exportName = "BUILDING_FLOOR_EDGE")
    if len(exportItems) != 1: 
        UserMessage.warning(f'No exported asset found for export "BUILDING_FLOOR_EDGE".')
    else:
        Storage().set('BUILDING_FLOOR_EDGE', data=File.from_url(exportItems[0]['href']), scope='entity')

    # get resulting exported asset of export called "BUILDING_FLOOR_ELV_AREA"
    exportItems = result.exportContentItems(exportName = "BUILDING_FLOOR_ELV_AREA")
    if len(exportItems) != 1: 
        UserMessage.warning(f'No exported asset found for export "BUILDING_FLOOR_ELV_AREA".')
    else:
        Storage().set('BUILDING_FLOOR_ELV_AREA', data=File.from_url(exportItems[0]['href']), scope='entity')

    # get glTF2 output
    contentItemsGltf2 = result.outputContentItemsGltf2()
    
    if len(contentItemsGltf2) < 1:
        raise UserError('Computation did not result in at least one glTF 2.0 asset.')
    
    if len(contentItemsGltf2) > 1: 
        UserMessage.warning(f'Computation resulted in {len(contentItemsGltf2)} glTF 2.0 assets, only displaying the first one.')

    glTF_url = contentItemsGltf2[0]['href']
    Storage().set('GLTF_URL', data=File.from_data(glTF_url), scope='entity')

    glTF_file = File.from_url(glTF_url)

    return glTF_file


def ShapeDiverComputationForOptimization(parameters):
    # Initialize a session with the model (memoized)
    shapeDiverSessionSdk = ShapeDiverTinySessionSdkMemoized(ticket, modelViewUrl, forceNewSession=True)

    # compute outputs and exports of ShapeDiver model at the same time,
    # get resulting glTF 2 assets and export assets
    result = shapeDiverSessionSdk.export(paramDict=parameters, includeOutputs=True)

    # get resulting exported asset of export called "BUILDING_STRUCTURE"
    exportItems = result.exportContentItems(exportName="BUILDING_STRUCTURE")
    if len(exportItems) != 1:
        UserMessage.warning(f'No exported asset found for export "BUILDING_STRUCTURE".')
    else:
        BUILDING_STRUCTURE = json.loads(File.from_url(exportItems[0]['href']).getvalue())

    # get resulting exported asset of export called "BUILDING_FLOOR_ELV_AREA"
    exportItems = result.exportContentItems(exportName="BUILDING_FLOOR_ELV_AREA")
    if len(exportItems) != 1:
        UserMessage.warning(f'No exported asset found for export "BUILDING_FLOOR_ELV_AREA".')
    else:
        BUILDING_FLOOR_ELV_AREA = json.loads(File.from_url(exportItems[0]['href']).getvalue())

    return BUILDING_STRUCTURE, BUILDING_FLOOR_ELV_AREA
