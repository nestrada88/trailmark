import argparse
import os
import re
from geopy.distance import geodesic
from pyproj import Geod
import gpxpy
import gpxpy.gpx


def load_gpx(file_path: str) -> gpxpy.gpx.GPX:
    """
    Loads and parses a GPX file.

    Args:
        file_path (str): Path to the GPX file.

    Returns:
        gpxpy.gpx.GPX: Parsed GPX object.

    Raises:
        FileNotFoundError: If the file is not found.
        RuntimeError: If there is an error loading the GPX file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            if not gpx.tracks or not gpx.tracks[0].segments:
                raise ValueError("No valid track data found in GPX file.")
            return gpx
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")
    except ValueError as ve:
        raise ValueError(f"Error parsing GPX file: {ve}")
    except Exception as e:
        raise RuntimeError(f"Error loading GPX file: {e}")


def calculate_distance(points: list[gpxpy.gpx.GPXTrackPoint]) -> tuple[float, list[float]]:
    """
    Calculates total distance and cumulative distances along the track with higher precision.

    Args:
        points (list): List of GPX track points.

    Returns:
        tuple: Total distance in km and list of cumulative distances in km.
    """
    if not points:
        raise ValueError("No points found in the track.")

    geod = Geod(ellps="WGS84")
    total_distance = 0
    distances = [0]

    try:
        for i in range(1, len(points)):
            _, _, distance = geod.inv(
                points[i - 1].longitude, points[i - 1].latitude,
                points[i].longitude, points[i].latitude
            )
            total_distance += distance / 1000  # Convert meters to km
            distances.append(total_distance)
    except Exception as e:
        raise RuntimeError(f"Error calculating distance: {e}")

    return total_distance, distances


def find_extreme_points(points: list[gpxpy.gpx.GPXTrackPoint]) -> tuple[gpxpy.gpx.GPXTrackPoint, gpxpy.gpx.GPXTrackPoint]:
    """
    Finds the highest and lowest elevation points.

    Args:
        points (list): List of GPX track points.

    Returns:
        tuple: Highest and lowest elevation points.
    """
    valid_points = [p for p in points if p.elevation is not None]
    if not valid_points:
        raise ValueError("No valid elevation data found.")

    try:
        highest = max(valid_points, key=lambda p: p.elevation)
        lowest = min(valid_points, key=lambda p: p.elevation)
    except Exception as e:
        raise RuntimeError(f"Error finding extreme points: {e}")

    return highest, lowest


def find_halfway_point(points: list[gpxpy.gpx.GPXTrackPoint], distances: list[float], total_distance: float) -> gpxpy.gpx.GPXTrackPoint:
    """
    Finds the halfway point of the track.

    Args:
        points (list): List of GPX track points.
        distances (list): List of cumulative distances.
        total_distance (float): Total distance of the track.

    Returns:
        gpxpy.gpx.GPXTrackPoint: Halfway point.
    """
    if not points:
        raise ValueError("No points found in the track.")
    halfway_distance = total_distance / 2
    try:
        for i, distance in enumerate(distances):
            if distance >= halfway_distance:
                return points[i]
    except Exception as e:
        raise RuntimeError(f"Error finding halfway point: {e}")

    return points[-1]  # Fallback


def generate_waypoints(gpx: gpxpy.gpx.GPX, prefix: str) -> list[tuple[str, gpxpy.gpx.GPXTrackPoint]]:
    """
    Generates waypoints for the given GPX track.

    Args:
        gpx (gpxpy.gpx.GPX): Parsed GPX object.
        prefix (str): Prefix for waypoint names.

    Returns:
        list: List of waypoints.
    """
    if not gpx.tracks or not gpx.tracks[0].segments:
        raise ValueError("No valid track data found in GPX file.")

    track = gpx.tracks[0]
    track.name = prefix  # Rename the track with the provided prefix
    segment = track.segments[0]
    points = segment.points

    if not points:
        raise ValueError("No track points available.")

    total_distance, distances = calculate_distance(points)

    # Trail head and trail end.
    waypoints = [(f"{prefix}_TH", points[0]), (f"{prefix}_TE", points[-1])]

    # Distance markers every 1km
    for dist_marker in range(1000, int(total_distance * 1000) + 1, 1000):
        for i, distance in enumerate(distances):
            if distance * 1000 >= dist_marker:
                waypoints.append((f"{prefix}_KM{dist_marker // 1000}", points[i]))
                break

    # Highest & lowest points.
    highest, lowest = find_extreme_points(points)
    waypoints.extend([(f"{prefix}_HGH", highest), (f"{prefix}_LWT", lowest)])

    # Halfway point.
    waypoints.append((f"{prefix}_HLF", find_halfway_point(points, distances, total_distance)))

    # Calculate telemetry statistics.
    num_points = len(points)
    ascent = sum(max(0, points[i].elevation - points[i - 1].elevation) for i in range(1, len(points)) if points[i].elevation is not None and points[i - 1].elevation is not None)
    descent = sum(max(0, points[i - 1].elevation - points[i].elevation) for i in range(1, len(points)) if points[i].elevation is not None and points[i - 1].elevation is not None)
    min_altitude = min((p.elevation for p in points if p.elevation is not None), default=None)
    max_altitude = max((p.elevation for p in points if p.elevation is not None), default=None)

    if min_altitude is None or max_altitude is None:
        raise ValueError("No valid elevation data found for telemetry statistics.")

    telemetry_str = (
        f"Total Distance: {total_distance:.2f} km\n"
        f"Number of Points: {num_points}\n"
        f"Total Ascent: {ascent:.0f} m\n"
        f"Total Descent: {descent:.0f} m\n"
        f"Minimum Altitude: {min_altitude:.0f} m\n"
        f"Maximum Altitude: {max_altitude:.0f} m"
    )

    track.comment = telemetry_str

    try:
        return waypoints
    except Exception as e:
        raise RuntimeError(f"Error generating waypoints: {e}")


def save_combined_gpx(gpx: gpxpy.gpx.GPX, waypoints: list[tuple[str, gpxpy.gpx.GPXTrackPoint]], output_file: str) -> None:
    """
    Saves a new GPX file containing the original track and generated waypoints.

    Args:
        gpx (gpxpy.gpx.GPX): Parsed GPX object.
        waypoints (list): List of waypoints.
        output_file (str): Path to save the output GPX file.
    """
    combined_gpx = gpxpy.gpx.GPX()

    for track in gpx.tracks:
        combined_gpx.tracks.append(track)

    for name, point in waypoints:
        combined_gpx.waypoints.append(
            gpxpy.gpx.GPXWaypoint(
                latitude=point.latitude,
                longitude=point.longitude,
                elevation=point.elevation,
                name=name
            )
        )

    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(combined_gpx.to_xml())
    except Exception as e:
        raise RuntimeError(f"Error saving combined GPX: {e}")


def validate_file_path(file_path: str) -> str:
    """
    Validates the file path to ensure it is a valid path.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: Validated file path.

    Raises:
        ValueError: If the file path is invalid.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"Invalid file path: {file_path}")
    try:
        return file_path
    except Exception as e:
        raise ValueError(f"Error validating file path: {e}")

def validate_prefix(prefix: str) -> str:
    """
    Validates the prefix to ensure it contains only alphanumeric characters and underscores.

    Args:
        prefix (str): Prefix for waypoint names.

    Returns:
        str: Validated prefix.

    Raises:
        ValueError: If the prefix is invalid.
    """
    if not re.match(r'^\w+$', prefix):
        raise ValueError(f"Invalid prefix: {prefix}. Only alphanumeric characters and underscores are allowed.")
    try:
        return prefix
    except Exception as e:
        raise ValueError(f"Error validating prefix: {e}")


def main() -> None:
    """
    Handles command-line arguments and executes the script.
    """
    parser = argparse.ArgumentParser(
        description="Generate waypoints for a GPX hiking trail and save an enhanced GPX file."
    )
    parser.add_argument("input_gpx", type=validate_file_path, help="Path to the input GPX file.")
    parser.add_argument("output_gpx", help="Path to save the output GPX file.")
    parser.add_argument("trail_prefix", type=validate_prefix, help="Prefix for waypoint names.")

    args = parser.parse_args()

    try:
        gpx_data = load_gpx(args.input_gpx)
        waypoints = generate_waypoints(gpx_data, args.trail_prefix)
        save_combined_gpx(gpx_data, waypoints, args.output_gpx)
        print(f"GPX file with waypoints saved: {args.output_gpx}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
