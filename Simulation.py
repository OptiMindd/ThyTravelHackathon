import gymnasium as gym
from gymnasium.spaces import Tuple, Discrete, Box, Dict
import numpy as np
from enum import Enum

import random
import pygame
import json

ports = {}
planes = {}
port_distances = json.load(open("port_distances.json"))

model_informations = {}
possible_passengers_between_ports = {}

def interpolate_location(start_loc, end_loc, route_completion): 
    lat = float(start_loc["latitude"]) + (float(end_loc["latitude"]) - float(start_loc["latitude"])) * route_completion
    lon = float(start_loc["longitude"]) + (float(end_loc["longitude"]) - float(start_loc["longitude"])) * route_completion
    return {"latitude": lat, "longitude": lon}

class Port:
    def __init__(self, id, name, location):
        self.id = id
        self.name = name
        self.location = location  # (x, y)

        self.plane_parked = []  # [int -> plane_id]
        self.plane_coming = []  # [int -> plane_id]
        self.plane_departing = []  # [int -> plane_id]

        self.current_passenger_count = None  # int
        self.possible_passenger_count = {}  # {port: int}

    def update(self, mode="train"):
        for port_id in ports.keys():
            if port_id != self.id:
                if mode == "test":
                    self.possible_passenger_count[port_id] += possible_passengers_between_ports[(self.id, port_id)] * random.uniform(0.9, 1.1)
                else:
                    self.possible_passenger_count[port_id] = random.randint(200, 1000)
                self.current_passenger_count += self.possible_passenger_count[port_id]
    
    def reset(self, continued_plane_id, mode="train"): 
        self.current_passenger_count = 0
        self.possible_passenger_count = {self.id : 0}
        for port_id in ports.keys(): 
            if port_id != self.id: 
                if mode == "test": 
                    self.possible_passenger_count[port_id] = possible_passengers_between_ports[(self.id, port_id)] * random.uniform(0.9, 1.1)
                else: 
                    self.possible_passenger_count[port_id] = random.randint(200, 1000)
                self.current_passenger_count += self.possible_passenger_count[port_id]
        self.plane_coming = []
        self.plane_departing = []
        parked_plane_count = self.current_passenger_count // 250
        self.plane_parked = []
        plane_left = len(planes) - continued_plane_id
        for _ in range(min(parked_plane_count, plane_left)):
            self.plane_parked.append(continued_plane_id)
            planes[continued_plane_id].reset(self.id)
            continued_plane_id += 1
        return continued_plane_id

class PlaneStatus(Enum):
    WAIT = 0
    PREPARE = 1
    FLY = 2

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
        self.id = id # int
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

        self.curr_fly_total_miles = None # int

        self.schedule = PlaneSchedule() 

        # TODO: change this parameter
        self.MILE_COMPLETION_PER_STEP = 100
        self.PREPARE_STEP_COUNT = 2
        self.image = pygame.image.load("ucak.png")
        self.image_size = (30, 30)
        self.image = pygame.transform.scale(self.image, self.image_size) 

    def init_model(self, model):
        if model not in model_informations:
            print("Model is not available!!")
            return
        self.model = model
        self.fuel = model_informations[model]["fuel"]
        self.capacity = model_informations[model]["capacity"]

    def step(self, action):
        self.schedule.add_step(self.status, self.departure_port_id, self.arrival_port_id)
        if self.status == PlaneStatus.WAIT:
            if action != 0:
                arrival_port_id = action - 1
                self.arrival_port_id = arrival_port_id

                self.steps_left_for_prepare = self.PREPARE_STEP_COUNT
                self.status = PlaneStatus.PREPARE
            return self.get_reward()
        elif self.status == PlaneStatus.PREPARE:
            if action != 0: # continue to prepare
                return -1

            self.steps_left_for_prepare -= 1
            if self.steps_left_for_prepare == 0:

                # change from wait to fly status
                ports[self.departure_port_id].plane_parked.remove(self.id)
                ports[self.departure_port_id].plane_departing.append(self.id)
                ports[self.arrival_port_id].plane_coming.append(self.id)

                # transfer passangers from port(departure) to plane
                self.current_passenger_count = min(self.capacity, ports[self.departure_port_id].possible_passenger_count[self.arrival_port_id])
                ports[self.departure_port_id].possible_passenger_count[self.arrival_port_id] -= self.current_passenger_count
                ports[self.departure_port_id].current_passenger_count -= self.current_passenger_count

                self.current_passenger_ratio = (int) ((self.current_passenger_count / self.capacity) * 100)
                self.route_completion = 0

                try:
                    self.curr_fly_total_miles = port_distances[ports[self.departure_port_id].name][ports[self.arrival_port_id].name]
                except:
                    self.curr_fly_total_miles = 400
                self.status = PlaneStatus.FLY
            return 0.8

        elif self.status == PlaneStatus.FLY:
            if action != 0: # continue to fly
                return -1

            self.route_completion += (int) ((self.MILE_COMPLETION_PER_STEP / self.curr_fly_total_miles) * 100)
            self.location = interpolate_location(ports[self.departure_port_id].location, ports[self.arrival_port_id].location, self.route_completion)
            if self.route_completion >= 1.0:
                # change from fly to wait status
                ports[self.departure_port_id].plane_departing.remove(self.id)
                ports[self.arrival_port_id].plane_coming.remove(self.id)
                ports[self.arrival_port_id].plane_parked.append(self.id)
                self.location = ports[self.arrival_port_id].location
                # self.arrival.current_passenger_count += self.current_passenger_count

                self.current_port_id = self.arrival_port_id
                self.departure_port_id = self.arrival_port_id
                self.arrival_port_id = -1

                self.current_passenger_count = 0

                self.status = PlaneStatus.WAIT
            return self.get_reward()

    def get_reward(self):
        return (self.current_passenger_ratio / 100) ** 2

    def reset(self, parked_plane_id):
        self.current_passenger_count = 0
        self.current_passenger_ratio = 0
        self.status = PlaneStatus.WAIT

        self.departure_port_id = parked_plane_id
        self.current_port_id = parked_plane_id
        self.arrival_port_id = -1
        self.location = ports[parked_plane_id].location

        self.route_completion = 0
        self.curr_fly_total_miles = None
        self.schedule.clear()
    
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
        color=(0, 0, 0)
        circle_radius = 5
        size=32
        font = pygame.font.Font(None, size)  # font nesnesi oluşturur
        text_surface = font.render(port.name, True, color)  # metni renderlar
        port_cart_loc = self.convert_geoloc_to_cart(port.location)
        self.screen.blit(text_surface, (port_cart_loc[0], port_cart_loc[1] + circle_radius))  # metni çizer
        pygame.draw.circle(self.screen, color, self.location, circle_radius)

    def render_plane(self, plane: Plane): 
        plane_cart_loc = self.convert_geoloc_to_cart(plane.location)
        self.screen.blit(plane.image, plane_cart_loc)
    
    def render(self): 
        self.screen.blit(self.background_image, (0, 0))
        for port in ports.values():  # havalimanlarını çizer
            self.render_port(port)
        for plane in planes.values(): 
            self.render_plane(plane)
        pygame.display.flip()


class Simulation (gym.Env):
    metadata = {'render.modes': ['human', 'machine']}

    def __init__(self, domestic_ports):
        self.seed = np.random.seed
        self.sim_duration = 168  # in hour
        self.step_count = 0

        port_count = 10
        for port_id, port_info in enumerate(domestic_ports):
            ports[port_id] = Port(port_id, port_info[0], port_info[1])

        plane_count = 1
        for plane_id in range(plane_count):
            if plane_id % 2 == 0:
                capacity = 250
            else:
                capacity = 350
            planes[plane_id] = Plane(plane_id, capacity)

        # one_space = Tuple((Discrete(len(ports)), Discrete(len(ports)),
        #                    Box(low=np.array([0, 0, 0]), high=np.array([100, 100, 100]), shape=(3,),
        #                        dtype=np.integer)))  # departure, arrival, current_passenger, passenger_ratio, route_completion

        one_space = Box(low=np.array([0, -1, 0, 0, 0]), high=np.array([len(ports), len(ports), 100, 100, 100]), shape=(5,),
                               dtype=np.integer)  # departure, arrival, current_passenger, passenger_ratio, route_completion

        self.observation_space = Tuple([one_space for _ in range(len(planes))])
        # self.action_space = Tuple([Discrete(len(ports) + 1) for _ in range(len(planes))])
        # self.action_space = Dict({plane_id: Discrete(len(ports) + 1) for plane_id in range(len(planes))})
        self.action_space = Discrete(len(ports))

        self.visualize = False
        if self.visualize: 
            self.visualizator = Visualization(800, 600)

        #TODO: Do we need it ?
        # self.reset()

    def step(self, action):
        done = False
        reward = 0
        for i, plane in planes.items():
            reward += plane.step(action)
        if self.step_count % 24 == 0:
            for port in ports.values():
                port.update()

        
        if self.visualize: 
            self.visualizator.render()

        self.step_count += 1

        if self.sim_duration == self.step_count:
            done = True
            # self.reset()
            # TODO: Do we need self.reset() ?


        return self.observe(), reward, done, False, {}

    def reset(self, seed = None, options = None):
        current_plane_id = 0
        for port in ports.values():
            current_plane_id = port.reset(current_plane_id)
        for i in range(current_plane_id, len(planes)):
            planes[i].reset(len(ports) - 1)

        self.step_count = 0

        return self.observe(), {}

    def observe(self):
        observations = []
        for plane in planes.values():
            # print([plane.departure_port_id, plane.arrival_port_id, plane.current_passenger_count, plane.current_passenger_ratio, plane.route_completion])
            observation = np.array([plane.departure_port_id, plane.arrival_port_id, plane.current_passenger_count, plane.current_passenger_ratio, plane.route_completion], dtype=np.integer)
            observations.append(observation)
        return np.array(observations)

    def render(self, mode='human', close=False):
        pass

    def close(self):
        pass

