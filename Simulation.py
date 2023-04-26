import gymnasium as gym
from gymnasium.spaces import Tuple, Discrete, Box, Dict
import numpy as np
from enum import Enum

import random
import json

ports = {}
planes = {}
port_distances = json.load(open("port_distances.json"))

model_informations = {}
possible_passengers_between_ports = {}

def interpolate_location(start_loc, end_loc, route_completion):
    lat = start_loc["latitude"] + (end_loc["latitude"] - start_loc["latitude"]) * route_completion
    lon = start_loc["longitude"] + (end_loc["longitude"] - start_loc["longitude"]) * route_completion
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

        # TODO: change this parameter
        self.MILE_COMPLETION_PER_STEP = 100
        self.PREPARE_STEP_COUNT = 2

    def init_model(self, model):
        if model not in model_informations:
            print("Model is not available!!")
            return
        self.model = model
        self.fuel = model_informations[model]["fuel"]
        self.capacity = model_informations[model]["capacity"]

    def step(self, action):
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

        self.step_count += 1

        if self.sim_duration == self.step_count:
            done = True
            # self.reset()
            # TODO: Do we need self.reset() ?


        return self.observe(), reward , done, {}

    def reset(self, seed = None, options = None):
        current_plane_id = 0
        for port in ports.values():
            current_plane_id = port.reset(current_plane_id)
        for i in range(current_plane_id, len(planes)):
            planes[i].reset(len(ports) - 1)

        self.step_count = 0

        return self.observe()

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

