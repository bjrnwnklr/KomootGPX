import base64
import requests
from requests.exceptions import HTTPError
from dataclasses import dataclass, asdict
from datetime import timedelta
from gpxpy.geo import Location


@dataclass
class TourDetails:
    id: int
    name: str
    sport: str
    distance: int  # distance in meters
    duration: int  # duration in seconds
    elevation_up: int
    elevation_down: int
    tourtype: str
    user_id: int
    user_display_name: str

    def __repr__(self):
        distance = self.distance / 1000.0
        duration = timedelta(seconds=self.duration)

        return (
            f"{self.id}: {self.name} by {self.user_display_name} "
            + f"({distance:.1f}km / {duration}hrs / {self.elevation_up}m 🠕 / "
            + f"{self.elevation_down}m 🠗) [{self.tourtype}]"
        )


@dataclass
class Tour:
    id: int
    json_data: dict


@dataclass
class User:
    id: int
    display_name: str


@dataclass
class Highlight:
    id: int
    name: str
    creator: User
    location: Location
    sport: str


@dataclass
class QueryFilter:
    """Used to filter results when calling the `/user/{username}/tours/` API.

    Valid values:
    - type: [str] `tour_planned`, `tour_recorded`. Default: `None`,
        i.e. fetches all tours.
    - sport_types: [str] see list at
        https://static.komoot.de/doc/external-api/v007/sports.html for possible values
        - `mtb` for Mountain Bike tours
        - `e_mtb` for eMTB tours
        - `mtb_advanced` for Enduro MTB tours
        - `hike` for hiking / walking
        Default: `None`, i.e. fetch all types
    - center: tuple[float] Filter for tours with start point around this center.
        Has to be in `(lat,lng)` format. Default: `None`
    - max_distance: [int] distance of start point of tours from
        `center` in meters. Set between length of the desired tour
        and half of the length to capture enough tours
        Default: None
    """

    type: str = None
    sport_types: str = None
    center: tuple[float] = None
    max_distance: int = None


class BasicAuthToken(requests.auth.AuthBase):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __call__(self, r):
        authstr = "Basic " + base64.b64encode(
            bytes(self.key + ":" + self.value, "utf-8")
        ).decode("utf-8")
        r.headers["Authorization"] = authstr
        return r


class KomootApi:
    def __init__(self):
        self.user_id = ""
        self.token = ""

    def __build_header(self):
        if self.user_id != "" and self.token != "":
            return {
                "Authorization": "Basic {0}".format(
                    base64.b64encode(
                        bytes(self.user_id + ":" + self.token, "utf-8")
                    ).decode()
                )
            }
        return {}

    @staticmethod
    def __send_request(url, auth, params=None):
        if not params:
            params = {}
        try:
            r = requests.get(url, params=params, auth=auth)
            r.raise_for_status()
        except HTTPError as exc:
            code = exc.response.status_code
            if code == 403:
                # oops, we hit a private profile our tour
                # and are not permissioned to view
                # TODO: add log message
                pass
            else:
                raise

        return r

    def login(self, email, password):

        r = self.__send_request(
            "https://api.komoot.de/v006/account/email/" + email + "/",
            BasicAuthToken(email, password),
        )

        self.user_id = r.json()["username"]
        self.token = r.json()["password"]

    def fetch_tours(self, tour_user_id=None, queryfilter=None) -> dict[TourDetails]:
        """Fetches all tours from a user. Tours can be filtered by passing a
        `QueryFilter` instance to the `queryfilter` argument.

        Valid values for the `QueryFilter` instance:
        - type: [str] `tour_planned`, `tour_recorded`. Default: `None`, i.e. fetches
            all tours.
        - sport_types: [str] see list at
            https://static.komoot.de/doc/external-api/v007/sports.html
            for possible values
            - `mtb` for Mountain Bike tours
            - `e_mtb` for eMTB tours
            - `mtb_advanced` for Enduro MTB tours
            - `hike` for hiking / walking
            Default: `None`, i.e. fetch all types
        - center: tuple[float] Filter for tours with start point around this center.
            Has to be in `(lat,lng)` format. Default: `None`
        - max_distance: [int] distance of start point of tours from `center`
            in meters. Set between length of the desired tour and half of the length
            to capture enough tours
            Default: None

        Args:
            tour_user_id (int, optional): Numeric komoot id of the tour.
                Defaults to None.
            queryfilter (QueryFilter, optional): `QueryFilter` instance to filter the
                returned results. Defaults to None.

        Returns:
            dict[TourDetails]: A dictionary of `TourDetails` instances,
                with the tour id as key.
        """

        # define the parameters to pass to the komoot API query for tours.
        # if no queryfilter object is passed, use an empty dict.
        # If a queryfilter instance is passed, convert to dict as the requests parameter
        # is a dictionary
        if not queryfilter:
            params = {}
        else:
            params = asdict(queryfilter)

        # if a different user than the logged in one is specified, it is mandatory
        # to set the `status` parameter of the request to `public`.
        # Otherwise, use the current logged in user.
        if tour_user_id:
            params["status"] = "public"
        else:
            tour_user_id = self.user_id

        results = {}
        has_next_page = True
        current_uri = "https://api.komoot.de/v007/users/" + tour_user_id + "/tours/"
        while has_next_page:
            r = self.__send_request(
                current_uri, BasicAuthToken(self.user_id, self.token), params
            )
            response = r.json()

            # check if any results found; if no results exit and return
            # an empty dict.
            total_elements = response["page"]["totalElements"]
            if total_elements == 0:
                break

            # process tours that were found and add to results
            tours = response["_embedded"]["tours"]
            for tour in tours:
                results[tour["id"]] = TourDetails(
                    tour["id"],
                    tour["name"],
                    tour["sport"],
                    int(tour["distance"]),
                    int(tour["duration"]),
                    int(tour["elevation_up"]),
                    int(tour["elevation_down"]),
                    tour["type"],
                    tour_user_id,
                    tour["_embedded"]["creator"]["display_name"],
                )

            # check if there is a next page link, if yes process
            # the link in the next iteration
            has_next_page = (
                "next" in response["_links"] and "href" in response["_links"]["next"]
            )
            if has_next_page:
                current_uri = response["_links"]["next"]["href"]

        return results

    def print_tours(self, tours):
        print()
        for tour_id in tours:
            print(tours[tour_id])

        if len(tours) < 1:
            print("No tours found on profile.")

    def fetch_tour(self, tour_id):

        # some of these query parameters are no longer supported.
        # The only supported ones are in _embedded:
        # coordinates, way_types, surfaces, directions, participants
        # Not supported:
        # timeline, directions, fields, format, timeline_highlights_fields, recommenders
        r = self.__send_request(
            "https://api.komoot.de/v007/tours/"
            + tour_id
            + "?_embedded=coordinates,way_types,"
            "surfaces,directions,participants,"
            "timeline&directions=v2&fields"
            "=timeline&format=coordinate_array"
            "&timeline_highlights_fields=tips,"
            "recommenders",
            BasicAuthToken(self.user_id, self.token),
        )

        return Tour(tour_id, r.json())

    def fetch_tour_gpx(self, tour_id: int) -> str:
        """Fetch the gpx track of a given tour.

        Args:
            tour_id (int): Id of the tour.

        Returns:
            str: XML string containing the GPX track

        Format of the returned string:

        ```xml
        <?xml version='1.0' encoding='UTF-8'?>
        <gpx version="1.1" creator="https://www.komoot.de"
            xmlns="http://www.topografix.com/GPX/1/1"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.topografix.com/GPX/1/1
            http://www.topografix.com/GPX/1/1/gpx.xsd">
        <metadata>
            <name>Goldener Oktober und dicker Nebel: Chestenberg Tour</name>
            <author>
            <link href="https://www.komoot.de">
                <text>komoot</text>
                <type>text/html</type>
            </link>
            </author>
        </metadata>
            <trk>
                <name>Goldener Oktober und dicker Nebel: Chestenberg Tour</name>
                <trkseg>
                    <trkpt lat="47.359209" lon="8.362022">
                        <ele>543.369024</ele>
                        <time>2022-10-23T07:08:56.000Z</time>
                    </trkpt>
                </trkseg>
            </trk>
        </gpx>
        ```
        """
        params = {}

        uri = f"https://api.komoot.de/v007/tours/{tour_id}.gpx"
        r = self.__send_request(uri, BasicAuthToken(self.user_id, self.token), params)

        return r.text

    def fetch_highlight_tips(self, highlight_id):

        r = self.__send_request(
            "https://api.komoot.de/v007/highlights/" + highlight_id + "/tips/",
            BasicAuthToken(self.user_id, self.token),
            critical=False,
        )

        return r.json()

    def fetch_recommenders(self, highlight_id):
        params = {}

        results = {}
        has_next_page = True
        current_uri = (
            f"https://api.komoot.de/v007/highlights/{highlight_id}/recommenders/"
        )
        while has_next_page:
            r = self.__send_request(
                current_uri, BasicAuthToken(self.user_id, self.token), params
            )

            has_next_page = (
                "next" in r.json()["_links"] and "href" in r.json()["_links"]["next"]
            )
            if has_next_page:
                current_uri = r.json()["_links"]["next"]["href"]

            recommenders = r.json()["_embedded"]["items"]
            for recommender in recommenders:
                # get only public profiles
                if recommender["status"] != "public":
                    continue
                results[recommender["username"]] = User(
                    recommender["username"], recommender["display_name"]
                )

        return results

    def fetch_highlight(self, highlight_id):
        params = {}

        uri = f"https://api.komoot.de/v007/highlights/{highlight_id}/"
        r = self.__send_request(uri, BasicAuthToken(self.user_id, self.token), params)

        highlight = r.json()
        result = Highlight(
            highlight["id"],
            highlight["name"],
            User(
                highlight["_embedded"]["creator"]["username"],
                highlight["_embedded"]["creator"]["display_name"],
            ),
            Location(
                highlight["mid_point"]["lat"],
                highlight["mid_point"]["lng"],
                highlight["mid_point"]["alt"],
            ),
            highlight["sport"],
        )

        return result
