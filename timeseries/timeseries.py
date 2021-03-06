#!/usr/bin/python
# -*- coding: utf-8 -*-
#******************************************************************************
#
# This file is part of the timeseries library.
#
# The timeseries library is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# the lizard_waterbalance app.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2011 Nelen & Schuurmans
#
#******************************************************************************
#
# Initial programmer: Mario Frasca
# Initial date:       2011-09-13
# $Id$
#
#******************************************************************************

import logging
from datetime import datetime
from datetime import timedelta
from xml.etree import ElementTree
import re
import operator


logger = logging.getLogger(__name__)


def convert_dom(dom):
    """
    strip all namespaces from tags.
    Replace None with '' in text.

    Want to put this in timseries.utils or so, but import failed.
    """
    root = dom.getroot()
    for e in root.iter():
        e.tag = re.sub('{.*}', '', e.tag)
        if e.tag is None:
            e.tag = ''


def daily_events(events, default_value=0):
    """Return a generator to iterate over all daily events.

    The generator iterates over the events in the given order. If dates are
    missing in between two successive events, this function fills in the
    missing dates with the given default value.

    Parameters:
      *events*
        sequence of (date or datetime, value) pairs ordered by date or datetime

    """
    # We initialize this variable to silence pyflakes.
    date_to_yield = None
    for date, value in events:
        if not date_to_yield is None:
            while date_to_yield < date:
                yield date_to_yield, default_value
                date_to_yield = date_to_yield + timedelta(1)
        yield date, value
        date_to_yield = date + timedelta(1)


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    def new_func(*args, **kwargs):
        logger.debug("Call to deprecated function %s." % func.__name__)
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


logger = logging.getLogger(__name__)


class Pythonifier(object):
    """functor class.  it has one global instance, called `pythonify`.

    given a camelCaseString, return a python_style_string.

    >>> pythonify = Pythonifier()
    >>> pythonify('camelCaseString')
    'camel_case_string'
    >>> pythonify('pythonStyleString')
    'python_style_string'
    """

    def __init__(self):
        self.pattern = re.compile("([A-Z])")

    def __call__(self, text):
        return self.pattern.sub(r"_\1", text).lower()

pythonify = Pythonifier()


def str_to_datetime(date, time, offset=0):
    """convert date/time/offset to datetime

    parameters:
     *date*
       str, in YYYY-mm-dd format
     *time*
       str, in HH:MM:SS format
     *offset*
       numeric, amount of hours expressing the offset from UTC of the
       time zone of the input data.

    returns:
       datetime object

    >>> str_to_datetime('2000-01-01', '00:00:00', 0)
    datetime.datetime(2000, 1, 1, 0, 0)
    >>> str_to_datetime('2000-01-01', '00:00:00', 1)
    datetime.datetime(1999, 12, 31, 23, 0)
    """

    return (datetime.strptime(date + 'T' + time, "%Y-%m-%dT%H:%M:%S") -
            timedelta(0, offset * 3600))


def _element_with_text(doc, tag, content='', attr={}):
    """create a minidom element
    """

    result = doc.createElement(tag)
    if content != '':
        result.appendChild(doc.createTextNode(content))
    for key, value in attr.items():
        result.setAttribute(key, str(value))
    return result


def _append_element_to(element, tag, text='', attrib={}):
    """
    Append child to element with tag and text.
    """
    child = ElementTree.Element(tag, attrib=attrib)
    child.text = text
    element.append(child)


class TimeSeries:
    """Describes a TimeSeries object.

    fields of TimeSeries shadow the content of <series> elements in
    PI files.

    you may argue that this ABC flatly follows a time series
    definition that is not necessarily the best usable in all cases,
    on the other hand, we already use that same definition in our Java
    code (where we don't even implement a complete own class, we just
    use the wldelft definition and make it more usable) and in R.

    """

    def get_events(self, start_date=None, end_date=None, dates=None):
        """return all valid events in given range

        If dates is provided, only return values of given dates
        (ignore start_date and end_date).
        """

        if start_date is None:
            start_date = self.get_start_date()
        if end_date is None:
            end_date = self.get_end_date()
        if dates is None:
            return sorted([(k, v) for (k, v) in self._events.items()
                           if start_date <= k <= end_date])
        else:
            return sorted([(k, v) for (k, v) in self._events.items()
                           if k in dates])

    @deprecated
    def events(self, start_date=None, end_date=None):
        """Return a generator to iterate over the requested daily events.

        Only legacy code uses this function.
        """
        date_value_pairs = self.get_values(start_date, end_date)
        for date, value in daily_events(date_value_pairs):
            yield date, value

    def get_values(self, start_date=None, end_date=None):
        """return only values of events in given range
        """

        result = self.get_events(start_date, end_date)
        return [(k, v[0]) for (k, v) in result]

    def __init__(self, events={}, **kwargs):
        ## one of: instantaneous, continuous.  we usually work with
        ## instantaneous
        self.type = kwargs.get('type', '')
        ## these are used to identify the TimeSeries in a collection
        self.location_id = kwargs.get('location_id')
        self.parameter_id = kwargs.get('parameter_id')
        ## datetime.timedelta or None (for nonequidistant)
        self.time_step = kwargs.get('time_step', '')
        ## what to store in equidistant timeseries in case a value is
        ## missing.
        self.miss_val = kwargs.get('miss_val', '')
        ## don't ask me why wldelft wants this one
        self.station_name = kwargs.get('station_name', '')
        ## geographic coordinates
        self.lat = kwargs.get('lat', '')
        self.lon = kwargs.get('lon', '')
        ## Rijksdriehoekscoördinaten
        self.x = kwargs.get('x', '')
        self.y = kwargs.get('y', '')
        self.z = kwargs.get('z', '')
        ## a string
        self.units = kwargs.get('units', '')
        ## key: timestamp, value: (double, flag, comment)
        self._events = dict(events)  # associate a timestamp to a
                                    # value, let's make a copy of it
        self.is_locf = False
        pass

    def get_start_date(self):
        """return the first timestamp

        returned value must match the events data
        """

        timestamps = self._events.keys()
        try:
            return min(timestamps)
        except:
            return datetime(1970, 1, 1)

    def get_end_date(self):
        """return the last timestamp

        returned value must match the events data
        """

        timestamps = self._events.keys()
        try:
            return max(timestamps)
        except:
            return datetime(1970, 1, 1)

    def add_value(self, tstamp, value):
        """set value/event, fall back to __setitem__
        """

        self.__setitem__(tstamp, value)

    def get_value(self, tstamp):
        """get value part of event
        """

        return self.__getitem__(tstamp)[0]

    def get_event(self, tstamp):
        """get complete event
        """

        return self.__getitem__(tstamp)

    _f = {'lt': lambda x, y: x < y,
          'lte': lambda x, y: x <= y,
          'gt': lambda x, y: x > y,
          'gte': lambda x, y: x >= y,
          }

    def filter(self, **kwargs):
        """similar to django filter"""

        result = self.clone(with_events=True)
        for request in kwargs:
            field, op = request.split("_")
            value = kwargs[request]
            if value is None:
                continue

            assert(field == 'timestamp')

            for timestamp in set(result._events):
                if not self._f[op](timestamp, value):
                    del result._events[timestamp]
        return result

    def __setitem__(self, key, value):
        """behave as a dictionary (content is series events)
        """

        if not isinstance(value, tuple):
            template = list(self._events.get(key, (0, 0, '')))
            template[0] = value
            value = tuple(template)
        self._events[key] = value

    def __getitem__(self, key):
        """behave as a dictionary (content is series events)
        """

        return self._events[key]

    def __delitem__(self, key):
        """behave as a dictionary
        """
        del self._events[key]

    def __len__(self):
        """behave as a container"""
        return len(self._events)

    def get(self, key, default=None):
        """behave as a dictionary (content is series events)
        """

        return self._events.get(key, default)

    @classmethod
    def _from_xml(cls, stream):
        """private function

        convert an open input `stream` looking like a PI file into the
        result described in as_dict

        not all entities are used.  in particular we do not do
        anything with `startDate` and `endDate` (we assume data starts
        and ends at the earliest and latest events) and `timeStep`.

        for `timeStep` the problem is making choices.  do we support
        anything else than "nonequidistant"?  in Java we don't.

        events are read without storing the `flag`.
        """

        def getText(node):
            return "".join(node.itertext())

        def fromNode(node, names):
            '''extract text from included elements, replace capital
            letter with underscore + lower case letter, return
            dictionary'''

            return dict((pythonify(n.tag), getText(n))
                        for n in node.getchildren()
                        if n.tag in set(names))

        from xml.etree import ElementTree
        dom = ElementTree.parse(stream)
        convert_dom(dom)

        root = dom.getroot()

        offsetNode = root.find("timeZone")
        offsetValue = float(getText(offsetNode))

        result = {}

        for seriesNode in root.findall("series"):
            headerNode = seriesNode.find("header")

            kwargs = fromNode(headerNode,
                              ['type', 'locationId', 'parameterId',
                               'missVal', 'stationName', 'lat', 'lon',
                               'x', 'y', 'z', 'units'])

            ignore_value = kwargs.get("miss_val", None)

            obj = TimeSeries(**kwargs)
            result[kwargs['location_id'], kwargs['parameter_id']] = obj

            for eventNode in seriesNode.findall("event"):
                date = eventNode.attrib["date"]
                time = eventNode.attrib["time"]
                attr_value = eventNode.attrib["value"]
                if attr_value != ignore_value:
                    value = float(attr_value)
                    obj[str_to_datetime(date, time, offsetValue)] = value

        return result

    @classmethod
    def _from_django_QuerySet(cls, qs, start, end):
        """private function

        convert a django QuerySet to a result described in as_dict.

        the `qs` QuerySet is assumed to be an iterable containing
        objects each of which with a `event_set` field with an `all`
        method.
        """

        result = {}
        for series in qs:
            obj = TimeSeries()
            event = None
            event_set = series.event_set.all()
            if start is not None:
                event_set = event_set.filter(timestamp__gte=start)
            if end is not None:
                event_set = event_set.filter(timestamp__lte=end)
            for event in event_set:
                obj[event.timestamp] = (
                    event.value, event.flag, event.comment)
            if event is not None:
                ## nice: we ran the loop at least once.
                obj.location_id = series.location.id
                obj.parameter_id = series.parameter.id
                obj.time_step = series.timestep.id
                obj.units = series.parameter.groupkey.unit
                ## and add the TimeSeries to the result
                result[(obj.location_id, obj.parameter_id)] = obj
        return result

    @classmethod
    def as_dict(cls, input, start=None, end=None):
        """convert input to collection of TimeSeries

        input may be (the name of) a PI file or just about anything
        that contains and defines a set of time series.

        output is a dictionary, where keys are the 2-tuple
        location_id/parameter_id and the values are the TimeSeries
        objects.

        `start` and `end` can be specified so that only the desired
        data from the `input` data source is retrieved.  if this
        really happens, it depends on the data source.
        """

        if (isinstance(input, str) or hasattr(input, 'read')):
            ## a string or a file, maybe PI?
            result = cls._from_xml(input)
        elif hasattr(input, 'count') or hasattr(input, 'raw_query'):
            ## a django.db.models.query.QuerySet?
            result = cls._from_django_QuerySet(input, start, end)
        else:
            result = None

        return result

    @classmethod
    def as_list(cls, input):
        """convert input to collection of TimeSeries
        """

        content = cls.as_dict(input)
        return [content[key] for key in sorted(content.keys())]

    @classmethod
    def write_to_pi_file(cls, dest, data, offset=0, append=False):
        """write TimeSeries to a PI-format file.

        `data` is a collection of TimeSeries objects, anything like
        `set`, `dict` or `list` should be good enough, as long as the
        content is TimeSeries.

        `dest` is the complete path of the file to be written.  or it
        is a stream to which we can write.

        `offset`, is a numeric offset from UTC.  it is the only
        property that goes into the pi file that is not owned by any
        of the TimeSeries objects.

        `append` is a boolean.  set it to True if you want to append
        your data to an already open and valid xml file.  the caller
        takes responsibility for writing there the root element and
        for closing it.  it is only used if `dest` is a stream.
        """

        if (isinstance(data, dict)):
            data = [data[key] for key in sorted(data.keys())]

        ## create xml document and add it its root element
        root = ElementTree.Element('TimeSeries')

        ## add references to internet resources for schema checking
        root.attrib.update({
            'xsi:schemaLocation': "http://www.wldelft.nl/fews/PI \
http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd",
            'version': "1.2",
            'xmlns': "http://www.wldelft.nl/fews/PI",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        })

        ## add single timeZone element
        _append_element_to(root, 'timeZone', '%0.2f' % offset)

        offset = timedelta(0, offset * 3600)

        ## add all series elements
        for item in data:
            root.append(item._as_element(offset=offset))

        ## if dest is a name of a file, open it for writing and
        ## remember we should close it before returning.
        if (isinstance(dest, str)):
            writer = file(dest, "w")
        else:
            writer = dest

        def indent(elem, level=0):
            """
            from
            http://www.python-forum.org/pythonforum/viewtopic.php?f=19&t=4207
            with fixes.
            """
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                for child in elem:
                    indent(child, level + 1)
                # Last child has different tail
                if not child.tail or not child.tail.strip():
                    child.tail = i
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        ## write document to open stream
        if writer == dest and append is True:
            #for child in root.getElementsByTagName('series'):
                #child.writexml(writer)
            for child in root.findall('series'):
                writer.write(ElementTree.tostring(child))
        else:
            #doc.writexml(writer, encoding="UTF-8")
            indent(root)
            ElementTree.ElementTree(element=root).write(
                writer,
                encoding='UTF-8',
            )

        ## if we created the writer here, we also need to close it,
        ## otherwise it's the caller's responsibility to do so.
        if (writer != dest):
            writer.close()

    def _as_element(self, offset=timedelta()):
        """create minidom object representing self

        private method
        """

        result = ElementTree.Element('series')
        header = ElementTree.Element('header')
        result.append(header)

        _append_element_to(header, 'type', self.type)
        _append_element_to(header, 'locationId', self.location_id)
        _append_element_to(header, 'parameterId', self.parameter_id)
        _append_element_to(header, 'timeStep', attrib={
            'unit': 'nonequidistant'
        })
        _append_element_to(header, 'startDate', attrib={
            'date': (self.get_start_date() + offset).strftime("%Y-%m-%d"),
            'time': (self.get_start_date() + offset).strftime("%H:%M:%S")})
        _append_element_to(header, 'endDate', attrib={
            'date': (self.get_end_date() + offset).strftime("%Y-%m-%d"),
            'time': (self.get_end_date() + offset).strftime("%H:%M:%S")})
        _append_element_to(header, 'missVal', str(self.miss_val))
        _append_element_to(header, 'stationName', self.station_name)
        _append_element_to(header, 'units', self.units)

        for key, value in self.sorted_event_items():
            if not isinstance(value, tuple):
                value = (value, 0, '')
            value, flag = value[:2]  # ignore comment
            _append_element_to(result, 'event', attrib={
                'date': (key + offset).strftime("%Y-%m-%d"),
                'time': (key + offset).strftime("%H:%M:%S"),
                'value': str(value),
                'flag': str(flag),
            })

        return result

    def sorted_event_items(self):
        """return all items, sorted by key
        """

        return sorted(self._events.items())

    def __eq__(self, other):
        """series equal if all fields equal, included events
        """

        for k in dir(self):
            v = getattr(self, k)
            if type(v) not in [str, int, float, bool]:
                continue
            if v != getattr(other, k, None):
                return False
        if len(self) != len(other):
            return False
        for (a, b) in zip(
            self.sorted_event_items(),
            other.sorted_event_items(),
        ):
            if a != b:
                return False
        return True

    def __binop(self, other, op, null):
        """return self`op`other

        return clone of `self`, with altered events

        *other* can be a constant or a TimeSeries object.

        if *other* is a TimeSeries and contains timestamps that are
        not in *self*, they are added to the resulting timeseries.  if
        either *self* or *other* contain a timestamp that is not
        present in both objects, the missing value is assumed to be
        the specified null value.
        """

        result = self.clone()
        keys = set(self.keys())
        defval = (null, 0, '')
        locf = (null, 0, '')
        if isinstance(other, TimeSeries):
            keys = keys.union(other.keys())
            for key in sorted(keys):
                try:
                    value, flag, comment = self.get(key, locf)
                    if self.is_locf:
                        locf = value, flag, comment
                        if key not in other.keys():
                            continue
                    result[key] = (
                        op(value, other.get(key, defval)[0]),
                        flag,
                        '',
                    )
                except:
                    pass
        else:
            for key in keys:
                flag = self[key][1]
                result[key] = op(self.get_value(key), other), flag, ''

        return result

    def __mul__(self, other):
        """implement multiplication
        """

        return self.__binop(other, operator.mul, None)

    def __add__(self, other):
        """implement addition
        """

        return self.__binop(other, operator.add, 0)

    def __radd__(self, other):
        """addition is commutative
        """

        return self.__add__(other)

    def __sub__(self, other):
        """implement subtraction
        """

        return self.__binop(other, operator.sub, 0)

    def __rsub__(self, other):
        """subtraction is not commutative

        `a - b` is same as `(-b) + a`
        """

        return (-1 * self).__add__(other)

    def __rmul__(self, other):
        """multiplication is commutative
        """

        return self.__mul__(other)

    def __abs__(self):
        """absolute values"""
        result = self.clone(with_events=True)
        for k in set(result._events):
            value = list(result.get_event(k))
            value[0] = abs(value[0])
            result[k] = tuple(value)
        return result

    def clone(self, with_events=False):
        """return a copy of self
        """

        result = TimeSeries(type=self.type,
                            location_id=self.location_id,
                            parameter_id=self.parameter_id,
                            time_step=self.time_step,
                            miss_val=self.miss_val,
                            station_name=self.station_name,
                            lat=self.lat,
                            lon=self.lon,
                            x=self.x,
                            y=self.y,
                            z=self.z,
                            units=self.units)
        if with_events:
            result._events = dict(self._events)
        return result

    def keys(self):
        """behave as a dictionary (content is series events)
        """

        return self._events.keys()
