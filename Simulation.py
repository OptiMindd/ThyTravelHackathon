import gym
from gym import error, spaces, utils
from gym.utils import seeding
from enum import Enum


class Port:
    def __int__(self):
        self.location = None  # (x, y)

        self.plane_parked = None  # [Plane]
        self.plane_coming = None  # [Plane]
        self.plane_departing = None  # [Plane]

        self.current_passenger_count = None  # int
        self.possible_passenger_count = None  # {port: int}


class PlaneStatus(Enum):
    WAIT = 0
    PREPARE = 1
    FLY = 2


class Plane:
    def __int__(self):
        self.model = None  # string
        self.fuel = None  # float: [0,1]

        self.capacity = None  # int
        self.current_passenger_count = None  # int
        self.current_passenger_ratio = None  # float: [0,1]

        self.location = None  # (x, y)
        self.status = None  # PlaneStatus
        self.current_port = None  # Port

        self.route_completion = None  # float: [0,1]
        self.departure = None  # Port
        self.arrival = None  # Port

    def init_model(self, model):
        pass

    def step(self):
        pass

    def get_reward(self):
        pass

    def set_passenger_count(self, passenger_count):
        pass

    def set_passenger_ratio(self, passenger_ratio):
        pass


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
