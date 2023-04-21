#!/usr/bin/env conda run -n ICE python

# will need to edit this shebang for your system

import numpy as np
import matplotlib.pyplot as plt
import requests
import json
import zipfile
import io
import os
import pprint
import re
import time

#####################################################################################
#################################### Begin user input ###############################

# Credentials

uid = ''  # Enter Earthdata Login user name
pswd = '' # Enter Earthdata Login password
email = '' # Enter Earthdata login email 

# Data product (e.g., 'ATL03')
short_name = 'ATL06'

# Dates in 'yyyy-mm-dd'
# Times in 'HH:mm:ss'
start_date = '2021-07-10'
start_time = '00:00:00'
end_date = '2022-08-11'
end_time = '00:00:00'

# bounds (no spaces after commas)
# '1' for bounding box, else polygon
bType='0'
##bounding_box='72.37,-68.85,72.77,-68.44'
# path to polygon written as a bunch of coordinate pairs
polygon=open('', 'r').read()


# Subsetting by bounding box, based on the area of interest inputted above
ss = 'y'
# Subsetting by geospatial file (Esri Shapefile, KML, etc.)
ps = 'n'
# Subsetting by time, based on the temporal range inputted above
ts = 'y'
# Reformatting option (make sure to omit quotes, e.g. GeoTIFF), otherwise leave blank.
reformat = 'n'
# If yes, more options are needed (see code below)

# Variable subsetting (remove spaces and retain all forward slashes)
#coverage='/gt1l/land_ice_segments/h_li,/gt1l/land_ice_segments/longitude,/gt1l/land_ice_segments/latitude'
coverage=''

# Outfile location
path = ''


#################################### End user input ##################################
######################################################################################


# Find most recent version of data product (005 right now)
# Get json response from CMR collection metadata

params = {
    'short_name': short_name
}

cmr_collections_url = 'https://cmr.earthdata.nasa.gov/search/collections.json'
response = requests.get(cmr_collections_url, params=params)
results = json.loads(response.content)

# Find all instances of 'version_id' in metadata and print most recent version number

versions = [el['version_id'] for el in results['feed']['entry']]
latest_version = max(versions)
print('The most recent version of ', short_name, ' is ', latest_version)

# Create CMR parameters used for granule search. Modify params depending on bounding_box or polygon input.

temporal = start_date + 'T' + start_time + 'Z' + ',' + end_date + 'T' + end_time + 'Z'
granule_search_url = 'https://cmr.earthdata.nasa.gov/search/granules'

if bType == '1':
# bounding box input:
    search_params = {
    'short_name': short_name,
    'version': latest_version,
    'temporal': temporal,
    'page_size': 100,
    'page_num': 1,
    'bounding_box': bounding_box
    }
else:
    # If polygon file input:
    search_params = {
    'short_name': short_name,
    'version': latest_version,
    'temporal': temporal,
    'page_size': 100,
    'page_num': 1,
    'polygon': polygon,
    }

granules = []
headers={'Accept': 'application/json'}
while True:
    response = requests.get(granule_search_url, params=search_params, headers=headers)
    results = json.loads(response.content)

    if len(results['feed']['entry']) == 0:
    #    # Out of results, so break out of loop
        break

    # Collect results and increment page_num
    granules.extend(results['feed']['entry'])
    search_params['page_num'] += 1

print('There are', len(granules), 'granules of', short_name, 'version', latest_version, 'over my area and time of interest.')

granule_sizes = [float(granule['granule_size']) for granule in granules]

print(f'The average size of each granule is {np.mean(granule_sizes):.2f} MB and the total size of all {len(granules)} granules is {sum(granule_sizes):.2f} MB')

# Query service capability URL 

from xml.etree import ElementTree as ET

capability_url = f'https://n5eil02u.ecs.nsidc.org/egi/capabilities/'+short_name+'.005.xml'

# Create session to store cookie and pass credentials to capabilities url

session = requests.session()
s = session.get(capability_url)
response = session.get(s.url,auth=(uid,pswd))

root = ET.fromstring(response.content)

#collect lists with each service option

subagent = [subset_agent.attrib for subset_agent in root.iter('SubsetAgent')]
if len(subagent) > 0 :

    # variable subsetting
    variables = [SubsetVariable.attrib for SubsetVariable in root.iter('SubsetVariable')]  
    variables_raw = [variables[i]['value'] for i in range(len(variables))]
    variables_join = [''.join(('/',v)) if v.startswith('/') == False else v for v in variables_raw] 
    variable_vals = [v.replace(':', '/') for v in variables_join]

    # reformatting
    formats = [Format.attrib for Format in root.iter('Format')]
    format_vals = [formats[i]['value'] for i in range(len(formats))]
    format_vals.remove('')

    # reprojection options
    projections = [Projection.attrib for Projection in root.iter('Projection')]

# Subset

#print service information depending on service availability and select service options
    
if len(subagent) < 1 :
    print('No services exist for', short_name, 'version', latest_version)
    agent = 'NO'
    bbox = ''
    time_var = ''
    reformat = ''
    projection = ''
    projection_parameters = ''
    coverage = ''
    Boundingshape = ''
else:
    agent = ''
    subdict = subagent[0]
    if subdict['spatialSubsetting'] == 'true' and bType == '1':
        Boundingshape = ''
        if ss == 'y': bbox = bounding_box
        else: bbox = '' 
    if subdict['spatialSubsettingShapefile'] == 'true' and bType == '2':
        bbox = ''
        if ps == 'y': Boundingshape = geojson
        else: Boundingshape = '' 
    if subdict['temporalSubsetting'] == 'true':
        if ts == 'y': time_var = start_date + 'T' + start_time + ',' + end_date + 'T' + end_time 
        else: time_var = ''
    else: time_var = ''
    if len(format_vals) > 0 :
        print('These reformatting options are available:', format_vals)
        if reformat == 'n': reformat = '' # Catch user input of 'n' instead of leaving blank
    else: 
        reformat = ''
        projection = ''
        projection_parameters = ''
    if len(projections) > 0:
        valid_proj = [] # select reprojection options based on reformatting selection
        for i in range(len(projections)):
            if 'excludeFormat' in projections[i]:
                exclformats_str = projections[i]['excludeFormat'] 
                exclformats_list = exclformats_str.split(',')
            if ('excludeFormat' not in projections[i] or reformat not in exclformats_list) and projections[i]['value'] != 'NO_CHANGE': valid_proj.append(projections[i]['value'])
        if len(valid_proj) > 0:
            print('These reprojection options are available with your requested format:', valid_proj)
            projection = input('If you would like to reproject, copy and paste the reprojection option you would like (make sure to omit quotes), otherwise leave blank.')
            # Enter required parameters for UTM North and South
            if projection == 'UTM NORTHERN HEMISPHERE' or projection == 'UTM SOUTHERN HEMISPHERE': 
                NZone = input('Please enter a UTM zone (1 to 60 for Northern Hemisphere; -60 to -1 for Southern Hemisphere):')
                projection_parameters = str('NZone:' + NZone)
            else: projection_parameters = ''
        else: 
            print('No reprojection options are supported with your requested format')
            projection = ''
            projection_parameters = ''
    else:
        print('No reprojection options are supported with your requested format')
        projection = ''
        projection_parameters = ''

#no services selected
if reformat == '' and projection == '' and projection_parameters == '' and coverage == '' and time_var == '' and bbox == '' and Boundingshape == '':
    agent = 'NO'

#### Order the data ####

#Set NSIDC data access base URL
base_url = 'https://n5eil02u.ecs.nsidc.org/egi/request'

#Set the request mode to asynchronous if the number of granules is over 100, otherwise synchronous is enabled by default
if len(granules) > 100:
    request_mode = 'async'
    page_size = 2000
else: 
    page_size = 100
    request_mode = 'stream'

#Determine number of orders needed for requests over 2000 granules. 
page_num = int(np.ceil(len(granules)/page_size))

print('There will be', page_num, 'total order(s) processed for our', short_name, 'request.')

Boundingshape=''
if bType == '1':
# bounding box search and subset:
    param_dict = {'short_name': short_name, 
                  'version': latest_version, 
                  'temporal': temporal, 
                  'time': time_var, 
                  'bounding_box': bounding_box, 
                  'bbox': bbox, 
                  'format': reformat, 
                  'projection': projection, 
                  'projection_parameters': projection_parameters, 
                  'Coverage': coverage, 
                  'page_size': page_size, 
                  'request_mode': request_mode, 
                  'agent': agent, 
                  'email': email, }
else:
    # If polygon file input:
    param_dict = {'short_name': short_name, 
                  'version': latest_version, 
                  'temporal': temporal, 
                  'time': time_var, 
                  'polygon': polygon,
                  'Boundingshape': polygon,
                  'format': reformat, 
                  'projection': projection, 
                  'projection_parameters': projection_parameters, 
                  'Coverage': coverage, 
                  'page_size': page_size, 
                  'request_mode': request_mode, 
                  'agent': agent, 
                  'email': email, }

#Remove blank key-value-pairs
param_dict = {k: v for k, v in param_dict.items() if v != ''}

#Convert to string
param_string = '&'.join("{!s}={!r}".format(k,v) for (k,v) in param_dict.items())
param_string = param_string.replace("'","")

#Print API base URL + request parameters
endpoint_list = [] 
for i in range(page_num):
    page_val = i + 1
    API_request = api_request = f'{base_url}?{param_string}&page_num={page_val}'
    endpoint_list.append(API_request)

print(*endpoint_list, sep = "\n") 

# Request data

# Create an output folder if the folder does not already exist.

if not os.path.exists(path):
    os.mkdir(path)

# Different access methods depending on request mode:

if request_mode=='async':
    # Request data service for each page number, and unzip outputs
    for i in range(page_num):
        page_val = i + 1
        print('Order: ', page_val)

    # For all requests other than spatial file upload, use get function
        request = session.get(base_url, params=param_dict)

        print('Request HTTP response: ', request.status_code)

    # Raise bad request: Loop will stop for bad response code.
        request.raise_for_status()
        print('Order request URL: ', request.url)
        esir_root = ET.fromstring(request.content)
        print('Order request response XML content: ', request.content)

    #Look up order ID
        orderlist = []   
        for order in esir_root.findall("./order/"):
            orderlist.append(order.text)
        orderID = orderlist[0]
        print('order ID: ', orderID)

    #Create status URL
        statusURL = base_url + '/' + orderID
        print('status URL: ', statusURL)

    #Find order status
        request_response = session.get(statusURL)    
        print('HTTP response from order response URL: ', request_response.status_code)

    # Raise bad request: Loop will stop for bad response code.
        request_response.raise_for_status()
        request_root = ET.fromstring(request_response.content)
        statuslist = []
        for status in request_root.findall("./requestStatus/"):
            statuslist.append(status.text)
        status = statuslist[0]
        print('Data request ', page_val, ' is submitting...')
        print('Initial request status is ', status)

    #Continue loop while request is still processing
        while status == 'pending' or status == 'processing': 
            print('Status is not complete. Trying again.')
            time.sleep(10)
            loop_response = session.get(statusURL)

    # Raise bad request: Loop will stop for bad response code.
            loop_response.raise_for_status()
            loop_root = ET.fromstring(loop_response.content)

    #find status
            statuslist = []
            for status in loop_root.findall("./requestStatus/"):
                statuslist.append(status.text)
            status = statuslist[0]
            print('Retry request status is: ', status)
            if status == 'pending' or status == 'processing':
                continue

    #Order can either complete, complete_with_errors, or fail:
    # Provide complete_with_errors error message:
        if status == 'complete_with_errors' or status == 'failed':
            messagelist = []
            for message in loop_root.findall("./processInfo/"):
                messagelist.append(message.text)
            print('error messages:')
            pprint.pprint(messagelist)

    # Download zipped order if status is complete or complete_with_errors
        if status == 'complete' or status == 'complete_with_errors':
            downloadURL = 'https://n5eil02u.ecs.nsidc.org/esir/' + orderID + '.zip'
            print('Zip download URL: ', downloadURL)
            print('Beginning download of zipped output...')
            zip_response = session.get(downloadURL)
            # Raise bad request: Loop will stop for bad response code.
            zip_response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
                z.extractall(path)
            print('Data request', page_val, 'is complete.')
        else: print('Request failed.')
            
else:
    for i in range(page_num):
        page_val = i + 1
        print('Order: ', page_val)
        print('Requesting...')
        request = session.get(base_url, params=param_dict)
        print('HTTP response from order response URL: ', request.status_code)
        request.raise_for_status()
        d = request.headers['content-disposition']
        fname = re.findall('filename=(.+)', d)
        dirname = os.path.join(path,fname[0].strip('\"'))
        print('Downloading...')
        open(dirname, 'wb').write(request.content)
        print('Data request', page_val, 'is complete.')
    
    # Unzip outputs
    for z in os.listdir(path): 
        if z.endswith('.zip'): 
            zip_name = path + "/" + z 
            zip_ref = zipfile.ZipFile(zip_name) 
            zip_ref.extractall(path) 
            zip_ref.close() 
            os.remove(zip_name) 
exit()