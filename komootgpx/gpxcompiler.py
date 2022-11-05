from datetime import datetime, timedelta

import gpxpy.gpx


class Point:
    CONST_UNDEFINED = -9999

    def __init__(self, json):
        self.lat = self.lng = self.time = self.alt = self.CONST_UNDEFINED

        if "lat" not in json and "lng" not in json:
            return
        self.lat = json["lat"]
        self.lng = json["lng"]
        if "alt" in json:
            self.alt = json["alt"]
        if "t" in json:
            self.time = json["t"]

    def is_empty(self):
        return self.lat == self.CONST_UNDEFINED and self.lng == self.CONST_UNDEFINED

    def has_only_coords(self):
        return self.alt == self.CONST_UNDEFINED and self.time == self.CONST_UNDEFINED


class POI:
    def __init__(self, name, point, image_url, url, description, type):
        self.name = name
        self.point = point
        self.url = url
        self.image_url = image_url
        self.description = description
        self.type = type


def extract_user_from_tip(json):
    if (
        "_embedded" in json
        and "creator" in json["_embedded"]
        and "display_name" in json["_embedded"]["creator"]
    ):
        return json["_embedded"]["creator"]["display_name"] + ": "
    return ""


class GpxCompiler:
    def __init__(self, tour):
        self.tour = tour

        self.route = []
        for coord in tour["_embedded"]["coordinates"]["items"]:
            self.route.append(Point(coord))

    def generate(self):
        gpx = gpxpy.gpx.GPX()
        gpx.name = self.tour["name"]
        if self.tour["type"] == "tour_recorded":
            gpx.name = gpx.name + " (Completed)"
        gpx.description = (
            f"Distance: {str(int(self.tour['distance']) / 1000.0)}km, "
            f"Estimated duration: {timedelta(seconds=self.tour['duration'])}hrs, "
            f"Elevation up: {self.tour['elevation_up']}m, "
            f"Elevation down: {self.tour['elevation_down']}m"
        )
        if "difficulty" in self.tour:
            gpx.description = (
                gpx.description + f", Grade: {self.tour['difficulty']['grade']}"
            )

        gpx.author_name = self.tour["_embedded"]["creator"]["display_name"]
        gpx.author_link = "https://www.komoot.de/user/" + str(
            self.tour["_embedded"]["creator"]["username"]
        )
        gpx.author_link_text = "View " + gpx.author_name + "'s Profile on Komoot"
        gpx.link = "https://www.komoot.de/tour/" + str(self.tour["id"])
        gpx.link_text = "View tour on Komoot"
        gpx.creator = self.tour["_embedded"]["creator"]["display_name"]

        track = gpxpy.gpx.GPXTrack()
        track.name = gpx.name
        track.description = gpx.description
        track.link = gpx.link
        track.link_text = gpx.link_text
        track.link_type = gpx.link_type

        gpx.tracks.append(track)

        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        augment_timestamp = self.route[0].time == 0
        start_date = datetime.strptime(self.tour["date"], "%Y-%m-%dT%H:%M:%S.%f%z")

        for coord in self.route:
            point = gpxpy.gpx.GPXTrackPoint(coord.lat, coord.lng)
            if coord.alt != coord.CONST_UNDEFINED:
                point.elevation = coord.alt
            if coord.time != coord.CONST_UNDEFINED:
                if augment_timestamp:
                    point.time = start_date + timedelta(seconds=coord.time / 1000)
                else:
                    point.time = datetime.fromtimestamp(coord.time / 1000)
            segment.points.append(point)

        return gpx.to_xml()
