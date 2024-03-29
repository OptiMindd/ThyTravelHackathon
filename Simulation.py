import gymnasium as gym
from gymnasium.spaces import Tuple, Discrete, Box, Dict
import numpy as np
from enum import Enum

import random
import pygame
import json

port_distances = json.load(open("port_distances.json"))
port_count = 10
plane_count = 1
max_passenger_count = 3000
domestic_ports = json.load(open("ports.json"))
domestic_ports = [[port_name, domestic_ports[port_name]] for port_name in domestic_ports.keys()][:port_count]

model_informations = {}
possible_passengers_between_ports = {}

def interpolate_location(start_loc, end_loc, route_completion):
    lat = float(start_loc["latitude"]) + (float(end_loc["latitude"]) - float(start_loc["latitude"])) * route_completion
    lon = float(start_loc["longitude"]) + (
                float(end_loc["longitude"]) - float(start_loc["longitude"])) * route_completion
    return {"latitude": lat, "longitude": lon}

class PortTypes:
    LOW_PORT = 0
    MEDIUM_PORT = 1
    HIGH_PORT = 2


passenger_ranges = {
    PortTypes.LOW_PORT: (0, 25),
    PortTypes.MEDIUM_PORT: (20, 50),
    PortTypes.HIGH_PORT: (50, 100)
}

class Port:
    def __init__(self, id, name, location, port_type):
        self.id = id
        self.name = name
        self.location = location  # (x, y)
        self.port_type = port_type
        self.random_passenger_range = passenger_ranges[port_type]

        self.plane_parked = []  # [int -> plane_id]
        self.plane_coming = []  # [int -> plane_id]
        self.plane_departing = []  # [int -> plane_id]

        self.current_passenger_count = None  # int
        self.possible_passenger_count = {}  # {port: int}

    def update(self, resources):
        self.current_passenger_count = 0
        for port_id in resources.ports.keys():
            if port_id != self.id:
                self.possible_passenger_count[port_id] = random.randint(*self.random_passenger_range)
                self.current_passenger_count += self.possible_passenger_count[port_id]

    def reset(self, continued_plane_id, resources, mode="train"):
        self.current_passenger_count = 0
        self.possible_passenger_count = {self.id: 0}
        for port_id in resources.ports.keys():
            if port_id != self.id:
                self.possible_passenger_count[port_id] = random.randint(*self.random_passenger_range)
                self.current_passenger_count += self.possible_passenger_count[port_id]
        self.plane_coming = []
        self.plane_departing = []
        parked_plane_count = self.current_passenger_count // 250
        self.plane_parked = []
        plane_left = len(resources.planes) - continued_plane_id
        for _ in range(min(parked_plane_count, plane_left)):
            self.plane_parked.append(continued_plane_id)
            resources.planes[continued_plane_id].reset(self.id, resources)
            continued_plane_id += 1
        return continued_plane_id


class PlaneStatus(Enum):
    WAIT = 0
    FLY = 1


class ScheduleStatusInfo:
    def __init__(self, status, departure_port_id, arrival_port_id):
        self.step_count = 1
        self.status: PlaneStatus = status
        self.departure_port_id = departure_port_id
        if self.status != PlaneStatus.WAIT:
            assert (arrival_port_id != None or arrival_port_id != -1), \
                "Arrival port id must not be None or -1 when status is not WAIT!!"
            self.arrival_port_id = arrival_port_id
        else:
            assert (arrival_port_id == None or arrival_port_id == -1), \
                "Arrival port id must be None or -1 when status is WAIT!!"

    def expand_one_step(self):
        self.step_count += 1


class PlaneSchedule:
    def __init__(self) -> None:
        self.status_schedule = []
        self.previous_status = None

    def add_step(self, status, departure_port_id, arrival_port_id=None):
        if self.previous_status == None or status != self.previous_status:
            schedule_info = ScheduleStatusInfo(status, departure_port_id, arrival_port_id)
            self.status_schedule.append(schedule_info)
        else:
            schedule_info: ScheduleStatusInfo = self.status_schedule[-1]
            schedule_info.expand_one_step()
        self.previous_status = schedule_info.status

    def convert_to_table(self):
        # convert the schedule to a table with visualizations
        pass

    def clear(self):
        self.status_schedule = []
        self.previous_status = None


class Plane:
    def __init__(self, id, capacity):
        self.id = id  # int
        self.capacity = capacity  # int
        self.model = None  # string
        self.fuel = None  # float: [0,1]

        self.current_passenger_count = None  # int
        self.current_passenger_ratio = None  # float: [0,1]

        self.location = None  # (x, y)
        self.status = None  # PlaneStatus
        self.current_port_id = None  # int

        self.route_completion = None  # float: [0,1]
        self.departure_port_id = None  # int
        self.arrival_port_id = None  # int

        self.curr_fly_total_miles = None  # int

        self.schedule = PlaneSchedule()

        # TODO: change this parameter
        self.MILE_COMPLETION_PER_HOUR = 100
        self.PREPARE_STEP_COUNT = 2
        self.image = pygame.image.load("ucak.png")
        self.image_size = (30, 30)
        self.image = pygame.transform.scale(self.image, self.image_size)

        self.stops = []

    def init_model(self, model):
        if model not in model_informations:
            print("Model is not available!!")
            return
        self.model = model
        self.fuel = model_informations[model]["fuel"]
        self.capacity = model_informations[model]["capacity"]

    def step(self, action, resources):
        # self.schedule.add_step(self.status, self.departure_port_id, self.arrival_port_id)
        self.arrival_port_id = action
        try:
            self.curr_fly_total_miles = port_distances[resources.ports[self.departure_port_id].name][
                resources.ports[self.arrival_port_id].name]
        except:
            self.curr_fly_total_miles = 400
        time_for_step = self.curr_fly_total_miles / self.MILE_COMPLETION_PER_HOUR

        resources.ports[self.departure_port_id].plane_parked.remove(self.id)
        resources.ports[self.departure_port_id].plane_departing.append(self.id)
        resources.ports[self.arrival_port_id].plane_coming.append(self.id)

        # transfer passangers from port(departure) to plane
        self.current_passenger_count = min(self.capacity,
                                           resources.ports[self.departure_port_id].possible_passenger_count[
                                               self.arrival_port_id])
        resources.ports[self.departure_port_id].possible_passenger_count[
            self.arrival_port_id] -= self.current_passenger_count
        resources.ports[self.departure_port_id].current_passenger_count -= self.current_passenger_count

        resources.ports[self.departure_port_id].plane_departing.remove(self.id)
        resources.ports[self.arrival_port_id].plane_coming.remove(self.id)
        resources.ports[self.arrival_port_id].plane_parked.append(self.id)
        self.location = resources.ports[self.arrival_port_id].location
        # self.arrival.current_passenger_count += self.current_passenger_count

        if self.current_port_id == action:
            reward = -1
        else:
            reward = self.get_reward(resources)
        self.current_port_id = self.arrival_port_id
        self.departure_port_id = self.arrival_port_id
        self.arrival_port_id = -1

        self.stops.append(resources.ports[self.departure_port_id].name)

        return reward

    def get_reward(self, resource):
        passengers = resource.ports[self.current_port_id].possible_passenger_count
        items = sorted(passengers.items(), key=lambda x:x[1], reverse=True)

        i = 0
        for item in items:
            if item[0] == self.arrival_port_id:
                break
            i += 1

        return (len(resource.ports)  - i) / len(resource.ports)

        # return (self.current_passenger_count / self.capacity) ** 2

    def reset(self, parked_plane_id, resources):
        self.current_passenger_count = 0
        self.current_passenger_ratio = 0
        self.status = PlaneStatus.WAIT

        self.departure_port_id = parked_plane_id
        self.current_port_id = parked_plane_id
        self.arrival_port_id = -1
        self.location = resources.ports[parked_plane_id].location

        self.route_completion = 0
        self.curr_fly_total_miles = None
        self.schedule.clear()

        self.stops.clear()


class Visualization:
    def __init__(self, width, height) -> None:
        pygame.init()  # pygame'i başlatır
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))  # ekranı oluşturur
        pygame.display.set_caption("Simulasyon")  # pencere
        # pencere başlığını ayarlar
        self.background_image = pygame.image.load("arkaplan.jpg")  # arkaplan resmini yükler
        self.background_image = pygame.transform.scale(self.background_image, (self.width, self.height))

        self.boundary_min_x = 0
        self.boundary_min_y = 0
        self.boundary_max_x = 0
        self.boundary_max_y = 0
        self.lat_length = self.boundary_max_x - self.boundary_min_x
        self.lon_length = self.boundary_max_y - self.boundary_min_y

    def convert_geoloc_to_cart(self, loc):
        x_ratio = (loc["longitude"] - self.boundary_min_x) / self.lon_length
        y_ratio = (loc["latitude"] - self.boundary_min_y) / self.lat_length
        x_loc = x_ratio * self.width
        y_loc = y_ratio * self.height
        return (x_loc, y_loc)

    def render_port(self, port: Port):
        color = (0, 0, 0)
        circle_radius = 5
        size = 32
        font = pygame.font.Font(None, size)  # font nesnesi oluşturur
        text_surface = font.render(port.name, True, color)  # metni renderlar
        port_cart_loc = self.convert_geoloc_to_cart(port.location)
        self.screen.blit(text_surface, (port_cart_loc[0], port_cart_loc[1] + circle_radius))  # metni çizer
        pygame.draw.circle(self.screen, color, self.location, circle_radius)

    def render_plane(self, plane: Plane):
        plane_cart_loc = self.convert_geoloc_to_cart(plane.location)
        self.screen.blit(plane.image, plane_cart_loc)

    def render(self, resources):
        self.screen.blit(self.background_image, (0, 0))
        for port in resources.ports.values():  # havalimanlarını çizer
            self.render_port(port)
        for plane in resources.planes.values():
            self.render_plane(plane)
        pygame.display.flip()


class Resources:
    def __init__(self) -> None:
        self.ports = {}
        self.planes = {}

        for port_id, port_info in enumerate(domestic_ports):
            self.ports[port_id] = Port(port_id, port_info[0], port_info[1], random.randint(0, 2))

        for plane_id in range(plane_count):
            if plane_id % 2 == 0:
                capacity = 250
            else:
                capacity = 350
            self.planes[plane_id] = Plane(plane_id, capacity)


class Simulation(gym.Env):
    metadata = {'render.modes': ['human', 'machine']}

    def __init__(self):
        self.seed = np.random.seed
        self.sim_duration = 168  # in hour
        self.step_count = 0
        self.resources = Resources()

        # one_space = Tuple((Discrete(len(ports)), Discrete(len(ports)),
        #                    Box(low=np.array([0, 0, 0]), high=np.array([100, 100, 100]), shape=(3,),
        #                        dtype=np.integer)))  # departure, arrival, current_passenger, passenger_ratio, route_completion


        # self.observation_space = Tuple((Discrete(len(self.resources.ports)) , Box(low=np.zeros((len(self.resources.ports), len(self.resources.ports))),
        #                              high=(np.ones((len(self.resources.ports), len(self.resources.ports))) - np.diag([1]*len(self.resources.ports))) * max_passenger_count,
        #                              shape=(len(self.resources.ports), len(self.resources.ports)),
        #                              dtype=np.integer)))  # departure, current_passenger, passenger_ratio

        port_count = len((self.resources.ports))
        high_values = (np.ones((len(self.resources.ports), len(self.resources.ports))) - np.diag([1]*len(self.resources.ports))) * max_passenger_count
        high_values = np.vstack((np.ones(port_count), high_values))
        # high_values = np.concatenate((np.array([len(self.resources.ports)]), high_values.flatten()))
        # self.observation_space = Box(low=np.zeros(len(self.resources.ports) * len(self.resources.ports) + 1),
        #      high=high_values,
        #      shape=(len(self.resources.ports) * len(self.resources.ports) + 1, ),
        #      dtype=np.integer)


        self.observation_space = Box(low=np.zeros((port_count + 1, port_count)), high=high_values, shape=(port_count+1, port_count), dtype=np.integer)

        self.action_space = Discrete(len(self.resources.ports))

        self.visualize = False
        if self.visualize:
            self.visualizator = Visualization(800, 600)

        # TODO: Do we need it ?
        # self.reset()

    def step(self, action):
        done = False
        reward = 0
        for i, plane in self.resources.planes.items():
            reward += plane.step(action, self.resources)

        if self.step_count % 5 == 0:
            for port in self.resources.ports.values():
                port.update(self.resources)

        if self.visualize:
            self.visualizator.render(self.resources)

        self.step_count += 1

        if self.sim_duration == self.step_count:
            done = True
            # self.reset()
            # TODO: Do we need self.reset() ?

        return self.observe(), reward, done, False, {}

    def reset(self, seed=None, options=None):
        current_plane_id = 0
        for port in self.resources.ports.values():
            current_plane_id = port.reset(current_plane_id, self.resources)
        for i in range(current_plane_id, len(self.resources.planes)):
            self.resources.planes[i].reset(len(self.resources.ports) - 1, self.resources)

        self.step_count = 0

        return self.observe(), {}

    def observe(self):
        plane_departure_port_id = self.resources.planes[0].departure_port_id
        port_passenger_mat = np.zeros((len(self.resources.ports), len(self.resources.ports)))
        for port in self.resources.ports.values():
            for other_port in self.resources.ports.values():
                port_passenger_mat[port.id][other_port.id] = port.possible_passenger_count[other_port.id]
        # state = np.concatenate(([plane_departure_port_id], port_passenger_mat.flatten()))
        current_port_vec = np.zeros(len(self.resources.ports))
        current_port_vec[plane_departure_port_id] = 1
        state = np.vstack((current_port_vec, port_passenger_mat))
        # state = np.zeros((len(self.resources.ports) + 1, len(self.resources.ports)))
        return state

        # for plane in self.resources.planes.values():
        #     # print([plane.departure_port_id, plane.arrival_port_id, plane.current_passenger_count, plane.current_passenger_ratio, plane.route_completion])
        #     observation = np.array([plane.departure_port_id, plane.arrival_port_id, plane.current_passenger_count,
        #                             plane.current_passenger_ratio, plane.route_completion], dtype=np.integer)
        # return observation

    def render(self, mode='human', close=False):
        pass

    def close(self):
        pass
