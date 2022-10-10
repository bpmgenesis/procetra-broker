from abc import ABC, abstractmethod

class Activity(ABC):
    @abstractmethod
    async def execute(self, flow_variables):
        pass