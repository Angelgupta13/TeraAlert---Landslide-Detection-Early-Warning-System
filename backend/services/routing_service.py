import osmnx as ox
import networkx as nx
import random
import math
from shapely.geometry import Point, LineString
from schemas import RouteRequest, RouteResponse

from core.config import settings


class RoutingService:
    def __init__(self):
        self.G = None
        self.place = settings.DEFAULT_MAP_PLACE

    def load_graph(self, origin_lat, origin_lon, dest_lat, dest_lon):
        # Calculate midpoint
        mid_lat = (origin_lat + dest_lat) / 2
        mid_lon = (origin_lon + dest_lon) / 2

        # Approximate distance logic to encompass both origin and destination
        lat_diff_meters = abs(origin_lat - dest_lat) * 111320
        lon_diff_meters = abs(origin_lon - dest_lon) * 111320
        max_dist = max(lat_diff_meters, lon_diff_meters)

        # Radius from midpoint to cover both plus 2km extra routing room
        search_radius = (max_dist / 2) + 2000

        if search_radius > 20000:
            raise ValueError(
                f"Origin and Destination are too far apart for real-time routing! Please select points closer together (max 30 km). Attempted distance radius: {int(search_radius / 1000)}km"
            )

        print(
            f"[INFO] Downloading OpenStreetMap data ({int(search_radius)}m radius)..."
        )
        self.G = ox.graph_from_point(
            (mid_lat, mid_lon), dist=search_radius, network_type="drive"
        )
        print("[OK] Dynamic Regional Map loaded successfully!")

    def remove_nearby_edges(self, G, active_landslides, radius_meters=300):
        """Creates a safe copy of the map graph by severely punishing roads near ALL active landslides (300m safety radius)."""
        G_safe = G.copy()
        edges_to_remove = set()

        for u, v, data in G_safe.edges(data=True):
            if "geometry" in data:
                line = data["geometry"]
            else:
                point_u = Point((G_safe.nodes[u]["x"], G_safe.nodes[u]["y"]))
                point_v = Point((G_safe.nodes[v]["x"], G_safe.nodes[v]["y"]))
                line = LineString([point_u, point_v])

            for landslide in active_landslides:
                slide_point = Point(landslide["longitude"], landslide["latitude"])
                distance = line.distance(slide_point)

                # Simple approximate spatial conversion: 1 degree ~ 111320 meters
                if distance < (radius_meters / 111320):
                    edges_to_remove.add((u, v))
                    break  # Already flagged for removal, skip checking others

        G_safe.remove_edges_from(edges_to_remove)
        return G_safe

    def generate_initial_population(self, G, start, end, pop_size=10):
        population = []
        try:
            shortest = nx.shortest_path(G, start, end, weight="length")
            population.append(shortest)
        except:
            return population

        for _ in range(pop_size - 1):
            try:
                path = nx.shortest_path(G, start, end, weight="length")
                rand_node = random.choice(path[1:-1])
                mid1 = nx.shortest_path(G, start, rand_node, weight="length")
                mid2 = nx.shortest_path(G, rand_node, end, weight="length")
                combined = mid1[:-1] + mid2
                population.append(combined)
            except:
                continue
        return population

    def get_fitness(self, G, path):
        try:
            return 1 / (nx.path_weight(G, path, weight="length") + 1)
        except:
            return 0

    def select(self, population, G, num=4):
        scored = sorted(population, key=lambda p: self.get_fitness(G, p), reverse=True)
        return scored[:num]

    def crossover(self, p1, p2):
        common = list(set(p1) & set(p2))
        if len(common) <= 2:
            return p1
        mid = random.choice(common[1:-1])
        return p1[: p1.index(mid)] + p2[p2.index(mid) :]

    def mutate(self, G, path):
        if len(path) < 4:
            return path
        idx = random.randint(1, len(path) - 2)
        neighbors = list(G.neighbors(path[idx]))
        if not neighbors:
            return path
        new_node = random.choice(neighbors)
        try:
            p1 = nx.shortest_path(G, path[0], new_node, weight="length")
            p2 = nx.shortest_path(G, new_node, path[-1], weight="length")
            return p1[:-1] + p2
        except:
            return path

    def run_ga(self, G, start, end, generations=10, pop_size=6):
        population = self.generate_initial_population(G, start, end, pop_size)
        if not population:
            return None

        for _ in range(generations):
            parents = self.select(population, G)
            children = []
            for i in range(len(parents) - 1):
                child = self.crossover(parents[i], parents[i + 1])
                child = self.mutate(G, child)
                children.append(child)
            population += children

        best = self.select(population, G, num=1)[0]
        return best

    def generate_directions(self, G, path):
        directions = []
        total_distance = 0
        for i in range(len(path) - 2):
            node1, node2, node3 = path[i], path[i + 1], path[i + 2]

            def vector(a, b):
                return (b[0] - a[0], b[1] - a[1])

            coord1 = (G.nodes[node1]["x"], G.nodes[node1]["y"])
            coord2 = (G.nodes[node2]["x"], G.nodes[node2]["y"])
            coord3 = (G.nodes[node3]["x"], G.nodes[node3]["y"])

            v1 = vector(coord2, coord1)
            v2 = vector(coord2, coord3)
            angle = math.degrees(math.atan2(v2[1], v2[0]) - math.atan2(v1[1], v1[0]))

            if -30 <= angle <= 30:
                direction_text = "Go straight"
            elif 30 < angle <= 135:
                direction_text = "Turn left"
            elif -135 <= angle < -30:
                direction_text = "Turn right"
            else:
                direction_text = "U-turn"

            try:
                segment_length = G.edges[node2, node3, 0]["length"]
            except:
                segment_length = 0

            total_distance += segment_length
            directions.append(f"{direction_text} for {int(segment_length)} meters")

        return directions, int(total_distance)

    def generate_gmaps_link_from_path(self, G, path, max_points=10):
        if not path or len(path) < 2:
            return None
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]
        if len(coords) > max_points:
            step = len(coords) // (max_points - 1)
            coords = [coords[i] for i in range(0, len(coords), step)]
            if coords[-1] != (G.nodes[path[-1]]["y"], G.nodes[path[-1]]["x"]):
                coords.append((G.nodes[path[-1]]["y"], G.nodes[path[-1]]["x"]))
        url = "https://www.google.com/maps/dir/" + "/".join(
            [f"{lat},{lon}" for lat, lon in coords]
        )
        return url

    def calculate_safe_route(
        self, request: RouteRequest, active_landslides: list
    ) -> RouteResponse:
        origin_coords = (request.origin.lat, request.origin.lon)
        dest_coords = (request.destination.lat, request.destination.lon)

        self.load_graph(
            origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1]
        )

        if self.G is None:
            raise ValueError("Failed to load map graph")

        start_node = ox.distance.nearest_nodes(
            self.G, origin_coords[1], origin_coords[0]
        )
        end_node = ox.distance.nearest_nodes(self.G, dest_coords[1], dest_coords[0])

        safe_graph = self.remove_nearby_edges(self.G, active_landslides)

        best_path_nodes = self.run_ga(safe_graph, start_node, end_node)

        if not best_path_nodes:
            raise ValueError(
                "No safe route could be found physically avoiding the landslide zone."
            )

        path_coords = [
            (safe_graph.nodes[n]["y"], safe_graph.nodes[n]["x"])
            for n in best_path_nodes
        ]
        directions, total_distance = self.generate_directions(
            safe_graph, best_path_nodes
        )
        gmap_link = self.generate_gmaps_link_from_path(safe_graph, best_path_nodes)

        return RouteResponse(
            path_coordinates=path_coords,
            total_distance_meters=total_distance,
            directions=directions,
            gmaps_link=gmap_link,
        )


# Instantiate singleton server handler
routing_service = RoutingService()
