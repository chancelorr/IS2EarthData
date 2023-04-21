getData.py

Python script to download subsetted IS2 data from NSIDC. Can readily download ATL03 (geolocated photons) or ATL06 (land ice height) data products, subsetted by date and bounding polygon



polygon.sh

Shell script to produce a polygon outline formatted as a serial list of lon lat pairs (e.g., lon1, lat1, lon2, lat2, etc.).

To use: make a kml outline in google earth, open it in a text editor, and copy and paste the coordinates. This program will clean them up, removing the extra commas and zeros. This can be fed into the toolshelf function getPolygon() to produce a numpy array of these values.
