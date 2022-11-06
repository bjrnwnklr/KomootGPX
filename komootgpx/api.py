import base64
import requests
from dataclasses import dataclass
from datetime import timedelta


from .utils import print_error


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
class Coordinates:
    lat: float
    lng: float
    alt: float


@dataclass
class Highlight:
    id: int
    name: str
    creator: User
    coordinates: Coordinates
    sport: str


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
    def __send_request(url, auth, params=None, critical=True):
        if not params:
            params = {}
        r = requests.get(url, params=params, auth=auth)
        if r.status_code != 200:
            print_error("Error " + str(r.status_code) + ": " + str(r.json()))
            if critical:
                exit(1)
        return r

    def login(self, email, password):
        print("Logging in...")

        r = self.__send_request(
            "https://api.komoot.de/v006/account/email/" + email + "/",
            BasicAuthToken(email, password),
        )

        self.user_id = r.json()["username"]
        self.token = r.json()["password"]

        print("Logged in as '" + r.json()["user"]["displayname"] + "'")

    def fetch_tours(self, tour_user_id=None, tourType="all", silent=False):
        # if a different user than the logged in one is specified, it is mandatory
        # to set the `status` parameter of the request to `public`.
        # Otherwise, use the current logged in user.
        params = {}
        if tour_user_id:
            params["status"] = "public"
        else:
            tour_user_id = self.user_id

        if not silent:
            print("Fetching tours of user '" + tour_user_id + "'...")

        results = {}
        has_next_page = True
        current_uri = "https://api.komoot.de/v007/users/" + tour_user_id + "/tours/"
        while has_next_page:
            r = self.__send_request(
                current_uri, BasicAuthToken(self.user_id, self.token), params
            )

            has_next_page = (
                "next" in r.json()["_links"] and "href" in r.json()["_links"]["next"]
            )
            if has_next_page:
                current_uri = r.json()["_links"]["next"]["href"]

            tours = r.json()["_embedded"]["tours"]
            for tour in tours:
                if tourType != "all" and tourType != tour["type"]:
                    continue
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

        print("Found " + str(len(results)) + " tours")
        return results

    def print_tours(self, tours):
        print()
        for tour_id in tours:
            print(tours[tour_id])

        if len(tours) < 1:
            print_error("No tours found on profile.")

    def fetch_tour(self, tour_id):
        print("Fetching tour '" + tour_id + "'...")

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

    def fetch_highlight_tips(self, highlight_id):
        print("Fetching highlight '" + highlight_id + "'...")

        r = self.__send_request(
            "https://api.komoot.de/v007/highlights/" + highlight_id + "/tips/",
            BasicAuthToken(self.user_id, self.token),
            critical=False,
        )

        return r.json()

    def fetch_recommenders(self, highlight_id=None):
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

        print("Found " + str(len(results)) + " public recommenders")

        return results
