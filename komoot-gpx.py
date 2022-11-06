import getopt
import os
import sys

import colorama

from komootgpx.api import KomootApi
from komootgpx.gpxcompiler import GpxCompiler
from komootgpx.utils import (
    bcolor,
    sanitize_filename,
    print_error,
    print_success,
    prompt,
    prompt_pass,
)

colorama.init()


def usage():
    print(bcolor.HEADER + bcolor.BOLD + "komoot-gpx.py [options]" + bcolor.ENDC)
    print(bcolor.OKBLUE + "[Authentication]" + bcolor.ENDC)
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-m", "--mail=mail_address", "Login using specified email address"
        )
    )
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-p", "--pass=password", "Use provided password and skip interactive prompt"
        )
    )
    print(bcolor.OKBLUE + "[Tours]" + bcolor.ENDC)
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-u",
            "--user",
            "Retrieve tours of this user (Komoot user ID, e.g. 1358618151959). "
            + "Otherwise retrieve tours of logged in user",
        )
    )
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-l", "--list-tours", "List all tours of the logged in user"
        )
    )
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-d", "--make-gpx=tour_id", "Download tour as GPX"
        )
    )
    print("\t{:<2s}, {:<30s} {:<10s}".format("-a", "--make-all", "Download all tours"))
    print(bcolor.OKBLUE + "[Filters]" + bcolor.ENDC)
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-f",
            "--filter=type",
            'Filter by track type (either "planned" or ' '"recorded")',
        )
    )
    print(bcolor.OKBLUE + "[Generator]" + bcolor.ENDC)
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-o", "--output", "Output directory (default: working directory)"
        )
    )
    print(
        "\t{:<2s}, {:<30s} {:<10s}".format(
            "-e", "--no-poi", "Do not include highlights as POIs"
        )
    )


def make_gpx(tour, output_dir):
    gpx = GpxCompiler(tour.json_data)

    path = f"{output_dir}/{sanitize_filename(tour.json_data['name'])}-{tour.id}.gpx"
    f = open(path, "w", encoding="utf-8")
    f.write(gpx.generate())
    f.close()

    print_success(f"GPX file written to '{path}'")


def main(argv):
    tour_selection = ""
    mail = ""
    pwd = ""
    user_id = ""
    print_tours = False
    typeFilter = "all"
    output_dir = os.getcwd()

    try:
        opts, args = getopt.getopt(
            argv,
            "hlo:d:m:p:f:u:",
            [
                "list-tours",
                "make-gpx=",
                "mail=",
                "pass=",
                "user=",
                "filter=",
                "output=",
                "make-all",
            ],
        )
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()

        elif opt in "--filter":
            typeFilter = "tour_" + str(arg)

        elif opt in ("-l", "--list-tours"):
            print_tours = True

        elif opt in ("-d", "--make-gpx"):
            tour_selection = str(arg)

        elif opt in ("-m", "--mail"):
            mail = str(arg)

        elif opt in ("-p", "--pass"):
            pwd = str(arg)

        elif opt in ("-u", "--user"):
            user_id = str(arg)

        elif opt in ("-o", "--output"):
            output_dir = str(arg)

        elif opt in ("-a", "--make-all"):
            tour_selection = "all"

    if mail == "":
        mail = prompt("Enter your mail address (komoot.de)")

    if pwd == "":
        pwd = prompt_pass("Enter your password (input hidden)")

    # log in to Komoot with the specified user
    api = KomootApi()
    api.login(mail, pwd)

    # if another user is specified, retrieve their tours. If none specified,
    # retrieve tours of the logged in user.
    if user_id == "":
        user_id = None

    # fetch all tours of the user
    tours = api.fetch_tours(user_id, typeFilter)
    api.print_tours(tours)

    # exit in case just the tours should be printed
    if print_tours:
        exit(0)

    # tour_selection can be set to `all`. In this case, all tours will be retrieved.
    # If tour_selection is not set, ask user which tour to retrieve.
    if tour_selection == "":
        tour_selection = prompt("Enter a tour id to download")

    if tour_selection != "all" and int(tour_selection) not in tours:
        print_error(
            "Unknown tour id selected. These are all available tours on the profile:"
        )
        api.print_tours(tours)
        exit(0)

    if tour_selection == "all":
        for tour_id in tours:
            tour = api.fetch_tour(tour_id)
            make_gpx(tour, output_dir)
    else:
        tour = api.fetch_tour(tour_selection)
        make_gpx(tour, output_dir)
    print()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print()
        print_error("Aborted by user")
        exit(1)
