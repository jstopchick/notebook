"""
Utility functions for Scenario_A_Model_Obs_Compare_Currents.ipynb
"""

from lxml import etree
from io import BytesIO
from warnings import warn
import requests
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

# Scientific stack.
import numpy as np
from IPython.display import HTML
from pandas import DataFrame, concat, read_csv

# Custom IOOS/ASA modules (available at PyPI).
from owslib import fes
from owslib.ows import ExceptionReport


def fes_date_filter(start_date='1900-01-01', stop_date='2100-01-01',
               constraint='overlaps'):
    """Hopefully something like this will be implemented in fes soon."""
    if constraint == 'overlaps':
        propertyname = 'apiso:TempExtent_begin'
        start = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname,
                                                literal=stop_date)
        propertyname = 'apiso:TempExtent_end'
        stop = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname,
                                                  literal=start_date)
    elif constraint == 'within':
        propertyname = 'apiso:TempExtent_begin'
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname,
                                                   literal=start_date)
        propertyname = 'apiso:TempExtent_end'
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname,
                                               literal=stop_date)
    return start, stop


def get_Coops_longName(station):
    """Get longName for specific station from COOPS SOS using DescribeSensor
    request."""
    url = ('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?service=SOS&'
           'request=DescribeSensor&version=1.0.0&'
           'outputFormat=text/xml;subtype="sensorML/1.0.1"&'
           'procedure=urn:ioos:station:NOAA.NOS.CO-OPS:%s') % station
    tree = etree.parse(urlopen(url))
    root = tree.getroot()
    path = "//sml:identifier[@name='longName']/sml:Term/sml:value/text()"
    namespaces = dict(sml="http://www.opengis.net/sensorML/1.0.1")
    longName = root.xpath(path, namespaces=namespaces)
    if len(longName) == 0:
        longName = station
    return longName[0]


def coops2df(collector, station_id, sos_name, iso_start, iso_end):
    """Request CSV response from SOS and convert to Pandas DataFrames."""

    long_name = get_Coops_longName(station_id)
    url = (('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
            'service=SOS&request=GetObservation&version=1.0.0'
            '&observedProperty=currents&offering=urn:ioos:station:NOAA.NOS.CO-OPS:%s'
            '&responseFormat=text/csv&eventTime=%s/%s') % (str(station_id), iso_start, iso_end))
    print url
    data_df = read_csv(url, parse_dates=True, index_col='date_time')
    data_df.name = long_name

    return data_df


def mod_df(arr, timevar, istart, istop, mod_name, ts):
    """Return time series (DataFrame) from model interpolated onto uniform time
    base."""
    t = timevar.points[istart:istop]
    jd = timevar.units.num2date(t)

    # Eliminate any data that is closer together than 10 seconds this was
    # required to handle issues with CO-OPS aggregations, I think because they
    # use floating point time in hours, which is not very accurate, so the
    # FMRC aggregation is aggregating points that actually occur at the same
    # time.
    dt = np.diff(jd)
    s = np.array([ele.seconds for ele in dt])
    ind = np.where(s > 10)[0]
    arr = arr[ind+1]
    jd = jd[ind+1]

    b = DataFrame(arr, index=jd, columns=[mod_name])
    # Eliminate any data with NaN.
    b = b[np.isfinite(b[mod_name])]
    # Interpolate onto uniform time base, fill gaps up to:
    # (10 values @ 6 min = 1 hour).
    c = concat([b, ts], axis=1).interpolate(limit=10)
    return c


def service_urls(records, service='odp:url'):
    """Extract service_urls of a specific type (DAP, SOS) from records."""
    service_string = 'urn:x-esri:specification:ServiceType:' + service
    urls = []
    for key, rec in records.iteritems():
        # Create a generator object, and iterate through it until the match is
        # found if not found, gets the default value (here "none").
        url = next((d['url'] for d in rec.references if
                    d['scheme'] == service_string), None)
        if url is not None:
            urls.append(url)
    return urls


def nearxy(x, y, xi, yi):
    """Find the indices x[i] of arrays (x,y) closest to the points (xi, yi)."""
    ind = np.ones(len(xi), dtype=int)
    dd = np.ones(len(xi), dtype='float')
    for i in np.arange(len(xi)):
        dist = np.sqrt((x-xi[i])**2 + (y-yi[i])**2)
        ind[i] = dist.argmin()
        dd[i] = dist[ind[i]]
    return ind, dd


def find_ij(x, y, d, xi, yi):
    """Find non-NaN cell d[j,i] that are closest to points (xi, yi)."""
    index = np.where(~np.isnan(d.flatten()))[0]
    ind, dd = nearxy(x.flatten()[index], y.flatten()[index], xi, yi)
    j, i = ind2ij(x, index[ind])
    return i, j, dd


def find_timevar(cube):
    """Return the time variable from Iris. This is a workaround for iris having
    problems with FMRC aggregations, which produce two time coordinates."""
    try:
        cube.coord(axis='T').rename('time')
    except:  # Be more specific.
        pass
    timevar = cube.coord('time')
    return timevar


def ind2ij(a, index):
    """Returns a[j, i] for a.ravel()[index]."""
    n, m = a.shape
    j = np.int_(np.ceil(index//m))
    i = np.remainder(index, m)
    return i, j


def get_coordinates(bounding_box, bounding_box_type=''):
    """Create bounding box coordinates for the map."""
    coordinates = []
    if bounding_box_type == "box":
        coordinates.append([bounding_box[1], bounding_box[0]])
        coordinates.append([bounding_box[1], bounding_box[2]])
        coordinates.append([bounding_box[3], bounding_box[2]])
        coordinates.append([bounding_box[3], bounding_box[0]])
        coordinates.append([bounding_box[1], bounding_box[0]])
    return coordinates


def inline_map(m):
    """From http://nbviewer.ipython.org/gist/rsignell-usgs/
    bea6c0fe00a7d6e3249c."""
    m._build_map()
    srcdoc = m.HTML.replace('"', '&quot;')
    embed = HTML('<iframe srcdoc="{srcdoc}" '
                 'style="width: 100%; height: 500px; '
                 'border: none"></iframe>'.format(srcdoc=srcdoc))
    return embed
