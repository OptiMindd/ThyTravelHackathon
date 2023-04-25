import gym
from gym import error, spaces, utils
from gym.utils import seeding
from enum import Enum

import random
from thy_api import ThyAPI
ports = {}
planes = {}

model_informations = {}
possible_passengers_between_ports = {}

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
    
    def reset(self, continued_plane_id, mode="train"): 
        self.current_passenger_count = 0
        self.possible_passenger_count = {}
        for port_id in ports.keys(): 
            if port_id != self.id: 
                if mode == "test": 
                    self.possible_passenger_count[port_id] = possible_passengers_between_ports[(self.id, port_id)] * random.uniform(0.9, 1.1)
                else: 
                    self.possible_passenger_count[port_id] = random.randint(200, 1000)
                self.current_passenger_count += self.possible_passenger_count[port_id]
        self.plane_coming = []
        self.plane_departing = []
        parked_plane_count = self.current_passenger_count / 250
        self.plane_parked = []
        for _ in parked_plane_count: 
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
                self.steps_left_for_prepare = self.PREPARE_STEP_COUNT
                self.status = PlaneStatus.PREPARE
            return self.get_reward()
        elif self.status == PlaneStatus.PREPARE: 
            if action != 0: # continue to prepare
                return -100.0

            self.steps_left_for_prepare -= 1
            if self.steps_left_for_prepare == 0: 
                arrival_port_id = action - 1
                self.arrival_port_id = arrival_port_id

                # change from wait to fly status
                ports[self.departure_port_id].plane_parked.remove(self.id)
                ports[self.departure_port_id].plane_departing.append(self.id)
                ports[arrival_port_id].plane_coming.append(self.id)
                
                # transfer passangers from port(departure) to plane
                self.current_passenger_count = min(self.capacity, ports[self.departure_port_id].possible_passenger_count[arrival_port_id])
                ports[self.departure_port_id].possible_passenger_count[arrival_port_id] -= self.current_passenger_count
                ports[self.departure_port_id].current_passenger_count -= self.current_passenger_count

                self.current_passenger_ratio = (int) ((self.current_passenger_count / self.capacity) * 100)
                self.route_completion = 0

                # TODO: get total miles from thy api
                self.curr_fly_total_miles = 1000
                self.status = PlaneStatus.FLY
            return 0.8

        elif self.status == PlaneStatus.FLY: 
            if action != 0: # continue to fly
                return -100.0
            
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
                self.arrival_port_id = None

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
        self.arrival_port_id = None
        self.location = ports[parked_plane_id].location

        self.route_completion = 0
        self.curr_fly_total_miles = None

class Simulation (gym.Env):
    metadata = {'render.modes': ['human', 'machine']}

    def __init__(self):
        self.observation_space = None
        self.action_space = None

        self.reset()
        
    def step(self, action):

        """
    This method is the primary interface between environment and agent.
    Paramters: 
        action: int
                the index of the respective action (if action space is discrete)
    Returns:
        output: (array, float, bool)
                information provided by the environment about its current state:
                (observation, reward, done)
    """
        pass

    def reset(self):
        """
    This method resets the environment to its initial values.
    Returns:
        observation:    array
                        the initial state of the environment
    """
        pass

    def render(self, mode='human', close=False):
        """
    This methods provides the option to render the environment's behavior to a window 
    which should be readable to the human eye if mode is set to 'human'.
    """
        pass

    def close(self):
        """
    This method provides the user with the option to perform any necessary cleanup.
    """
        pass

if __name__ == "__main__": 
    api = ThyAPI()
    port_count = 10
    domestic_ports = api.get_domestic_ports()[:port_count]
    for port_id, port_info in enumerate(domestic_ports): 
        ports[port_id] = Port(port_id, port_info[0], port_info[1])
    
    plane_count = (int) (port_count * 1.5)
    for plane_id in range(plane_count):
        if plane_id % 2 == 0: 
            capacity = 250
        else: 
            capacity = 350 
        planes[plane_id] = Plane(plane_id, capacity)